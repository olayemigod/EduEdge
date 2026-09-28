from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.report_card_issues import resolve_report_card_pdf
from eduedge.education.report_cards import get_student_report_card_payload
from eduedge.services.institution_branding import get_report_identity


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _attach_institution_identity(payload: dict) -> dict:
	if (
		(payload.get("issue") or payload.get("issue_record"))
		and payload.get("branding")
		and payload.get("terminology")
	):
		return payload
	branch_name = (payload.get("branch") or {}).get("name")
	identity = get_report_identity(branch=branch_name)
	payload["institution"] = identity["institution"]
	payload["branding"] = identity["branding"]
	payload["terminology"] = identity["terminology"]
	if identity.get("address"):
		payload["address"] = identity["address"]
	return payload

@frappe.whitelist()
def get_report_card(publication: str, student: str) -> dict:
	_require_login()
	return _attach_institution_identity(
		get_student_report_card_payload(publication, student)
	)


@frappe.whitelist()
def preview_report_card(publication: str, student: str) -> None:
	_require_login()
	payload = _attach_institution_identity(
		get_student_report_card_payload(publication, student)
	)
	frappe.response.filename = f"Report Card {student}.pdf"
	frappe.response.filecontent = resolve_report_card_pdf(payload)
	frappe.response.type = "pdf"
