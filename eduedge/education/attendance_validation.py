from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_operations import before_validate_student_attendance as validate_attendance
from eduedge.education.custom_fields import BRANCH_FIELD


def before_validate_student_attendance(doc, method=None) -> None:
	_resolve_exact_schedule(doc)
	validate_attendance(doc, method)


def _resolve_exact_schedule(doc) -> None:
	"""Bind direct-form attendance to the only matching schedule, or fail closed.

	Unscheduled attendance remains valid only when no Course Schedule exists for the
	exact Student Group and date. This keeps direct forms/API calls aligned with the
	EduEdge attendance register page and prevents parallel scheduled/unscheduled rows.
	"""
	if doc.get("course_schedule") or not doc.get("student_group") or not doc.get("date"):
		return
	filters = {
		"student_group": doc.student_group,
		"schedule_date": doc.date,
	}
	group_branch = frappe.db.get_value("Student Group", doc.student_group, BRANCH_FIELD)
	if group_branch and frappe.get_meta("Course Schedule").has_field(BRANCH_FIELD):
		filters[BRANCH_FIELD] = group_branch
	matches = frappe.get_all(
		"Course Schedule",
		filters=filters,
		fields=["name"],
		order_by="from_time asc, name asc",
		limit_page_length=2,
	)
	if len(matches) == 1:
		doc.course_schedule = matches[0].name
		return
	if len(matches) > 1:
		frappe.throw(
			_("More than one Course Schedule exists for this Class and date. Select the exact scheduled session before saving attendance."),
			frappe.ValidationError,
		)
