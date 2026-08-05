from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"


def _group_offering(student_group: str) -> str | None:
	meta = frappe.get_meta("Student Group")
	if meta.has_field(OFFERING_FIELD):
		value = frappe.db.get_value("Student Group", student_group, OFFERING_FIELD)
		if value:
			return value
	group = frappe.db.get_value(
		"Student Group",
		student_group,
		["program", "academic_year", "academic_term", BRANCH_FIELD],
		as_dict=True,
	)
	if not group:
		return None
	filters = {
		"program": group.program,
		"academic_year": group.academic_year,
		"school_branch": group.get(BRANCH_FIELD),
		"is_active": 1,
	}
	if group.academic_term:
		filters["academic_term"] = group.academic_term
	rows = frappe.get_all("EduEdge Program Offering", filters=filters, pluck="name", limit_page_length=2)
	return rows[0] if len(rows) == 1 else None


def assert_schedule_instructor_assignment(doc) -> None:
	"""Require a matching Class or Class Arm Teacher Assignment after activation."""
	if not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE):
		return
	branch = doc.get(BRANCH_FIELD)
	if not branch or not doc.get("student_group") or not doc.get("instructor"):
		return
	if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch, "enabled": 1}):
		return
	program_offering = _group_offering(doc.student_group)
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			"school_branch": branch,
			"instructor": doc.instructor,
			"enabled": 1,
		},
		fields=[
			"name", "assignment_scope", "program_offering", "student_group", "course", "valid_from", "valid_to"
		],
		limit_page_length=500,
	)
	reference_date = getdate(doc.schedule_date) if doc.get("schedule_date") else None
	for row in rows:
		scope = row.assignment_scope or CLASS_ARM_SCOPE
		if scope == CLASS_SCOPE:
			if not program_offering or row.program_offering != program_offering:
				continue
		elif row.student_group != doc.student_group:
			continue
		if row.course and row.course != doc.get("course"):
			continue
		if reference_date and row.valid_from and getdate(row.valid_from) > reference_date:
			continue
		if reference_date and row.valid_to and getdate(row.valid_to) < reference_date:
			continue
		return
	frappe.throw(
		_(
			"Instructor {0} has no active Teacher Assignment for Class {1}, Class Arm {2}, Subject {3}, and the selected date."
		).format(
			doc.instructor,
			program_offering or _("Unresolved"),
			doc.student_group,
			doc.get("course") or _("Whole Class"),
		),
		frappe.ValidationError,
	)
