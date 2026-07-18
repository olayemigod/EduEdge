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
		frappe.db.sql(
			f"""
			update `tabStudent Admission`
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

	if default_branch:
		frappe.db.sql(
			f"""
			update `tabStudent Applicant`
			set `{BRANCH_FIELD}` = %s
			where coalesce(`{BRANCH_FIELD}`, '') = ''
			""",
			(default_branch,),
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

	if default_branch:
		frappe.db.sql(
			f"""
			update `tabStudent`
			set `{BRANCH_FIELD}` = %s
			where coalesce(`{BRANCH_FIELD}`, '') = ''
			""",
			(default_branch,),
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
