from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

BRANCH_FIELD = "eduedge_school_branch"

EDUCATION_CUSTOM_FIELDS = {
	"Student Admission": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "academic_year",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Branch or campus publishing this admission.",
		},
	],
	"Student Applicant": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "program",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Branch or campus handling this application.",
		},
	],
	"Student": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "student_applicant",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Primary branch or campus responsible for this student.",
		},
	],
	"Program Enrollment": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "student_name",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Inherited from the selected Student and protected by backend validation.",
		},
	],
	"Student Group": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "academic_year",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Branch or campus responsible for this class or student group.",
		},
	],
	"Room": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "room_name",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Branch or campus where this room is located.",
		},
	],
	"Course Schedule": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "student_group",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Inherited from the selected Student Group.",
		},
	],
	"Student Attendance": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "student_group",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Inherited from the Student Group or Course Schedule.",
		},
	],
	"Assessment Plan": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "student_group",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Inherited from the selected Student Group.",
		},
	],
	"Assessment Result": [
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": "assessment_plan",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Inherited from the Assessment Plan and Student.",
		},
	],
}


def ensure_education_custom_fields() -> None:
	"""Create or update EduEdge fields without changing upstream Education schemas."""
	create_custom_fields(EDUCATION_CUSTOM_FIELDS, update=True)


def backfill_education_branch_context() -> None:
	"""Backfill only deterministic branch values; ambiguous records remain unassigned."""
	if not _custom_fields_are_available():
		return

	default_branch = _get_deterministic_default_branch()
	if default_branch:
		for doctype in ("Student Admission", "Student Applicant", "Student", "Room"):
			frappe.db.sql(
				f"""
				update `tab{doctype}`
				set `{BRANCH_FIELD}` = %s
				where coalesce(`{BRANCH_FIELD}`, '') = ''
				""",
				(default_branch,),
			)

	frappe.db.sql(
		f"""
		update `tabStudent Applicant` applicant
		inner join `tabStudent Admission` admission
			on admission.name = applicant.student_admission
		set applicant.`{BRANCH_FIELD}` = admission.`{BRANCH_FIELD}`
		where coalesce(applicant.`{BRANCH_FIELD}`, '') = ''
			and coalesce(admission.`{BRANCH_FIELD}`, '') != ''
		"""
	)

	frappe.db.sql(
		f"""
		update `tabStudent` student
		inner join `tabStudent Applicant` applicant
			on applicant.name = student.student_applicant
		set student.`{BRANCH_FIELD}` = applicant.`{BRANCH_FIELD}`
		where coalesce(student.`{BRANCH_FIELD}`, '') = ''
			and coalesce(applicant.`{BRANCH_FIELD}`, '') != ''
		"""
	)

	frappe.db.sql(
		f"""
		update `tabProgram Enrollment` enrollment
		inner join `tabStudent` student on student.name = enrollment.student
		set enrollment.`{BRANCH_FIELD}` = student.`{BRANCH_FIELD}`
		where coalesce(enrollment.`{BRANCH_FIELD}`, '') = ''
			and coalesce(student.`{BRANCH_FIELD}`, '') != ''
		"""
	)

	_backfill_student_groups(default_branch)
	_backfill_course_schedules()
	_backfill_student_attendance()
	_backfill_assessment_plans()
	_backfill_assessment_results()


def _backfill_student_groups(default_branch: str | None) -> None:
	frappe.db.sql(
		f"""
		update `tabStudent Group` student_group
		inner join (
			select group_student.parent,
				min(student.`{BRANCH_FIELD}`) as branch,
				count(distinct student.`{BRANCH_FIELD}`) as branch_count
			from `tabStudent Group Student` group_student
			inner join `tabStudent` student on student.name = group_student.student
			where coalesce(student.`{BRANCH_FIELD}`, '') != ''
			group by group_student.parent
			having branch_count = 1
		) resolved on resolved.parent = student_group.name
		set student_group.`{BRANCH_FIELD}` = resolved.branch
		where coalesce(student_group.`{BRANCH_FIELD}`, '') = ''
		"""
	)
	if default_branch:
		frappe.db.sql(
			f"""
			update `tabStudent Group`
			set `{BRANCH_FIELD}` = %s
			where coalesce(`{BRANCH_FIELD}`, '') = ''
			""",
			(default_branch,),
		)


def _backfill_course_schedules() -> None:
	frappe.db.sql(
		f"""
		update `tabCourse Schedule` schedule
		inner join `tabStudent Group` student_group on student_group.name = schedule.student_group
		set schedule.`{BRANCH_FIELD}` = student_group.`{BRANCH_FIELD}`
		where coalesce(schedule.`{BRANCH_FIELD}`, '') = ''
			and coalesce(student_group.`{BRANCH_FIELD}`, '') != ''
		"""
	)


def _backfill_student_attendance() -> None:
	frappe.db.sql(
		f"""
		update `tabStudent Attendance` attendance
		left join `tabCourse Schedule` schedule on schedule.name = attendance.course_schedule
		left join `tabStudent Group` student_group on student_group.name = attendance.student_group
		left join `tabStudent` student on student.name = attendance.student
		set attendance.`{BRANCH_FIELD}` = coalesce(
			nullif(schedule.`{BRANCH_FIELD}`, ''),
			nullif(student_group.`{BRANCH_FIELD}`, ''),
			nullif(student.`{BRANCH_FIELD}`, '')
		)
		where coalesce(attendance.`{BRANCH_FIELD}`, '') = ''
			and coalesce(
				nullif(schedule.`{BRANCH_FIELD}`, ''),
				nullif(student_group.`{BRANCH_FIELD}`, ''),
				nullif(student.`{BRANCH_FIELD}`, '')
			) is not null
		"""
	)


def _backfill_assessment_plans() -> None:
	frappe.db.sql(
		f"""
		update `tabAssessment Plan` plan
		inner join `tabStudent Group` student_group on student_group.name = plan.student_group
		set plan.`{BRANCH_FIELD}` = student_group.`{BRANCH_FIELD}`
		where coalesce(plan.`{BRANCH_FIELD}`, '') = ''
			and coalesce(student_group.`{BRANCH_FIELD}`, '') != ''
		"""
	)


def _backfill_assessment_results() -> None:
	frappe.db.sql(
		f"""
		update `tabAssessment Result` result
		left join `tabAssessment Plan` plan on plan.name = result.assessment_plan
		left join `tabStudent` student on student.name = result.student
		set result.`{BRANCH_FIELD}` = coalesce(
			nullif(plan.`{BRANCH_FIELD}`, ''),
			nullif(student.`{BRANCH_FIELD}`, '')
		)
		where coalesce(result.`{BRANCH_FIELD}`, '') = ''
			and coalesce(
				nullif(plan.`{BRANCH_FIELD}`, ''),
				nullif(student.`{BRANCH_FIELD}`, '')
			) is not null
		"""
	)


def _custom_fields_are_available() -> bool:
	return all(
		frappe.get_meta(doctype).has_field(BRANCH_FIELD)
		for doctype in EDUCATION_CUSTOM_FIELDS
	)


def _get_deterministic_default_branch() -> str | None:
	settings_branch = frappe.db.get_single_value("EduEdge Settings", "default_school_branch")
	if settings_branch and frappe.db.get_value(
		"EduEdge School Branch", settings_branch, "enabled"
	):
		return settings_branch

	branches = frappe.get_all(
		"EduEdge School Branch",
		filters={"enabled": 1},
		pluck="name",
		limit=2,
	)
	return branches[0] if len(branches) == 1 else None
