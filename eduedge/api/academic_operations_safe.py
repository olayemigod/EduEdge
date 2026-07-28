from __future__ import annotations

from collections import Counter

import frappe
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations as base
from eduedge.education.academic_operations import ASSIGNMENT_DOCTYPE
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch


def _selected_branch_context(branch: str) -> dict:
	row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["name", "branch_name", "company", "institution"],
		as_dict=True,
	) or {}
	institution = row.get("institution")
	row["institution_name"] = (
		frappe.db.get_value("EduEdge Institution", institution, "institution_name")
		if institution
		else None
	)
	return row


def _attendance_coverage(
	branch: str,
	date: str,
	schedules: list[dict],
	group_strength: dict[str, int],
	group_labels: dict[str, str],
) -> list[dict]:
	"""Return submitted-attendance coverage for each scheduled session.

	Attendance is saved against Course Schedule when the register is opened from a
	schedule. Coverage therefore follows the schedule identity, not only the Student
	Group, so two sessions for the same class cannot incorrectly satisfy each other.
	"""
	scheduled_rows = [
		dict(row)
		for row in schedules
		if row.get("name") and row.get("student_group")
	]
	if not scheduled_rows:
		return []

	schedule_names = [row["name"] for row in scheduled_rows]
	rows = frappe.get_all(
		"Student Attendance",
		filters={
			BRANCH_FIELD: branch,
			"date": date,
			"docstatus": 1,
			"course_schedule": ["in", schedule_names],
		},
		fields=[
			"course_schedule",
			"status",
			{"COUNT": "name", "as": "record_count"},
		],
		group_by="course_schedule, status",
	)
	counts: dict[str, Counter] = {name: Counter() for name in schedule_names}
	for row in rows:
		counts.setdefault(row.course_schedule, Counter())[row.status] = int(row.record_count or 0)

	coverage = []
	for schedule in scheduled_rows:
		group = schedule["student_group"]
		expected = int(group_strength.get(group, 0))
		schedule_counts = counts.get(schedule["name"], Counter())
		submitted = sum(schedule_counts.values())
		coverage.append(
			{
				"course_schedule": schedule["name"],
				"course": schedule.get("course"),
				"student_group": group,
				"student_group_name": group_labels.get(group) or group,
				"from_time": schedule.get("from_time"),
				"to_time": schedule.get("to_time"),
				"room": schedule.get("room"),
				"expected": expected,
				"submitted": submitted,
				"present": schedule_counts["Present"],
				"absent": schedule_counts["Absent"],
				"leave": schedule_counts["Leave"],
				"missing": max(expected - submitted, 0),
				"has_attendance": submitted > 0,
				"complete": expected > 0 and submitted >= expected,
			}
		)
	return coverage


def _room_usage(schedules: list[dict]) -> list[dict]:
	usage: dict[str, dict] = {}
	for schedule in schedules:
		room = schedule.get("room") or "Unassigned"
		item = usage.setdefault(
			room,
			{
				"room": room,
				"is_unassigned": not bool(schedule.get("room")),
				"sessions": 0,
				"first_start": schedule.get("from_time"),
				"last_end": schedule.get("to_time"),
			},
		)
		item["sessions"] += 1
		if schedule.get("from_time") and (
			not item.get("first_start") or schedule.get("from_time") < item.get("first_start")
		):
			item["first_start"] = schedule.get("from_time")
		if schedule.get("to_time") and (
			not item.get("last_end") or schedule.get("to_time") > item.get("last_end")
		):
			item["last_end"] = schedule.get("to_time")
	return sorted(usage.values(), key=lambda row: (row["is_unassigned"], row["room"]))


def _calendar_display(calendar_context: dict, target_date: str) -> dict:
	context = dict(calendar_context or {})
	context["reference_date"] = target_date
	context["calendar_gap"] = bool(
		context.get("source") == "institution_calendar"
		and context.get("calendar")
		and not context.get("academic_term")
	)
	context["period_label"] = context.get("academic_term") or "No configured period"
	return context


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	base._require_academic_operator()
	resolved_branch = base._resolve_branch(branch)
	target_date = str(getdate(date or nowdate()))
	calendar_context = _calendar_display(resolve_academic_defaults(resolved_branch, target_date), target_date)
	academic_year = calendar_context.get("academic_year")
	academic_term = calendar_context.get("academic_term")

	group_filters: dict = {BRANCH_FIELD: resolved_branch, "disabled": 0}
	if academic_year:
		group_filters["academic_year"] = academic_year
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=[
			"name",
			"student_group_name",
			"group_based_on",
			"program",
			"course",
			"academic_year",
			"academic_term",
			"max_strength",
		],
		order_by="student_group_name asc",
		page_length=100,
	)
	if academic_term:
		# Year-wide groups with no term remain operational in every period.
		groups = [row for row in groups if not row.academic_term or row.academic_term == academic_term]
	group_names = [row.name for row in groups]
	group_strength = base._get_group_strength(group_names)
	group_labels = {}
	for row in groups:
		row["student_count"] = group_strength.get(row.name, 0)
		group_labels[row.name] = row.student_group_name

	schedule_filters: dict = {
		BRANCH_FIELD: resolved_branch,
		"schedule_date": target_date,
	}
	if student_group:
		schedule_filters["student_group"] = student_group
	schedules = frappe.get_list(
		"Course Schedule",
		filters=schedule_filters,
		fields=[
			"name",
			"student_group",
			"course",
			"instructor",
			"instructor_name",
			"room",
			"schedule_date",
			"from_time",
			"to_time",
			"title",
		],
		order_by="from_time asc",
		page_length=200,
	)
	attendance_summary = base._get_attendance_summary(resolved_branch, target_date)
	attendance_coverage = _attendance_coverage(
		resolved_branch,
		target_date,
		schedules,
		group_strength,
		group_labels,
	)
	room_usage = _room_usage(schedules)
	allowed_branches = get_allowed_school_branches()
	current_branch = get_current_school_branch()
	selected_branch = _selected_branch_context(resolved_branch)
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	missing_registers = sum(1 for row in attendance_coverage if not row["has_attendance"])
	incomplete_registers = sum(1 for row in attendance_coverage if row["has_attendance"] and not row["complete"])
	complete_registers = sum(1 for row in attendance_coverage if row["complete"])

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": selected_branch.get("company"),
		"current_branch": current_branch,
		"selected_branch": selected_branch,
		"allowed_branches": allowed_branches,
		"academic_calendar": calendar_context,
		"filters": {
			"branch": resolved_branch,
			"date": target_date,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"student_group": student_group,
		},
		"counts": {
			"student_groups": len(groups),
			"assigned_instructors": frappe.db.count(
				ASSIGNMENT_DOCTYPE,
				{"school_branch": resolved_branch, "enabled": 1},
			),
			"schedules": len(schedules),
			"rooms_used": sum(1 for row in room_usage if not row["is_unassigned"]),
			"unassigned_room_sessions": sum(row["sessions"] for row in room_usage if row["is_unassigned"]),
			"attendance_submitted": attendance_summary["total"],
			"present": attendance_summary["Present"],
			"absent": attendance_summary["Absent"],
			"leave": attendance_summary["Leave"],
			"attendance_complete_registers": complete_registers,
			"attendance_incomplete_registers": incomplete_registers,
			"attendance_missing_registers": missing_registers,
			# Backward-compatible aliases retained for existing consumers and tests.
			"attendance_complete_groups": complete_registers,
			"attendance_incomplete_groups": incomplete_registers,
			"attendance_missing_groups": missing_registers,
		},
		"student_groups": groups,
		"schedules": schedules,
		"attendance_coverage": attendance_coverage,
		"room_usage": room_usage,
	}
