from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import academic_operations_safe as safe


def _rows(value) -> list[dict]:
	rows = frappe.parse_json(value) if isinstance(value, str) else value
	return rows if isinstance(rows, list) else []


def _schedule_context(course_schedule: str | None) -> tuple[str, str]:
	if not course_schedule:
		return "", ""
	schedule = safe._get_schedule_row(course_schedule)
	return str(schedule.student_group or ""), str(schedule.schedule_date or "")


@frappe.whitelist()
def get_student_attendance_records(
	based_on,
	date=None,
	student_group=None,
	course_schedule=None,
):
	"""Compatibility-safe replacement for Frappe Education's Attendance Tool read path."""
	mode = str(based_on or "").strip()
	group_name = str(student_group or "").strip()
	schedule_name = str(course_schedule or "").strip()
	target_date = str(date or "").strip()

	if mode == "Course Schedule":
		if not schedule_name:
			frappe.throw(_("Select a Course Schedule."), frappe.ValidationError)
		group_name, schedule_date = _schedule_context(schedule_name)
		target_date = schedule_date or target_date
	elif mode == "Student Group":
		if not group_name or not target_date:
			frappe.throw(_("Select a Student Group and date."), frappe.ValidationError)
	else:
		frappe.throw(_("Select a valid attendance basis."), frappe.ValidationError)

	register = safe.get_attendance_register(
		group_name,
		target_date,
		schedule_name or None,
	)
	return [
		{
			"student": row["student"],
			"student_name": row.get("student_name"),
			"group_roll_number": row.get("group_roll_number"),
			"status": row.get("status") or "Present",
			"disabled": bool(row.get("locked")),
		}
		for row in register["students"]
	]


@frappe.whitelist()
def mark_attendance(
	students_present,
	students_absent,
	course_schedule=None,
	student_group=None,
	date=None,
):
	"""Route the legacy Attendance Tool write through EduEdge's governed register save."""
	group_name = str(student_group or "").strip()
	schedule_name = str(course_schedule or "").strip()
	target_date = str(date or "").strip()

	if schedule_name:
		schedule_group, schedule_date = _schedule_context(schedule_name)
		if group_name and group_name != schedule_group:
			frappe.throw(
				_("Course Schedule does not belong to the selected Student Group."),
				frappe.ValidationError,
			)
		group_name = schedule_group
		target_date = schedule_date or target_date

	if not group_name or not target_date:
		frappe.throw(
			_("Select a Student Group and attendance date."),
			frappe.ValidationError,
		)

	entries = [
		{"student": row.get("student"), "status": "Present"}
		for row in _rows(students_present)
	]
	entries.extend(
		{"student": row.get("student"), "status": "Absent"}
		for row in _rows(students_absent)
	)

	result = safe.save_attendance_register(
		group_name,
		target_date,
		entries,
		schedule_name or None,
		submit=1,
	)
	frappe.msgprint(_("Attendance has been marked successfully."))
	return result
