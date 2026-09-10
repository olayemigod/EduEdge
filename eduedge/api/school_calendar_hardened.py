from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import school_calendar as base
from eduedge.education.custom_fields import BRANCH_FIELD


def _institution_session_options(institution: str) -> list[dict]:
	if not institution:
		return []
	calendar_rows = frappe.get_all(
		"EduEdge Institution Academic Calendar",
		filters={"institution": institution, "enabled": 1},
		fields=["academic_year"],
		page_length=500,
	)
	years = sorted({row.academic_year for row in calendar_rows if row.academic_year})
	if not years:
		return []
	return [
		dict(row)
		for row in frappe.get_all(
			"Academic Year",
			filters={"name": ["in", years]},
			fields=["name", "academic_year_name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc, name desc",
			page_length=500,
		)
	]


def _institution_terms(institution: str, academic_year: str) -> list[dict]:
	if not institution or not academic_year:
		return []
	calendar = frappe.db.get_value(
		"EduEdge Institution Academic Calendar",
		{"institution": institution, "academic_year": academic_year, "enabled": 1},
		"name",
	)
	if not calendar:
		return []
	period_rows = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={"parent": calendar, "parenttype": "EduEdge Institution Academic Calendar"},
		fields=["academic_term", "sequence"],
		order_by="sequence asc, idx asc",
		page_length=500,
	)
	term_names = [row.academic_term for row in period_rows if row.academic_term]
	if not term_names:
		return []
	term_rows = frappe.get_all(
		"Academic Term",
		filters={"name": ["in", term_names]},
		fields=["name", "term_name", "term_start_date", "term_end_date"],
		page_length=500,
	)
	by_name = {row.name: dict(row) for row in term_rows}
	return [by_name[name] for name in term_names if name in by_name]


def _event_form_options(branch: str, institution: str, academic_year: str, program: str | None = None) -> dict:
	terms = _institution_terms(institution, academic_year)
	offerings = frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "academic_year": academic_year},
		fields=["program"],
		order_by="program asc",
		page_length=1000,
	)
	programs = sorted({row.program for row in offerings if row.program})
	group_filters: dict = {BRANCH_FIELD: branch, "academic_year": academic_year, "disabled": 0}
	if program:
		if program not in programs:
			frappe.throw(
				_("Select a Class / Programme offered by this Branch in the chosen Academic Session."),
				frappe.ValidationError,
			)
		group_filters["program"] = program
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=["name", "student_group_name", "program"],
		order_by="student_group_name asc, name asc",
		page_length=2000,
	)
	return {
		"terms": terms,
		"programs": [{"value": name, "label": name} for name in programs],
		"class_arms": [
			{
				"value": row.name,
				"label": row.student_group_name or row.name,
				"program": row.program or "",
			}
			for row in groups
		],
	}


def _empty_context(branches: list[dict], branch_row: dict | None = None) -> dict:
	branch_row = branch_row or {}
	return {
		"branch": branch_row.get("name") or "",
		"branches": branches,
		"institution": branch_row.get("institution") or "",
		"institution_name": branch_row.get("institution_name") or branch_row.get("institution") or "",
		"academic_year": "",
		"academic_term": "",
		"sessions": [],
		"terms": [],
		"range": {"start": "", "end": ""},
		"items": [],
		"event_options": {"terms": [], "programs": [], "class_arms": []},
		"permissions": {
			"event_read": bool(frappe.has_permission(base.EVENT_DOCTYPE, "read")),
			"event_create": bool(frappe.has_permission(base.EVENT_DOCTYPE, "create")),
			"event_write": bool(frappe.has_permission(base.EVENT_DOCTYPE, "write")),
		},
	}


@frappe.whitelist()
def get_school_calendar_context(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	start: str | None = None,
	end: str | None = None,
	event_type: str | None = None,
	audience: str | None = None,
	include_teaching: int | str | None = 0,
) -> dict:
	base._require_login()
	branches = base._branch_options()
	selected_branch = base._resolve_branch(branch, branches)
	if not selected_branch:
		return _empty_context([])
	branch_row = next(row for row in branches if row["name"] == selected_branch)
	institution = branch_row.get("institution") or ""
	if not institution:
		frappe.throw(_("The selected School Branch / Campus has no Institution context."), frappe.ValidationError)

	sessions = _institution_session_options(institution)
	if not sessions:
		return _empty_context(branches, branch_row)
	selected_year = academic_year or base._default_session(sessions)
	if selected_year not in {row["name"] for row in sessions}:
		frappe.throw(
			_("Select an Academic Session configured for this Institution."),
			frappe.ValidationError,
		)
	terms = _institution_terms(institution, selected_year)
	if academic_term and academic_term not in {row["name"] for row in terms}:
		frappe.throw(
			_("Select a Term configured in this Institution Academic Calendar."),
			frappe.ValidationError,
		)
	start_date, end_date = base._range(selected_year, start, end)

	items: list[dict] = []
	items.extend(base._academic_period_items(institution, selected_year, start_date, end_date))
	items.extend(base._assessment_items(selected_branch, selected_year, academic_term, start_date, end_date))
	items.extend(base._cbt_items(selected_branch, selected_year, academic_term, start_date, end_date))
	items.extend(
		base._school_event_items(
			selected_branch,
			selected_year,
			academic_term,
			start_date,
			end_date,
			event_type,
			audience,
		)
	)
	if cint(include_teaching):
		items.extend(base._teaching_items(selected_branch, selected_year, start_date, end_date))
	items.sort(key=lambda row: (str(row.get("starts_on") or ""), str(row.get("title") or "")))

	return {
		"branch": selected_branch,
		"branches": branches,
		"institution": institution,
		"institution_name": branch_row.get("institution_name") or institution,
		"academic_year": selected_year,
		"academic_term": academic_term or "",
		"sessions": sessions,
		"terms": terms,
		"range": {"start": str(start_date), "end": str(end_date)},
		"items": items,
		"event_options": _event_form_options(selected_branch, institution, selected_year),
		"permissions": {
			"event_read": bool(frappe.has_permission(base.EVENT_DOCTYPE, "read")),
			"event_create": bool(frappe.has_permission(base.EVENT_DOCTYPE, "create")),
			"event_write": bool(frappe.has_permission(base.EVENT_DOCTYPE, "write")),
		},
	}


@frappe.whitelist()
def get_event_form_options(branch: str, academic_year: str, program: str | None = None) -> dict:
	base._require_login()
	branches = base._branch_options()
	selected_branch = base._resolve_branch(branch, branches)
	branch_row = next(row for row in branches if row["name"] == selected_branch)
	institution = branch_row.get("institution") or ""
	if academic_year not in {row["name"] for row in _institution_session_options(institution)}:
		frappe.throw(
			_("Select an Academic Session configured for this Institution."),
			frappe.ValidationError,
		)
	return _event_form_options(selected_branch, institution, academic_year, program)
