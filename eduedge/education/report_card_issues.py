from __future__ import annotations

import base64
import io
import hashlib
import json
import secrets
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.services.institution_branding import get_institution_branding

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


def generate_verification_code() -> str:
	"""Return an opaque, non-sequential code suitable for a public verification link."""
	while True:
		code = secrets.token_urlsafe(18)
		if not frappe.db.exists(ISSUE_DOCTYPE, {"verification_code": code}):
			return code


def ensure_issue_verification_code(issue_name: str, current_code: str | None = None) -> str:
	"""Backfill verification metadata without changing the immutable report payload/hash."""
	if current_code:
		return current_code
	code = generate_verification_code()
	frappe.db.set_value(
		ISSUE_DOCTYPE,
		issue_name,
		"verification_code",
		code,
		update_modified=False,
	)
	return code


def build_verification_url(code: str) -> str:
	base = frappe.utils.get_url().rstrip("/")
	return f"{base}/verify-result?{urlencode({'code': code})}"


def build_verification_qr_data_uri(url: str) -> str:
	from pyqrcode import create as qrcreate

	stream = io.BytesIO()
	qrcreate(url).svg(stream, scale=3, quiet_zone=1)
	encoded = base64.b64encode(stream.getvalue()).decode("ascii")
	return f"data:image/svg+xml;base64,{encoded}"


def create_report_card_issue(review: str) -> str:
	review_doc = frappe.get_doc("EduEdge Report Card Review", review)
	if review_doc.progression_status != "Approved":
		frappe.throw(_("Approve the Report Card Review before issuing the official report card."), frappe.ValidationError)

	from eduedge.education.report_cards import get_student_report_card_payload

	payload = get_student_report_card_payload(
		review_doc.result_publication,
		review_doc.student,
		_prefer_issued=False,
	)
	payload = _freeze_institution_identity(payload)
	publication = payload.get("publication") or {}
	payload["issue"] = {
		"issue_version": _next_issue_version(review_doc.result_publication, review_doc.student),
		"issued_by": frappe.session.user,
		"issued_on": str(now_datetime()),
		"report_card_review": review_doc.name,
	}
	previous = _latest_issue_row(review_doc.result_publication, review_doc.student)
	if previous:
		payload["issue"]["supersedes_issue"] = previous.name

	payload_json = _canonical_json(payload)
	payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
	issue = frappe.get_doc(
		{
			"doctype": ISSUE_DOCTYPE,
			"result_publication": review_doc.result_publication,
			"publication_version": int(publication.get("publication_version") or 1),
			"report_card_review": review_doc.name,
			"issue_version": payload["issue"]["issue_version"],
			"supersedes_issue": previous.name if previous else None,
			"student": review_doc.student,
			"student_name": payload.get("student", {}).get("student_name"),
			"school_branch": review_doc.school_branch,
			"student_group": review_doc.student_group,
			"academic_year": review_doc.academic_year,
			"academic_term": review_doc.academic_term,
			"result_mode": publication.get("result_mode") or "Terminal",
			"result_profile": publication.get("result_profile"),
			"payload_hash": payload_hash,
			"issued_by": frappe.session.user,
			"issued_on": now_datetime(),
			"verification_code": generate_verification_code(),
			"payload_json": payload_json,
		}
	)
	issue.insert(ignore_permissions=True)
	return issue.name


def get_effective_issued_payload(publication: str, student: str) -> dict | None:
	review = frappe.db.get_value(
		"EduEdge Report Card Review",
		{"result_publication": publication, "student": student},
		["name", "progression_status"],
		as_dict=True,
	)
	if not review or review.progression_status != "Approved":
		return None
	row = _latest_issue_row(publication, student)
	if not row:
		return None
	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if actual_hash != row.payload_hash:
		frappe.throw(_("Issued Report Card integrity check failed."), frappe.ValidationError)
	payload = json.loads(row.payload_json)
	verification_code = ensure_issue_verification_code(row.name, row.get("verification_code"))
	verification_url = build_verification_url(verification_code)
	payload["issue_record"] = {
		"name": row.name,
		"issue_version": int(row.issue_version or 1),
		"payload_hash": row.payload_hash,
		"verification_code": verification_code,
		"verification_url": verification_url,
		"verification_qr_data_uri": build_verification_qr_data_uri(verification_url),
	}
	return payload


def _freeze_institution_identity(payload: dict) -> dict:
	branch = payload.get("branch") or {}
	branch_name = branch.get("name")
	institution_name = (
		frappe.db.get_value("EduEdge School Branch", branch_name, "institution")
		if branch_name
		else None
	)
	branding = get_institution_branding(institution_name, branch=branch_name)
	institution = {}
	if institution_name:
		institution = dict(
			frappe.db.get_value(
				"EduEdge Institution",
				institution_name,
				[
					"name",
					"institution_name",
					"official_name",
					"short_name",
					"institution_code",
					"institution_type",
				],
				as_dict=True,
			)
			or {}
		)
	payload["institution"] = institution
	payload["branding"] = branding
	if branding.get("address"):
		payload["address"] = branding["address"]
	return payload


def _latest_issue_row(publication: str, student: str):
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": publication, "student": student},
		fields=["name", "issue_version", "payload_hash", "payload_json", "verification_code"],
		order_by="issue_version desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def _next_issue_version(publication: str, student: str) -> int:
	previous = _latest_issue_row(publication, student)
	return int(previous.issue_version or 0) + 1 if previous else 1


def _canonical_json(value: dict) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
