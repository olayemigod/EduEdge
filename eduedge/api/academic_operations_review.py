from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations_safe as safe
from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD
from eduedge.education.academic_progression import get_programme_course_rows
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.native_identity import DISPLAY_FIELD
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
			"blocking_issue": _("No enabled Institution Academic Calendar covers the selected date. Configure the Academic Session and its Terms before creating or selecting a Class Arm / Lecture Group."),
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
	_annotate_schedule_labels(payload)
	return payload


def _annotate_group_hierarchy(groups: list[dict]) -> None:
	if not groups:
		return
	names = [row.get("name") for row in groups if row.get("name")]
	fields = ["name", "student_group_name", DISPLAY_FIELD, "program", "course", "group_based_on", "academic_year", "academic_term", "batch", BRANCH_FIELD]
	if frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		fields.append(ACADEMIC_LEVEL_FIELD)
	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", names]},
		fields=fields,
		page_length=len(names),
	)
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all(
			"Program",
			filters={"name": ["in", program_names]},
			fields=["name", "program_name", DISPLAY_FIELD, "department"],
			page_length=max(len(program_names), 1),
		)
	} if program_names else {}
	level_names = list({row.get(ACADEMIC_LEVEL_FIELD) for row in rows if row.get(ACADEMIC_LEVEL_FIELD)})
	levels = {
		row.name: row.level_name
		for row in frappe.get_all(
			"EduEdge Academic Level",
			filters={"name": ["in", level_names]},
			fields=["name", "level_name"],
			page_length=max(len(level_names), 1),
		)
	} if level_names else {}
	by_name = {row.name: row for row in rows}
	for group in groups:
		row = by_name.get(group.get("name"))
		if not row:
			continue
		programme = programmes.get(row.program)
		group["program"] = row.program or ""
		group["program_name"] = (programme or {}).get(DISPLAY_FIELD) or (programme or {}).get("program_name") or row.program or ""
		group["department"] = (programme or {}).get("department") or ""
		group["academic_level"] = row.get(ACADEMIC_LEVEL_FIELD) or ""
		group["academic_level_name"] = levels.get(group["academic_level"]) or ""
		group["course"] = row.course or ""
		group["group_based_on"] = row.group_based_on or ""
		group["academic_year"] = row.academic_year or ""
		group["academic_term"] = row.academic_term or ""
		group["batch"] = row.batch or ""
		group["display_name"] = row.get(DISPLAY_FIELD) or row.student_group_name or row.name
		group["hierarchy_label"] = " → ".join(
			value for value in (group["department"], group["program_name"], group["academic_level_name"], group["display_name"]) if value
		)


def _annotate_schedule_labels(payload: dict) -> None:
	groups = {row.get("name"): row for row in payload.get("student_groups") or []}
	course_names = list({row.get("course") for row in payload.get("schedules") or [] if row.get("course")})
	courses = {
		row.name: row.get(DISPLAY_FIELD) or row.course_name or row.name
		for row in frappe.get_all(
			"Course",
			filters={"name": ["in", course_names]},
			fields=["name", "course_name", DISPLAY_FIELD],
			page_length=max(len(course_names), 1),
		)
	} if course_names else {}
	for row in payload.get("schedules") or []:
		row["course_display_name"] = courses.get(row.get("course")) or row.get("course") or ""
		row["student_group_display_name"] = (groups.get(row.get("student_group")) or {}).get("display_name") or row.get("student_group") or ""
	for row in payload.get("attendance_coverage") or []:
		row["course_display_name"] = courses.get(row.get("course")) or row.get("course") or ""
		row["student_group_name"] = (groups.get(row.get("student_group")) or {}).get("display_name") or row.get("student_group_name") or row.get("student_group") or ""


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
	if filters.get(ACADEMIC_LEVEL_FIELD) and frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		group_filters[ACADEMIC_LEVEL_FIELD] = filters.get(ACADEMIC_LEVEL_FIELD)
	fields = ["name", "student_group_name", DISPLAY_FIELD, "program", "course", "academic_year", "academic_term"]
	if frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		fields.append(ACADEMIC_LEVEL_FIELD)
	rows = frappe.get_list(
		"Student Group",
		filters=group_filters,
		or_filters={"name": ["like", f"%{txt}%"], "student_group_name": ["like", f"%{txt}%"], DISPLAY_FIELD: ["like", f"%{txt}%"], "program": ["like", f"%{txt}%"], "course": ["like", f"%{txt}%"]},
		fields=fields,
		start=int(start),
		page_length=int(page_len),
		order_by=f"{DISPLAY_FIELD} asc, student_group_name asc",
	)
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	program_names = list({row.program for row in rows if row.program})
	programmes = {
		row.name: row
		for row in frappe.get_all("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name", DISPLAY_FIELD, "department"], page_length=max(len(program_names), 1))
	} if program_names else {}
	level_names = list({row.get(ACADEMIC_LEVEL_FIELD) for row in rows if row.get(ACADEMIC_LEVEL_FIELD)})
	levels = {
		row.name: row.level_name
		for row in frappe.get_all("EduEdge Academic Level", filters={"name": ["in", level_names]}, fields=["name", "level_name"], page_length=max(len(level_names), 1))
	} if level_names else {}
	return [
		[
			row.name,
			row.get(DISPLAY_FIELD) or row.student_group_name,
			" → ".join(value for value in ((programmes.get(row.program) or {}).get("department"), (programmes.get(row.program) or {}).get(DISPLAY_FIELD) or (programmes.get(row.program) or {}).get("program_name") or row.program, levels.get(row.get(ACADEMIC_LEVEL_FIELD)), row.course) if value),
			row.academic_term or row.academic_year or "",
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Courses configured for the selected Program, Level and curriculum period."""
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
	period_number = _curriculum_period_number(
		institution,
		filters.get("academic_year"),
		filters.get("academic_term"),
	)
	course_names = [
		row.course
		for row in get_programme_course_rows(
			program,
			academic_level=filters.get(ACADEMIC_LEVEL_FIELD),
			period_number=period_number,
		)
		if row.course
	]
	if not course_names:
		return []
	course_filters = {"name": ["in", course_names]}
	course_meta = frappe.get_meta("Course")
	if course_meta.has_field(INSTITUTION_FIELD):
		course_filters[INSTITUTION_FIELD] = institution
	fields = ["name", "course_name", "course_code"]
	if course_meta.has_field(DISPLAY_FIELD):
		fields.append(DISPLAY_FIELD)
	rows = frappe.get_list(
		"Course",
		filters=course_filters,
		or_filters={"name": ["like", f"%{txt}%"], "course_name": ["like", f"%{txt}%"], DISPLAY_FIELD: ["like", f"%{txt}%"], "course_code": ["like", f"%{txt}%"]},
		fields=fields,
		start=int(start),
		page_length=int(page_len),
		order_by=f"{DISPLAY_FIELD} asc, course_name asc, name asc" if course_meta.has_field(DISPLAY_FIELD) else "course_name asc, name asc",
	)
	return [[row.name, row.get(DISPLAY_FIELD) or row.course_name or row.name, row.course_code or "", program_row.department or ""] for row in rows]


def _curriculum_period_number(institution: str | None, academic_year: str | None, academic_term: str | None) -> int | None:
	if not institution or not academic_year or not academic_term:
		return None
	calendar = frappe.db.get_value(
		"EduEdge Institution Academic Calendar",
		{"institution": institution, "academic_year": academic_year, "enabled": 1},
		"name",
	)
	if not calendar:
		return None
	return frappe.db.get_value(
		"EduEdge Academic Calendar Period",
		{"parent": calendar, "parenttype": "EduEdge Institution Academic Calendar", "academic_term": academic_term},
		"sequence",
	)
