from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

CLASS_SCOPE = "Class / Programme Offering"
CLASS_ARM_SCOPE = "Class Arm"
ACADEMIC_ASSIGNMENT_SCOPES = {CLASS_SCOPE, CLASS_ARM_SCOPE}
COURSE_REQUIRED_TYPES = {
	"Subject Teacher",
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
}


def ensure_teaching_assignment_foundation() -> None:
	if not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
		return
	meta = frappe.get_meta("EduEdge Instructor Assignment")
	if not meta.has_field("assignment_scope"):
		return
	frappe.db.sql(
		"""
		update `tabEduEdge Instructor Assignment`
		set assignment_scope = case
			when ifnull(student_group, '') != '' then %s
			else %s
		end
		where ifnull(assignment_scope, '') = ''
		""",
		(CLASS_ARM_SCOPE, CLASS_SCOPE),
	)


def current_user_instructors(user: str | None = None) -> list[str]:
	resolved = user or frappe.session.user
	if not resolved or resolved == "Guest" or not frappe.db.exists("DocType", "Instructor"):
		return []
	instructors: set[str] = set()
	meta = frappe.get_meta("Instructor")
	if meta.has_field("eduedge_email"):
		instructors.update(
			frappe.get_all(
				"Instructor",
				filters={"eduedge_email": resolved, "status": "Active"},
				pluck="name",
				limit_page_length=0,
			)
		)
	if frappe.db.exists("DocType", "Employee") and frappe.get_meta("Employee").has_field("user_id"):
		employees = frappe.get_all(
			"Employee",
			filters={"user_id": resolved, "status": "Active"},
			pluck="name",
			limit_page_length=0,
		)
		if employees:
			instructors.update(
				frappe.get_all(
					"Instructor",
					filters={"employee": ["in", employees], "status": "Active"},
					pluck="name",
					limit_page_length=0,
				)
			)
	return sorted(instructors)


def _active_on(row, on_date=None) -> bool:
	day = getdate(on_date or nowdate())
	return (not row.get("valid_from") or getdate(row.valid_from) <= day) and (
		not row.get("valid_to") or getdate(row.valid_to) >= day
	)


def active_assignment_rows(
	user: str | None = None,
	*,
	instructors: Iterable[str] | None = None,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	on_date=None,
) -> list[dict]:
	resolved_instructors = sorted(set(instructors or current_user_instructors(user)))
	if not resolved_instructors or not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
		return []
	filters: dict = {"instructor": ["in", resolved_instructors], "enabled": 1}
	if branch:
		filters["school_branch"] = branch
	if program_offering:
		filters["program_offering"] = program_offering
	if course:
		filters["course"] = course
	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters=filters,
		fields=[
			"name",
			"assignment_title",
			"instructor",
			"instructor_name",
			"assignment_type",
			"assignment_scope",
			"school_branch",
			"institution",
			"program_offering",
			"student_group",
			"course",
			"academic_year",
			"academic_term",
			"valid_from",
			"valid_to",
		],
		order_by="modified desc",
		limit_page_length=0,
	)
	result = [row for row in rows if _active_on(row, on_date)]
	if student_group:
		result = [
			row
			for row in result
			if (
				(row.get("assignment_scope") or CLASS_ARM_SCOPE) == CLASS_SCOPE
				or row.get("student_group") == student_group
			)
		]
	return result


def assigned_course_rows(
	user: str | None = None,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> list[dict]:
	return [
		row
		for row in active_assignment_rows(
			user,
			branch=branch,
			program_offering=program_offering,
			student_group=student_group,
		)
		if row.get("course")
	]


def assigned_courses(
	user: str | None = None,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> set[str]:
	return {
		row.course
		for row in assigned_course_rows(user, branch, program_offering, student_group)
		if row.get("course")
	}


def has_course_assignment(
	course: str,
	*,
	user: str | None = None,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> bool:
	return course in assigned_courses(user, branch, program_offering, student_group)


def require_course_assignment(
	course: str,
	*,
	user: str | None = None,
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
) -> None:
	if has_course_assignment(
		course,
		user=user,
		branch=branch,
		program_offering=program_offering,
		student_group=student_group,
	):
		return
	frappe.throw(
		_("This Subject / Course is not assigned to you for the selected Class or Class Arm."),
		frappe.PermissionError,
	)


def assignment_scope_label(row) -> str:
	scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
	if scope == CLASS_SCOPE:
		return row.get("program_offering") or _("Class / Programme Offering")
	return row.get("student_group") or _("Class Arm")
