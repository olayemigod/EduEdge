from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, parse_query_filters

ACADEMIC_OPERATOR_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
	"Instructor",
	"Teacher",
}


def _require_operator() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not ACADEMIC_OPERATOR_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to manage academic groups."), frappe.PermissionError)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_student_query(doctype, txt, searchfield, start, page_len, filters):
	_require_operator()
	filters = parse_query_filters(filters)
	branch = filters.get(BRANCH_FIELD)
	if not branch:
		return []
	assert_branch_access(branch)
	params = {
		"branch": branch,
		"offering": filters.get(OFFERING_FIELD),
		"academic_level": filters.get(ACADEMIC_LEVEL_FIELD),
		"academic_year": filters.get("academic_year"),
		"academic_term": filters.get("academic_term"),
		"program": filters.get("program"),
		"batch": filters.get("batch"),
		"student_category": filters.get("student_category"),
		"course": filters.get("course"),
		"txt": f"%{txt or ''}%",
		"start": int(start),
		"page_len": int(page_len),
	}
	conditions = ["enrollment.docstatus = 1", f"enrollment.`{BRANCH_FIELD}` = %(branch)s"]
	if filters.get(OFFERING_FIELD) and frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD):
		conditions.append(f"enrollment.`{OFFERING_FIELD}` = %(offering)s")
	else:
		for fieldname in ("academic_year", "academic_term", "program"):
			if filters.get(fieldname):
				conditions.append(f"enrollment.`{fieldname}` = %({fieldname})s")
		if filters.get(ACADEMIC_LEVEL_FIELD) and frappe.get_meta("Program Enrollment").has_field(ACADEMIC_LEVEL_FIELD):
			conditions.append(f"enrollment.`{ACADEMIC_LEVEL_FIELD}` = %(academic_level)s")
		if filters.get("batch"):
			conditions.append("enrollment.student_batch_name = %(batch)s")
	if filters.get("student_category"):
		conditions.append("enrollment.student_category = %(student_category)s")
	course_join = ""
	if filters.get("course"):
		course_join = """
		inner join `tabProgram Enrollment Course` enrollment_course
			on enrollment_course.parent = enrollment.name
			and enrollment_course.parenttype = 'Program Enrollment'
			and enrollment_course.course = %(course)s
		"""
	return frappe.db.sql(
		f"""
		select distinct student.name, student.student_name
		from `tabProgram Enrollment` enrollment
		inner join `tabStudent` student on student.name = enrollment.student
		{course_join}
		where {' and '.join(conditions)}
			and student.enabled = 1
			and (
				student.name like %(txt)s
				or student.student_name like %(txt)s
				or coalesce(student.student_email_id, '') like %(txt)s
			)
		order by student.student_name asc
		limit %(start)s, %(page_len)s
		""",
		params,
	)
