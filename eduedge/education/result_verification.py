from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.utils.print_format_generator import get_qr_code

ISSUE_DOCTYPE = "EduEdge Report Card Issue"


def build_issue_verification(issue_name: str, token: str | None) -> dict:
	if not issue_name or not token:
		return {}
	query = urlencode({"issue": issue_name, "token": token})
	url = get_url(f"/eduedge-result-verify?{query}")
	return {
		"issue": issue_name,
		"url": url,
		"qr_data_uri": get_qr_code(url),
	}


def verify_issued_report_card(issue_name: str | None, token: str | None) -> dict:
	issue_name = (issue_name or "").strip()
	token = (token or "").strip()
	if not issue_name or not token:
		return _invalid(_("Verification information is incomplete."))

	row = frappe.db.get_value(
		ISSUE_DOCTYPE,
		issue_name,
		[
			"name",
			"result_publication",
			"publication_version",
			"report_card_review",
			"issue_version",
			"student",
			"student_name",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"result_mode",
			"result_profile",
			"verification_token",
			"payload_hash",
			"payload_json",
			"issued_on",
		],
		as_dict=True,
	)
	if not row or not row.verification_token or not hmac.compare_digest(str(row.verification_token), token):
		return _invalid(_("This verification code is not valid."))

	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if not hmac.compare_digest(actual_hash, str(row.payload_hash or "")):
		return _invalid(_("The issued report-card integrity check failed."))

	try:
		payload = json.loads(row.payload_json or "{}")
	except (TypeError, ValueError):
		return _invalid(_("The issued report-card payload is unreadable."))

	review_status = frappe.db.get_value(
		"EduEdge Report Card Review",
		row.report_card_review,
		"progression_status",
	)
	latest_rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": row.result_publication, "student": row.student},
		fields=["name", "issue_version"],
		order_by="issue_version desc, creation desc",
		limit=1,
	)
	latest_issue = latest_rows[0] if latest_rows else None
	if latest_issue and latest_issue.name != row.name:
		status = "Superseded"
		status_message = _("This is an authentic earlier issue. A newer official issue exists.")
	elif review_status != "Approved":
		status = "Review Reopened"
		status_message = _("This is an authentic issued report, but its review has subsequently been reopened.")
	else:
		status = "Current"
		status_message = _("This is the current authentic issued report card.")

	branding = payload.get("branding") or {}
	institution = payload.get("institution") or {}
	publication = payload.get("publication") or {}
	summary = payload.get("summary") or {}
	student = payload.get("student") or {}
	return {
		"valid": True,
		"status": status,
		"status_message": status_message,
		"issue": row.name,
		"issue_version": int(row.issue_version or 1),
		"publication_version": int(row.publication_version or 1),
		"institution_name": branding.get("official_name")
		or institution.get("official_name")
		or institution.get("institution_name")
		or "",
		"branch_name": branding.get("branch_name") or "",
		"student_name": student.get("student_name") or row.student_name or "",
		"student_id": student.get("name") or row.student or "",
		"student_group": publication.get("student_group") or row.student_group or "",
		"academic_year": publication.get("academic_year") or row.academic_year or "",
		"academic_term": summary.get("academic_term_label")
		or publication.get("academic_term_label")
		or publication.get("academic_term")
		or row.academic_term
		or "",
		"result_mode": publication.get("result_mode") or row.result_mode or "Terminal",
		"issued_on": str(row.issued_on or ""),
		"fingerprint": str(row.payload_hash or "")[:16].upper(),
	}


def _invalid(message: str) -> dict:
	return {
		"valid": False,
		"status": "Invalid",
		"status_message": message,
	}
