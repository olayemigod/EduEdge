from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations as base
from eduedge.education.academic_operations import ASSIGNMENT_DOCTYPE
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	base._require_academic_operator()
	resolved_branch = base._resolve_branch(branch)
	target_date = str(getdate(date or nowdate()))
	calendar_context = resolve_academic_defaults(resolved_branch, target_date)
	academic_year = calendar_context.get("academic_year")
	academic_term = calendar_context.get("academic_term")

	group_filters: dict = {BRANCH_FIELD: resolved_branch, "disabled": 0}
	if academic_year:
		group_filters["academic_year"] = academic_year
	if academic_term:
		group_filters["academic_term"] = academic_term
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
	group_names = [row.name for row in groups]
	group_strength = base._get_group_strength(group_names)
	for row in groups:
		row["student_count"] = group_strength.get(row.name, 0)

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
	allowed_branches = get_allowed_school_branches()
	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
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
			"attendance_submitted": attendance_summary["total"],
			"present": attendance_summary["Present"],
			"absent": attendance_summary["Absent"],
			"leave": attendance_summary["Leave"],
		},
		"student_groups": groups,
		"schedules": schedules,
	}
