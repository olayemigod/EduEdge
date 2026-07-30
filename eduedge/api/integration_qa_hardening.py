from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_foundation_safe as academic_foundation
from eduedge.api import academic_operations_review
from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.services.branch_context import (
	get_active_branch_context,
	get_allowed_school_branches,
	get_current_school_branch,
)


def _academic_calendars(institution: str | None) -> list[dict]:
	"""Return calendar rows using mapping access after normalising Frappe rows to dicts."""
	if not institution or not frappe.has_permission(academic_foundation.CALENDAR_DOCTYPE, "read"):
		return []
	rows = [
		dict(row)
		for row in frappe.get_list(
			academic_foundation.CALENDAR_DOCTYPE,
			filters={"institution": institution, "enabled": 1},
			fields=[
				"name",
				"institution",
				"academic_year",
				"is_current",
				"enabled",
				"start_date",
				"end_date",
				"notes",
				"modified",
			],
			order_by="is_current desc, start_date desc",
			page_length=academic_foundation.MAX_ROWS,
		)
	]
	if not rows:
		return rows
	periods = frappe.get_all(
		academic_foundation.PERIOD_DOCTYPE,
		filters={
			"parent": ["in", [row["name"] for row in rows]],
			"parenttype": academic_foundation.CALENDAR_DOCTYPE,
		},
		fields=[
			"name",
			"parent",
			"academic_term",
			"start_date",
			"end_date",
			"sequence",
			"result_publication_date",
		],
		order_by="parent asc, sequence asc, start_date asc",
		limit_page_length=academic_foundation.MAX_ROWS * 4,
	)
	by_calendar: dict[str, list[dict]] = defaultdict(list)
	for period in periods:
		by_calendar[period.parent].append(dict(period))
	today = getdate(nowdate())
	for calendar in rows:
		calendar_periods = by_calendar.get(calendar["name"], [])
		current_period = next(
			(
				row
				for row in calendar_periods
				if row.get("start_date")
				and row.get("end_date")
				and getdate(row["start_date"]) <= today <= getdate(row["end_date"])
			),
			None,
		)
		calendar["periods"] = calendar_periods
		calendar["period_count"] = len(calendar_periods)
		calendar["current_period"] = current_period
		calendar["contains_today"] = bool(
			calendar.get("start_date")
			and calendar.get("end_date")
			and getdate(calendar["start_date"]) <= today <= getdate(calendar["end_date"])
		)
		calendar["has_calendar_gap_today"] = bool(calendar["contains_today"] and not current_period)
	return rows


@frappe.whitelist()
def get_academic_foundation(institution: str | None = None) -> dict:
	"""Serve the Institution-wide Academic Foundation without requiring a Branch."""
	academic_foundation._require_login()
	institutions = academic_foundation._permitted_institutions()
	selected = academic_foundation._resolve_selected_institution(institution, institutions)
	active_context = academic_foundation.get_effective_institution_context(institution=selected)
	terms = (
		academic_foundation.get_terminology_map(active_context.get("institution_type"))
		if selected
		else {}
	)
	departments = academic_foundation._departments(selected)
	programmes = academic_foundation._programmes(selected)
	branches = academic_foundation._branches(selected)
	student_groups = academic_foundation._student_groups(branches)
	calendars = _academic_calendars(selected)
	hierarchy = academic_foundation._build_hierarchy(departments, programmes, student_groups)
	readiness = academic_foundation._build_readiness(
		selected,
		departments,
		programmes,
		student_groups,
		calendars,
	)
	return {
		"active_context": active_context,
		"selected_institution": selected,
		"terms": terms,
		"institutions": institutions,
		"departments": departments,
		"programmes": programmes,
		"branches": branches,
		"student_groups": student_groups,
		"calendars": calendars,
		"hierarchy": hierarchy,
		"readiness": readiness,
		"today": nowdate(),
		"permissions": {
			"can_create_department": bool(frappe.has_permission("Department", "create")),
			"can_write_department": bool(frappe.has_permission("Department", "write")),
			"can_create_programme": bool(frappe.has_permission("Program", "create")),
			"can_write_programme": bool(frappe.has_permission("Program", "write")),
			"can_create_student_group": bool(frappe.has_permission("Student Group", "create")),
			"can_write_student_group": bool(frappe.has_permission("Student Group", "write")),
			"can_create_calendar": bool(
				frappe.has_permission(academic_foundation.CALENDAR_DOCTYPE, "create")
			),
			"can_write_calendar": bool(
				frappe.has_permission(academic_foundation.CALENDAR_DOCTYPE, "write")
			),
		},
	}


def _preferred_operational_branch(branch: str | None = None) -> str:
	if branch:
		assert_branch_access(branch)
		return branch

	current = get_current_school_branch() or {}
	if current.get("name"):
		assert_branch_access(current["name"])
		return current["name"]

	context = get_active_branch_context()
	active_institution = current.get("institution") or context.get("active_institution")
	allowed = get_allowed_school_branches(institution=active_institution) if active_institution else get_allowed_school_branches()
	allowed = [row for row in allowed if row.get("name")]
	default_branch = next(
		(row["name"] for row in allowed if row.get("is_default")),
		None,
	)
	resolved = default_branch or (allowed[0]["name"] if len(allowed) == 1 else None) or get_context_branch()
	if resolved:
		assert_branch_access(resolved)
		return resolved

	if not allowed:
		frappe.throw(
			_("Set up a School Branch / Campus before using branch-scoped academic operations."),
			frappe.ValidationError,
		)
	frappe.throw(
		_("Select a School Branch / Campus to continue."),
		frappe.ValidationError,
	)


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	"""Resolve an active/default/sole permitted Branch before loading operations."""
	return academic_operations_review.get_operations_context(
		branch=_preferred_operational_branch(branch),
		date=date,
		student_group=student_group,
	)
