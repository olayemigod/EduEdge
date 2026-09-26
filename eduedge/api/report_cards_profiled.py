from __future__ import annotations

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

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
	settings = frappe.get_single("EduEdge Settings")
	letter_head_name = (
		(payload.get("branding") or {}).get("report_card_letter_head")
		or settings.report_card_letter_head
	)
	letterhead = None
	if letter_head_name:
		letterhead = frappe.db.get_value("Letter Head", letter_head_name, "content")

	html = frappe.render_template(
		"eduedge/templates/report_card.html",
		{
			**payload,
			"letterhead": letterhead,
			"show_marks": bool(settings.report_card_show_marks),
		},
	)
	final_html = frappe.render_template(
		"frappe/www/printview.html",
		{"body": html, "title": _("Student Report Card")},
	)
	frappe.response.filename = f"Report Card {student}.pdf"
	frappe.response.filecontent = get_pdf(final_html)
	frappe.response.type = "pdf"
