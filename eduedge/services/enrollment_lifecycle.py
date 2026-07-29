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


def get_capacity_consuming_enrollment_counts(program_offerings: list[str]) -> dict[str, int]:
	"""Return occupied-seat counts for multiple Offerings in one query.

	The page catalogue can display up to 50 Offerings. Counting each Offering
	individually produces an avoidable N+1 query pattern, so list/read surfaces
	use this grouped helper while submit-time capacity checks retain row locking.
	"""
	offerings = list(dict.fromkeys(value for value in program_offerings if value))
	if not offerings:
		return {}

	if not frappe.db.exists("DocType", "EduEdge Enrollment Status Log"):
		rows = frappe.get_all(
			"Program Enrollment",
			filters={
				OFFERING_FIELD: ["in", offerings],
				"docstatus": 1,
			},
			fields=[OFFERING_FIELD, {"COUNT": "name", "as": "record_count"}],
			group_by=OFFERING_FIELD,
			limit_page_length=len(offerings),
		)
		return {row.get(OFFERING_FIELD): int(row.record_count or 0) for row in rows}

	placeholders = ", ".join(["%s"] * len(offerings))
	rows = frappe.db.sql(
		f"""
		select enrollment.`{OFFERING_FIELD}` as program_offering, count(*) as record_count
		from `tabProgram Enrollment` enrollment
		where enrollment.`{OFFERING_FIELD}` in ({placeholders})
			and enrollment.docstatus = 1
			and coalesce(
				(
					select status_log.new_status
					from `tabEduEdge Enrollment Status Log` status_log
					where status_log.program_enrollment = enrollment.name
					order by status_log.effective_date desc, status_log.creation desc
					limit 1
				),
				%s
			) in (%s, %s)
		group by enrollment.`{OFFERING_FIELD}`
		""",
		(*offerings, "Active", "Active", "Suspended"),
		as_dict=True,
	)
	return {row.program_offering: int(row.record_count or 0) for row in rows}


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
					order by status_log.effective_date desc, creation desc
					limit 1
				),
				%(active)s
			) in (%(active)s, %(suspended)s)
		""",
		params,
	)
	return int(rows[0][0] or 0) if rows else 0
