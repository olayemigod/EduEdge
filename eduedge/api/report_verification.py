from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _

from eduedge.education.report_card_issues import ISSUE_DOCTYPE


def _safe_text(value) -> str:
	return str(value or "").strip()


def _latest_issue_name(publication: str, student: str) -> str | None:
	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"result_publication": publication, "student": student},
		fields=["name"],
		order_by="issue_version desc, creation desc",
		limit=1,
	)
	return rows[0].name if rows else None


@frappe.whitelist(allow_guest=True)
def verify_report_card(code: str | None = None) -> dict:
	code = _safe_text(code)
	if not code or len(code) > 128:
		return {
			"found": False,
			"authentic": False,
			"current": False,
			"status": "Invalid",
			"message": _("Enter a valid report-card verification code."),
		}

	row = frappe.db.get_value(
		ISSUE_DOCTYPE,
		{"verification_code": code},
		[
			"name",
			"result_publication",
			"publication_version",
			"report_card_review",
			"issue_version",
			"student",
			"student_name",
			"student_group",
			"academic_year",
			"academic_term",
			"result_mode",
			"payload_hash",
			"payload_json",
			"issued_on",
		],
		as_dict=True,
	)
	if not row:
		return {
			"found": False,
			"authentic": False,
			"current": False,
			"status": "Not Found",
			"message": _("No issued EduEdge report card matches this verification code."),
		}

	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if actual_hash != row.payload_hash:
		return {
			"found": True,
			"authentic": False,
			"current": False,
			"status": "Integrity Check Failed",
			"message": _("The issued report-card payload failed its integrity check."),
		}

	try:
		payload = json.loads(row.payload_json or "{}")
	except (TypeError, ValueError):
		return {
			"found": True,
			"authentic": False,
			"current": False,
			"status": "Integrity Check Failed",
			"message": _("The issued report-card payload is not readable."),
		}

	review_status = frappe.db.get_value(
		"EduEdge Report Card Review",
		row.report_card_review,
		"progression_status",
	)
	latest_issue = _latest_issue_name(row.result_publication, row.student)
	if review_status != "Approved":
		status = "Under Review"
		current = False
		message = _("This report card was issued previously but is not currently approved.")
	elif latest_issue != row.name:
		status = "Superseded"
		current = False
		message = _("This report card is authentic but has been superseded by a newer issued version.")
	else:
		status = "Current"
		current = True
		message = _("This is the current authentic issued report card.")

	branding = payload.get("branding") or {}
	institution = payload.get("institution") or {}
	branch = payload.get("branch") or {}
	publication = payload.get("publication") or {}
	student = payload.get("student") or {}

	return {
		"found": True,
		"authentic": True,
		"current": current,
		"status": status,
		"message": message,
		"report_card": {
			"issue": row.name,
			"issue_version": int(row.issue_version or 1),
			"publication_version": int(row.publication_version or 1),
			"student_name": student.get("student_name") or row.student_name,
			"student_id": student.get("name") or row.student,
			"student_group": publication.get("student_group") or row.student_group,
			"academic_year": publication.get("academic_year") or row.academic_year,
			"academic_term": publication.get("academic_term_label") or publication.get("academic_term") or row.academic_term,
			"result_mode": publication.get("result_mode") or row.result_mode,
			"institution_name": branding.get("official_name")
				or institution.get("official_name")
				or institution.get("institution_name"),
			"branch_name": branch.get("branch_name") or branch.get("name"),
			"issued_on": str(row.issued_on or ""),
		},
	}
