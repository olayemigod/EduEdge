from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations_safe as safe
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.academic_calendar import resolve_academic_defaults


@frappe.whitelist()
def get_operations_context(branch: str | None = None, date: str | None = None, student_group: str | None = None) -> dict:
	payload = safe.get_operations_context(branch=branch, date=date, student_group=student_group)
	calendar = payload.get("academic_calendar") or {}
	selected_branch = payload.get("selected_branch") or {}
	institution = selected_branch.get("institution")
	if institution and calendar.get("source") != "institution_calendar":
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _("No enabled Institution Academic Calendar covers the selected date. Configure the Academic Session and its Terms before creating or selecting a Class Arm / Level."),
		}
	elif institution and not calendar.get("academic_term"):
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _("The selected date is inside the Academic Session but outside every configured Term / Semester."),
		}
	else:
		payload["academic_calendar"] = {**calendar, "ready": bool(calendar.get("academic_year"))}
	_annotate_group_hierarchy(payload.get("student_groups") or [])
	return payload


def _annotate_group_hierarchy(groups: list[dict]) -> None:
	if not groups:
		return
	names = [row.get("name") for row in groups if row.get("name")]
	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", names]},
		fields=["name", "student_group_name", "program", "course", "group_based_on", "academic_year", "academic_term", "batch", BRANCH_FIELD],
		page_length=len(names),
	)
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name", "department"], page_length=max(len(program_names), 1))
	} if program_names else {}
	by_name = {row.name: row for row in rows}
	for group in groups:
		row = by_name.get(group.get("name"))
		if not row:
			continue
		programme = programmes.get(row.program)
		group["program"] = row.program or ""
		group["program_name"] = (programme or {}).get("program_name") or row.program or ""
		group["department"] = (programme or {}).get("department") or ""
		group["course"] = row.course or ""
		group["group_based_on"] = row.group_based_on or ""
		group["academic_year"] = row.academic_year or ""
		group["academic_term"] = row.academic_term or ""
		group["batch"] = row.batch or ""
		group["hierarchy_label"] = " → ".join(value for value in (group["department"], group["program_name"], row.student_group_name or row.name) if value)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Student Groups valid for the Branch and selected lesson date."""
	safe.base._require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = safe.base._resolve_branch(filters.get(BRANCH_FIELD))
	reference_date = str(getdate(filters.get("reference_date") or nowdate()))
	calendar = resolve_academic_defaults(branch, reference_date)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if institution and (calendar.get("source") != "institution_calendar" or not calendar.get("academic_year") or not calendar.get("academic_term")):
		return []
	group_filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	academic_year = filters.get("academic_year") or calendar.get("academic_year")
	academic_term = filters.get("academic_term") or calendar.get("academic_term")
	if academic_year:
		group_filters["academic_year"] = academic_year
	if filters.get("program"):
		group_filters["program"] = filters.get("program")
	rows = frappe.get_list(
		"Student Group",
		filters=group_filters,
		or_filters={"name": ["like", f"%{txt}%"], "student_group_name": ["like", f"%{txt}%"], "program": ["like", f"%{txt}%"], "course": ["like", f"%{txt}%"]},
		fields=["name", "student_group_name", "program", "course", "academic_year", "academic_term"],
		start=int(start),
		page_length=int(page_len),
		order_by="student_group_name asc",
	)
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name", "department"], page_length=max(len(program_names), 1))
	} if program_names else {}
	return [
		[
			row.name,
			row.student_group_name,
			" → ".join(value for value in ((programmes.get(row.program) or {}).get("department"), (programmes.get(row.program) or {}).get("program_name") or row.program, row.course) if value),
			row.academic_term or row.academic_year or "",
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Courses configured on the selected native Program."""
	safe.base._require_academic_operator()
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to read Courses / Subjects."), frappe.PermissionError)
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	program = str(filters.get("program") or "").strip()
	branch = str(filters.get(BRANCH_FIELD) or "").strip()
	if not program or not branch:
		return []
	branch = safe.base._resolve_branch(branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	program_row = frappe.db.get_value("Program", program, ["department", INSTITUTION_FIELD], as_dict=True)
	if not program_row or program_row.get(INSTITUTION_FIELD) != institution:
		return []
	course_names = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		order_by="idx asc",
	)
	if not course_names:
		return []
	course_filters = {"name": ["in", course_names]}
	course_meta = frappe.get_meta("Course")
	if course_meta.has_field(INSTITUTION_FIELD):
		course_filters[INSTITUTION_FIELD] = institution
	rows = frappe.get_list(
		"Course",
		filters=course_filters,
		or_filters={"name": ["like", f"%{txt}%"], "course_name": ["like", f"%{txt}%"], "course_code": ["like", f"%{txt}%"]},
		fields=["name", "course_name", "course_code"],
		start=int(start),
		page_length=int(page_len),
		order_by="course_name asc, name asc",
	)
	return [[row.name, row.course_name or row.name, row.course_code or "", program_row.department or ""] for row in rows]
