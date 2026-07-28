from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import nowdate

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import (
	PURPOSE_FIELD,
	parse_query_filters,
	resolve_query_branch,
)
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)

CROSS_BRANCH_ENROLLMENT_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
	"Registrar",
	"Admission Officer",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def school_branch_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	rows = get_allowed_school_branches(
		company=filters.get("company"),
		institution=filters.get("institution"),
	)
	needle = (txt or "").strip().lower()
	if needle:
		rows = [
			row
			for row in rows
			if needle
			in " ".join(
				str(row.get(key) or "")
				for key in (
					"name",
					"branch_name",
					"branch_code",
					"company",
					"institution",
					"institution_name",
				)
			).lower()
		]
	rows = rows[int(start) : int(start) + int(page_len)]
	return [
		[
			row["name"],
			row.get("branch_name"),
			row.get("branch_code"),
			row.get("institution_name") or row.get("institution"),
			row.get("company"),
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	branch = resolve_query_branch(filters)
	academic_year = filters.get("academic_year")
	academic_term = filters.get("academic_term")
	purpose = filters.get("purpose") or "admission"
	if purpose not in PURPOSE_FIELD:
		frappe.throw(_("Invalid program availability purpose."), frappe.ValidationError)
	if not branch or not academic_year:
		return []

	purpose_field = PURPOSE_FIELD[purpose]
	term_condition = ""
	params = {
		"branch": branch,
		"academic_year": academic_year,
		"txt": f"%{txt or ''}%",
	}
	if academic_term:
		term_condition = (
			"and (coalesce(offering.academic_term, '') = '' "
			"or offering.academic_term = %(academic_term)s)"
		)
		params["academic_term"] = academic_term

	return frappe.db.sql(
		f"""
		select distinct program.name, program.program_name
		from `tabProgram` program
		inner join `tabEduEdge Program Offering` offering
			on offering.program = program.name
		where offering.school_branch = %(branch)s
			and offering.academic_year = %(academic_year)s
			and offering.is_active = 1
			and offering.`{purpose_field}` = 1
			{term_condition}
			and (
				program.name like %(txt)s
				or program.program_name like %(txt)s
				or coalesce(program.program_abbreviation, '') like %(txt)s
			)
		order by program.program_name asc
		limit {int(start)}, {int(page_len)}
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_admission_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	branch = resolve_query_branch(filters)
	academic_year = filters.get("academic_year")
	program = filters.get("program")
	if not branch or not academic_year:
		return []

	program_join = ""
	program_condition = ""
	params = {
		"branch": branch,
		"academic_year": academic_year,
		"txt": f"%{txt or ''}%",
		"today": nowdate(),
	}
	if program:
		program_join = """
		inner join `tabStudent Admission Program` admission_program
			on admission_program.parent = admission.name
			and admission_program.parenttype = 'Student Admission'
		"""
		program_condition = "and admission_program.program = %(program)s"
		params["program"] = program

	return frappe.db.sql(
		f"""
		select distinct admission.name, admission.title
		from `tabStudent Admission` admission
		{program_join}
		where admission.docstatus = 1
			and admission.{BRANCH_FIELD} = %(branch)s
			and admission.academic_year = %(academic_year)s
			and admission.application_start_date <= %(today)s
			and admission.application_end_date >= %(today)s
			{program_condition}
			and (
				admission.name like %(txt)s
				or admission.title like %(txt)s
			)
		order by admission.application_end_date desc, admission.title asc
		limit {int(start)}, {int(page_len)}
		""",
		params,
	)
