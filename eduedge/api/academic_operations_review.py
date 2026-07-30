from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations_safe as safe
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import resolve_academic_defaults


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	payload = safe.get_operations_context(branch=branch, date=date, student_group=student_group)
	calendar = payload.get("academic_calendar") or {}
	selected_branch = payload.get("selected_branch") or {}
	institution = selected_branch.get("institution")

	if institution and calendar.get("source") != "institution_calendar":
		# Never expose every active Student Group merely because a Branch-specific
		# Session could not be resolved. Existing schedules remain visible for the
		# selected date so historical operational records are not hidden.
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _(
				"No enabled Institution Academic Calendar covers the selected date. Configure the Academic Session and its Terms before creating or selecting a Class Arm."
			),
		}
	elif institution and not calendar.get("academic_term"):
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _(
				"The selected date is inside the Academic Session but outside every configured Term / Academic Period."
			),
		}
	else:
		payload["academic_calendar"] = {**calendar, "ready": bool(calendar.get("academic_year"))}
	_annotate_group_hierarchy(payload.get("student_groups") or [])
	return payload


def _annotate_group_hierarchy(groups: list[dict]) -> None:
	if not groups:
		return
	meta = frappe.get_meta("Student Group")
	level_field = "eduedge_academic_level"
	if not meta.has_field(level_field):
		return
	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", [row.get("name") for row in groups if row.get("name")]]},
		fields=["name", level_field],
		page_length=len(groups),
	)
	levels = {row.name: row.get(level_field) for row in rows}
	level_names = {
		row.name: row.level_name
		for row in frappe.get_all(
			"EduEdge Academic Level",
			filters={"name": ["in", list({value for value in levels.values() if value})]},
			fields=["name", "level_name"],
			page_length=max(len(levels), 1),
		)
	} if any(levels.values()) else {}
	for group in groups:
		level = levels.get(group.get("name"))
		group["academic_level"] = level or ""
		group["academic_level_name"] = level_names.get(level) or level or ""


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Class Arms valid for the Branch and selected lesson date."""
	safe.base._require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = safe.base._resolve_branch(filters.get(BRANCH_FIELD))
	reference_date = str(getdate(filters.get("reference_date") or nowdate()))
	calendar = resolve_academic_defaults(branch, reference_date)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if institution and (
		calendar.get("source") != "institution_calendar"
		or not calendar.get("academic_year")
		or not calendar.get("academic_term")
	):
		return []

	group_filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	academic_year = filters.get("academic_year") or calendar.get("academic_year")
	academic_term = filters.get("academic_term") or calendar.get("academic_term")
	if academic_year:
		group_filters["academic_year"] = academic_year
	fields = ["name", "student_group_name", "program", "course", "academic_year", "academic_term"]
	if frappe.get_meta("Student Group").has_field("eduedge_academic_level"):
		fields.append("eduedge_academic_level")
	rows = frappe.get_list(
		"Student Group",
		filters=group_filters,
		or_filters={
			"name": ["like", f"%{txt}%"],
			"student_group_name": ["like", f"%{txt}%"],
			"program": ["like", f"%{txt}%"],
			"course": ["like", f"%{txt}%"],
		},
		fields=fields,
		start=int(start),
		page_length=int(page_len),
		order_by="student_group_name asc",
	)
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	level_names = {
		row.name: row.level_name
		for row in frappe.get_all(
			"EduEdge Academic Level",
			filters={"name": ["in", list({row.get("eduedge_academic_level") for row in rows if row.get("eduedge_academic_level")})]},
			fields=["name", "level_name"],
			page_length=max(len(rows), 1),
		)
	} if any(row.get("eduedge_academic_level") for row in rows) else {}
	return [
		[
			row.name,
			row.student_group_name,
			level_names.get(row.get("eduedge_academic_level")) or row.program or row.course or "",
			row.academic_term or row.academic_year or "",
		]
		for row in rows
	]
