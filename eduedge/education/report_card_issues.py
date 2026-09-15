from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.services.institution_branding import get_institution_branding
from eduedge.education.result_verification import build_issue_verification

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


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
			"verification_token": frappe.generate_hash(length=32),
			"issued_by": frappe.session.user,
			"issued_on": now_datetime(),
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
	payload["issue_record"] = {
		"name": row.name,
		"issue_version": int(row.issue_version or 1),
		"payload_hash": row.payload_hash,
	}
	payload["verification"] = build_issue_verification(row.name, row.get("verification_token"))
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
		fields=["name", "issue_version", "payload_hash", "payload_json", "verification_token", "issued_on", "supersedes_issue"],
		order_by="issue_version desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def get_report_card_issue_history(publication: str, student: str) -> list[dict]:
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": publication, "student": student},
		fields=[
			"name",
			"issue_version",
			"publication_version",
			"supersedes_issue",
			"payload_hash",
			"issued_by",
			"issued_on",
		],
		order_by="issue_version desc, creation desc",
		page_length=0,
	)
	return [
		{
			**dict(row),
			"fingerprint": str(row.payload_hash or "")[:16].upper(),
		}
		for row in rows
	]


def _next_issue_version(publication: str, student: str) -> int:
	previous = _latest_issue_row(publication, student)
	return int(previous.issue_version or 0) + 1 if previous else 1


def _canonical_json(value: dict) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
