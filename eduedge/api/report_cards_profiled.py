from __future__ import annotations

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

from eduedge.education.report_cards import get_student_report_card_payload
from eduedge.services.institution_branding import get_institution_branding


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _attach_institution_identity(payload: dict) -> dict:
	branch = payload.get("branch") or {}
	branch_name = branch.get("name")
	institution_name = None
	if branch_name:
		institution_name = frappe.db.get_value(
			"EduEdge School Branch", branch_name, "institution"
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
