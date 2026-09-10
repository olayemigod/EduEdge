from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
)

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


def assert_schedule_instructor_assignment(doc) -> dict | None:
	"""Require an exact effective Subject teaching responsibility for Course Schedule.

	Branch Eligibility answers whether an Instructor may work at a Branch. This check
	answers the narrower operational question: may this Instructor teach this Subject
	for this Class/Class Arm on this schedule date? Class responsibilities without a
	Subject never authorise a Subject lesson.
	"""
	if not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE):
		return None
	branch = doc.get(BRANCH_FIELD)
	student_group = doc.get("student_group")
	instructor = doc.get("instructor")
	course = doc.get("course")
	if not branch or not student_group or not instructor or not course:
		return None

	# Migration-safe activation: a Branch that has not started using Academic
	# Instructor Assignments keeps the existing Branch Eligibility behavior. Once one
	# academic assignment exists in the Branch, schedule selection is exact and
	# authoritative for every new/edited Course Schedule there.
	if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch}):
		return None

	program_offering = _group_offering(student_group)
	if not program_offering:
		frappe.throw(
			_("The selected Class Arm has no unambiguous Class / Programme Offering. Correct the Class Arm before scheduling a lesson."),
			frappe.ValidationError,
		)

	reference_date = getdate(doc.schedule_date) if doc.get("schedule_date") else None
	filters = {
		"school_branch": branch,
		"program_offering": program_offering,
		"instructor": instructor,
		"course": course,
		"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
		"enabled": 1,
	}
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"assignment_title",
			"assignment_type",
			"assignment_scope",
			"program_offering",
			"student_group",
			"course",
			"valid_from",
			"valid_to",
		],
		limit_page_length=100,
	)
	for row in rows:
		scope = row.assignment_scope or CLASS_ARM_SCOPE
		if scope == CLASS_SCOPE:
			pass
		elif scope == CLASS_ARM_SCOPE and row.student_group == student_group:
			pass
		else:
			continue
		if reference_date and row.valid_from and getdate(row.valid_from) > reference_date:
			continue
		if reference_date and row.valid_to and getdate(row.valid_to) < reference_date:
			continue
		return dict(row)

	frappe.throw(
		_(
			"Instructor {0} has no effective Subject Instructor Assignment for Class {1}, Class Arm {2}, Subject {3}, and the selected date."
		).format(
			instructor,
			program_offering,
			student_group,
			course,
		),
		frappe.ValidationError,
	)
