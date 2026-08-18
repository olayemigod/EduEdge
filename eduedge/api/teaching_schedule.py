from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations_safe as operations
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_scope import get_user_instructor_names, is_limited_instructor_user
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

VALID_VIEWS = {"day", "week", "upcoming", "rooms"}


def _date_window(reference_date, view: str):
	day = getdate(reference_date or nowdate())
	if view == "week":
		start = day - timedelta(days=day.weekday())
		return start, start + timedelta(days=6)
	if view == "upcoming":
		return day, day + timedelta(days=30)
	return day, day


def _selected_branch_context(branch: str) -> dict:
	return operations._selected_branch_context(branch)


def _group_labels(names: list[str]) -> dict[str, str]:
	if not names:
		return {}
	rows = frappe.get_list(
		"Student Group",
		filters={"name": ["in", names]},
		fields=["name", "student_group_name"],
		page_length=max(len(names), 1),
	)
	return {row.name: row.student_group_name or row.name for row in rows}


def _require_schedule_read() -> None:
	operations.base._require_academic_operator()
	if not frappe.has_permission("Course Schedule", "read"):
		frappe.throw(_("You are not permitted to view Teaching Schedules."), frappe.PermissionError)


@frappe.whitelist()
def get_teaching_schedule_context(
	branch: str | None = None,
	reference_date: str | None = None,
	view: str = "day",
) -> dict:
	"""Return a focused, permission-aware view over native Course Schedule records."""
	_require_schedule_read()
	view = str(view or "day").strip().lower()
	if view not in VALID_VIEWS:
		frappe.throw(_("Select a valid Teaching Schedule view."), frappe.ValidationError)

	resolved_branch = operations.base._resolve_branch(branch)
	start_date, end_date = _date_window(reference_date, view)
	limited_instructor = is_limited_instructor_user()
	instructor_names = get_user_instructor_names(required=limited_instructor)

	filters: dict = {
		BRANCH_FIELD: resolved_branch,
		"schedule_date": ["between", [str(start_date), str(end_date)]],
	}
	if limited_instructor:
		filters["instructor"] = ["in", instructor_names]

	schedules = frappe.get_list(
		"Course Schedule",
		filters=filters,
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
		order_by="schedule_date asc, from_time asc, student_group asc",
		page_length=500,
	)
	group_labels = _group_labels(sorted({row.student_group for row in schedules if row.student_group}))
	for row in schedules:
		row["student_group_name"] = group_labels.get(row.student_group) or row.student_group

	room_usage = operations._room_usage([dict(row) for row in schedules if str(row.schedule_date) == str(start_date)])
	calendar = resolve_academic_defaults(resolved_branch, str(getdate(reference_date or nowdate())))
	selected_branch = _selected_branch_context(resolved_branch)
	permissions = operations._operations_permissions()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": selected_branch.get("company"),
		"current_branch": get_current_school_branch(),
		"selected_branch": selected_branch,
		"allowed_branches": get_allowed_school_branches(),
		"permissions": permissions,
		"view": view,
		"reference_date": str(getdate(reference_date or nowdate())),
		"start_date": str(start_date),
		"end_date": str(end_date),
		"academic_calendar": {
			**calendar,
			"ready": bool(calendar.get("academic_year") and calendar.get("academic_term")),
		},
		"schedules": [dict(row) for row in schedules],
		"room_usage": room_usage,
		"counts": {
			"schedules": len(schedules),
			"instructors": len({row.instructor for row in schedules if row.instructor}),
			"student_groups": len({row.student_group for row in schedules if row.student_group}),
			"rooms": len({row.room for row in schedules if row.room}),
			"unassigned_rooms": sum(1 for row in schedules if not row.room),
		},
	}
