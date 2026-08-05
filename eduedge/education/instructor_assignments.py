from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from eduedge.education.custom_fields import BRANCH_FIELD

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"


def assert_schedule_instructor_assignment(doc) -> None:
	"""Require an operational assignment after a Branch starts using the new register.

	Existing sites remain backward compatible until the first enabled operational
	Instructor Assignment is created for a Branch. From that point, new or changed
	Course Schedules in the Branch must match the assigned Instructor, Class Arm,
	Course and effective dates.
	"""
	if not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE):
		return
	branch = doc.get(BRANCH_FIELD)
	if not branch or not doc.get("student_group") or not doc.get("instructor"):
		return
	if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch, "enabled": 1}):
		return

	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			"school_branch": branch,
			"student_group": doc.student_group,
			"instructor": doc.instructor,
			"enabled": 1,
		},
		fields=["name", "course", "valid_from", "valid_to"],
		limit_page_length=100,
	)
	reference_date = getdate(doc.schedule_date) if doc.get("schedule_date") else None
	for row in rows:
		if row.course and row.course != doc.get("course"):
			continue
		if reference_date and row.valid_from and getdate(row.valid_from) > reference_date:
			continue
		if reference_date and row.valid_to and getdate(row.valid_to) < reference_date:
			continue
		return

	frappe.throw(
		_(
			"Instructor {0} has no active Instructor Assignment for Class Arm {1}, Course {2}, and the selected date."
		).format(doc.instructor, doc.student_group, doc.get("course") or _("Whole Class")),
		frappe.ValidationError,
	)
