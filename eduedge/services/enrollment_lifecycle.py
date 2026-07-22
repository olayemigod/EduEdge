from __future__ import annotations

import frappe

from eduedge.education.academic_fields import OFFERING_FIELD

CAPACITY_CONSUMING_STATUSES = {"Active", "Suspended"}


def get_current_enrollment_status(program_enrollment: str) -> str:
	if not frappe.db.exists("DocType", "EduEdge Enrollment Status Log"):
		return "Active"
	status = frappe.db.sql(
		"""
		select new_status
		from `tabEduEdge Enrollment Status Log`
		where program_enrollment = %s
		order by effective_date desc, creation desc
		limit 1
		""",
		(program_enrollment,),
	)
	return status[0][0] if status else "Active"


def count_capacity_consuming_enrollments(
	program_offering: str,
	*,
	exclude_enrollment: str | None = None,
) -> int:
	if not frappe.db.exists("DocType", "EduEdge Enrollment Status Log"):
		return frappe.db.count(
			"Program Enrollment",
			{
				OFFERING_FIELD: program_offering,
				"docstatus": 1,
				"name": ["!=", exclude_enrollment or ""],
			},
		)
	params = {
		"offering": program_offering,
		"exclude_enrollment": exclude_enrollment or "",
		"active": "Active",
		"suspended": "Suspended",
	}
	rows = frappe.db.sql(
		f"""
		select count(*)
		from `tabProgram Enrollment` enrollment
		where enrollment.`{OFFERING_FIELD}` = %(offering)s
			and enrollment.docstatus = 1
			and enrollment.name != %(exclude_enrollment)s
			and coalesce(
				(
					select status_log.new_status
					from `tabEduEdge Enrollment Status Log` status_log
					where status_log.program_enrollment = enrollment.name
					order by status_log.effective_date desc, status_log.creation desc
					limit 1
				),
				%(active)s
			) in (%(active)s, %(suspended)s)
		""",
		params,
	)
	return int(rows[0][0] or 0) if rows else 0
