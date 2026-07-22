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
	rows = get_allowed_school_branches(company=filters.get("company"))
	needle = (txt or "").strip().lower()
	if needle:
		rows = [
			row
			for row in rows
			if needle
			in " ".join(
				str(row.get(key) or "")
				for key in ("name", "branch_name", "branch_code", "company")
			).lower()
		]
	rows = rows[int(start) : int(start) + int(page_len)]
	return [
		[row["name"], row.get("branch_name"), row.get("branch_code"), row.get("company")]
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
		where admission.`{BRANCH_FIELD}` = %(branch)s
			and admission.academic_year = %(academic_year)s
			and admission.enable_admission_application = 1
			and (
				coalesce(admission.admission_start_date, '') = ''
				or admission.admission_start_date <= %(today)s
			)
			and (
				coalesce(admission.admission_end_date, '') = ''
				or admission.admission_end_date >= %(today)s
			)
			{program_condition}
			and (
				admission.name like %(txt)s
				or coalesce(admission.title, '') like %(txt)s
			)
		order by admission.admission_end_date asc, admission.title asc
		limit {int(start)}, {int(page_len)}
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	branch = filters.get(BRANCH_FIELD)
	allowed = {row["name"] for row in get_allowed_school_branches()}
	if branch and branch not in allowed:
		frappe.throw(_("You do not have access to the selected School Branch."), frappe.PermissionError)
	if not branch:
		current = get_current_school_branch()
		branch = current.get("name") if current else None

	allow_cross_branch = str(filters.get("allow_cross_branch") or "").lower() in {"1", "true", "yes", "on"}
	if allow_cross_branch:
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(CROSS_BRANCH_ENROLLMENT_ROLES):
			frappe.throw(_("You are not permitted to enroll students across Branches."), frappe.PermissionError)
		if not branch:
			return []
		institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
		if not institution:
			return []
		return frappe.db.sql(
			f"""
			select student.name, student.student_name, student.student_email_id, student.`{BRANCH_FIELD}`
			from `tabStudent` student
			inner join `tabEduEdge School Branch` home_branch
				on home_branch.name = student.`{BRANCH_FIELD}`
			where student.enabled = 1
				and home_branch.institution = %(institution)s
				and (
					student.name like %(txt)s
					or student.student_name like %(txt)s
					or coalesce(student.student_email_id, '') like %(txt)s
				)
			order by student.student_name asc
			limit %(start)s, %(page_len)s
			""",
			{
				"institution": institution,
				"txt": f"%{txt or ''}%",
				"start": int(start),
				"page_len": int(page_len),
			},
		)

	student_filters: dict = {"enabled": 1}
	if branch:
		student_filters[BRANCH_FIELD] = branch
	rows = frappe.get_list(
		"Student",
		filters=student_filters,
		or_filters={
			"name": ["like", f"%{txt}%"],
			"student_name": ["like", f"%{txt}%"],
			"student_email_id": ["like", f"%{txt}%"],
		},
		fields=["name", "student_name", "student_email_id", BRANCH_FIELD],
		start=int(start),
		page_length=int(page_len),
		order_by="student_name asc",
	)
	return [
		[row["name"], row.get("student_name"), row.get("student_email_id"), row.get(BRANCH_FIELD)]
		for row in rows
	]


@frappe.whitelist()
def get_guardian_branch_summary(guardian: str) -> dict:
	_require_login()
	if not frappe.has_permission("Guardian", "read", guardian):
		frappe.throw(_("Not permitted to read this Guardian."), frappe.PermissionError)
	students = frappe.get_all(
		"Guardian Student",
		filters={"parent": guardian, "parenttype": "Guardian"},
		pluck="student",
	)
	if not students:
		return {"guardian": guardian, "branches": [], "students": []}
	rows = frappe.get_list(
		"Student",
		filters={"name": ["in", students]},
		fields=["name", "student_name", BRANCH_FIELD],
		order_by="student_name asc",
	)
	branches = sorted({row.get(BRANCH_FIELD) for row in rows if row.get(BRANCH_FIELD)})
	return {"guardian": guardian, "branches": branches, "students": rows}
