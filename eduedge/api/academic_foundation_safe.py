from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_hierarchy import _validate_department
from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context, get_terminology_map

MAX_ROWS = 1000
CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
PERIOD_DOCTYPE = "EduEdge Academic Calendar Period"


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _permitted_institutions() -> list[dict]:
	if not frappe.has_permission("EduEdge Institution", "read"):
		return []
	return frappe.get_list(
		"EduEdge Institution",
		filters={"enabled": 1},
		fields=["name", "institution_name", "institution_code", "institution_type", "company"],
		order_by="institution_name asc",
		page_length=MAX_ROWS,
	)


def _resolve_selected_institution(institution: str | None, institutions: list[dict]) -> str | None:
	allowed = {row.name for row in institutions}
	requested = str(institution or "").strip()
	if requested:
		if requested not in allowed:
			frappe.throw(_("You do not have access to this Institution."), frappe.PermissionError)
		return requested
	active = get_effective_institution_context().get("institution")
	if active in allowed:
		return active
	return institutions[0].name if institutions else None


@frappe.whitelist()
def get_academic_foundation(institution: str | None = None) -> dict:
	_require_login()
	institutions = _permitted_institutions()
	selected = _resolve_selected_institution(institution, institutions)
	active_context = get_effective_institution_context(institution=selected)
	terms = get_terminology_map(active_context.get("institution_type")) if selected else {}
	departments = _departments(selected)
	programmes = _programmes(selected)
	branches = _branches(selected)
	student_groups = _student_groups(branches)
	calendars = _calendars(selected)
	hierarchy = _build_hierarchy(departments, programmes, student_groups)
	readiness = _build_readiness(selected, departments, programmes, student_groups, calendars)
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
			"can_create_calendar": bool(frappe.has_permission(CALENDAR_DOCTYPE, "create")),
			"can_write_calendar": bool(frappe.has_permission(CALENDAR_DOCTYPE, "write")),
		},
	}


def _departments(institution: str | None) -> list[dict]:
	if not institution or not frappe.has_permission("Department", "read"):
		return []
	meta = frappe.get_meta("Department")
	filters = {INSTITUTION_FIELD: institution} if meta.has_field(INSTITUTION_FIELD) else {"company": frappe.db.get_value("EduEdge Institution", institution, "company")}
	if meta.has_field("disabled"):
		filters["disabled"] = 0
	fields = ["name", "department_name", "parent_department", "is_group", "company", "lft", "rgt"]
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	return frappe.get_list("Department", filters=filters, fields=fields, order_by="lft asc, department_name asc", page_length=MAX_ROWS)


def _programmes(institution: str | None) -> list[dict]:
	if not institution or not frappe.has_permission("Program", "read"):
		return []
	meta = frappe.get_meta("Program")
	fields = ["name", "program_name", "program_abbreviation", "department", INSTITUTION_FIELD, "modified"]
	if meta.has_field("enabled"):
		fields.append("enabled")
	rows = frappe.get_list(
		"Program",
		filters={INSTITUTION_FIELD: institution},
		fields=fields,
		order_by="department asc, program_name asc",
		page_length=MAX_ROWS,
	)
	_attach_program_counts(rows)
	return rows


def _attach_program_counts(programmes: list[dict]) -> None:
	names = [row.name for row in programmes]
	if not names:
		return
	course_counts = {}
	if frappe.db.exists("DocType", "Program Course"):
		rows = frappe.get_all(
			"Program Course",
			filters={"parent": ["in", names], "parenttype": "Program"},
			fields=["parent", {"COUNT": "name", "as": "record_count"}],
			group_by="parent",
		)
		course_counts = {row.parent: cint(row.record_count) for row in rows}
	offering_counts = {}
	if frappe.db.exists("DocType", "EduEdge Program Offering") and frappe.has_permission("EduEdge Program Offering", "read"):
		rows = frappe.get_list(
			"EduEdge Program Offering",
			filters={"program": ["in", names], "is_active": 1},
			fields=["program", {"COUNT": "name", "as": "record_count"}],
			group_by="program",
			page_length=max(len(names), 1),
		)
		offering_counts = {row.program: cint(row.record_count) for row in rows}
	for row in programmes:
		row["course_count"] = course_counts.get(row.name, 0)
		row["active_offering_count"] = offering_counts.get(row.name, 0)


def _branches(institution: str | None) -> list[dict]:
	if not institution or not frappe.has_permission("EduEdge School Branch", "read"):
		return []
	return frappe.get_list(
		"EduEdge School Branch",
		filters={"institution": institution, "enabled": 1},
		fields=["name", "branch_name", "branch_code", "company", "institution"],
		order_by="branch_name asc",
		page_length=MAX_ROWS,
	)


def _student_groups(branches: list[dict]) -> list[dict]:
	if not branches or not frappe.has_permission("Student Group", "read"):
		return []
	branch_names = [row.name for row in branches]
	rows = frappe.get_list(
		"Student Group",
		filters={"eduedge_school_branch": ["in", branch_names], "disabled": 0},
		fields=[
			"name", "student_group_name", "group_based_on", "program", "course", "batch",
			"academic_year", "academic_term", "max_strength", "disabled", "eduedge_school_branch",
			"eduedge_program_offering",
		],
		order_by="program asc, student_group_name asc",
		page_length=MAX_ROWS,
	)
	strength = _group_strength([row.name for row in rows])
	for row in rows:
		row["student_count"] = strength.get(row.name, 0)
	return rows


def _group_strength(names: list[str]) -> dict[str, int]:
	if not names:
		return {}
	rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": ["in", names], "parenttype": "Student Group", "active": 1},
		fields=["parent", {"COUNT": "name", "as": "record_count"}],
		group_by="parent",
	)
	return {row.parent: cint(row.record_count) for row in rows}


def _calendars(institution: str | None) -> list[dict]:
	if not institution or not frappe.has_permission(CALENDAR_DOCTYPE, "read"):
		return []
	rows = [
		dict(row)
		for row in frappe.get_list(
			CALENDAR_DOCTYPE,
			filters={"institution": institution, "enabled": 1},
			fields=["name", "institution", "academic_year", "is_current", "enabled", "start_date", "end_date", "notes", "modified"],
			order_by="is_current desc, start_date desc",
			page_length=MAX_ROWS,
		)
	]
	if not rows:
		return rows
	periods = frappe.get_all(
		PERIOD_DOCTYPE,
		filters={"parent": ["in", [row["name"] for row in rows]], "parenttype": CALENDAR_DOCTYPE},
		fields=["name", "parent", "academic_term", "start_date", "end_date", "sequence", "result_publication_date"],
		order_by="parent asc, sequence asc, start_date asc",
		limit_page_length=MAX_ROWS * 4,
	)
	by_calendar: dict[str, list[dict]] = defaultdict(list)
	for period in periods:
		by_calendar[period.parent].append(dict(period))
	today = getdate(nowdate())
	for calendar in rows:
		calendar_periods = by_calendar.get(calendar["name"], [])
		current_period = next((row for row in calendar_periods if row.get("start_date") and row.get("end_date") and getdate(row.start_date) <= today <= getdate(row.end_date)), None)
		calendar["periods"] = calendar_periods
		calendar["period_count"] = len(calendar_periods)
		calendar["current_period"] = current_period
		calendar["contains_today"] = bool(calendar.get("start_date") and calendar.get("end_date") and getdate(calendar["start_date"]) <= today <= getdate(calendar["end_date"]))
		calendar["has_calendar_gap_today"] = bool(calendar["contains_today"] and not current_period)
	return rows


def _build_hierarchy(departments: list[dict], programmes: list[dict], groups: list[dict]) -> list[dict]:
	groups_by_program: dict[str, list[dict]] = defaultdict(list)
	for group in groups:
		groups_by_program[group.program].append(dict(group))
	programmes_by_department: dict[str, list[dict]] = defaultdict(list)
	for programme in programmes:
		row = dict(programme)
		row["student_groups"] = groups_by_program.get(programme.name, [])
		programmes_by_department[programme.department].append(row)
	children: dict[str | None, list[dict]] = defaultdict(list)
	for department in departments:
		row = dict(department)
		row["programmes"] = programmes_by_department.get(department.name, [])
		row["children"] = []
		children[department.parent_department or None].append(row)
	by_name = {row["name"]: row for rows in children.values() for row in rows}
	for parent, rows in children.items():
		if parent and parent in by_name:
			by_name[parent]["children"].extend(rows)
	return children.get(None, []) + [row for parent, rows in children.items() if parent and parent not in by_name for row in rows]


def _effective_calendar(calendars: list[dict]) -> dict | None:
	if not calendars:
		return None
	explicit = next((row for row in calendars if cint(row.get("is_current"))), None)
	if explicit:
		return explicit
	today = getdate(nowdate())
	covering = [row for row in calendars if row.get("start_date") and row.get("end_date") and getdate(row["start_date"]) <= today <= getdate(row["end_date"])]
	return (sorted(covering, key=lambda row: (getdate(row.get("start_date")), row.get("modified") or ""), reverse=True)[0] if covering else sorted(calendars, key=lambda row: (getdate(row.get("start_date")), row.get("modified") or ""), reverse=True)[0])


def _build_readiness(institution: str | None, departments: list[dict], programmes: list[dict], groups: list[dict], calendars: list[dict]) -> dict:
	issues = []
	orphan_programmes = [row for row in programmes if not row.get("department")]
	orphan_groups = [row for row in groups if not row.get("program") or not row.get("eduedge_school_branch") or not row.get("academic_year")]
	if not departments:
		issues.append({"code": "no_departments", "severity": "danger", "message": _("No Department, Faculty, School, or School Section is configured.")})
	if not programmes:
		issues.append({"code": "no_programmes", "severity": "danger", "message": _("No Programme or Class is configured beneath the academic hierarchy.")})
	if orphan_programmes:
		issues.append({"code": "programmes_without_department", "severity": "danger", "message": _("{0} Programme(s) or Class(es) have no Department / School Section.").format(len(orphan_programmes))})
	if not groups:
		issues.append({"code": "no_student_groups", "severity": "warning", "message": _("No Class Arm, Level, Lecture Group, or Training Class is configured yet.")})
	if orphan_groups:
		issues.append({"code": "incomplete_student_groups", "severity": "danger", "message": _("{0} Student Group(s) have incomplete Programme, Branch, or Academic Session context.").format(len(orphan_groups))})
	effective = _effective_calendar(calendars)
	if not effective:
		issues.append({"code": "no_current_calendar", "severity": "danger", "message": _("No enabled Institution Academic Calendar is configured.")})
	else:
		if not effective.get("period_count"):
			issues.append({"code": "calendar_without_periods", "severity": "danger", "message": _("The current Academic Session calendar has no Terms / Semesters.")})
		if effective.get("has_calendar_gap_today"):
			issues.append({"code": "calendar_gap", "severity": "warning", "message": _("Today falls inside the Academic Session but outside every configured Term / Semester.")})
	return {
		"institution": institution,
		"ready": not any(row["severity"] == "danger" for row in issues),
		"issues": issues,
		"department_count": len(departments),
		"programme_count": len(programmes),
		"student_group_count": len(groups),
		"calendar_count": len(calendars),
		"current_calendar": effective.get("name") if effective else None,
		"current_academic_year": effective.get("academic_year") if effective else None,
		"current_academic_term": (effective.get("current_period") or {}).get("academic_term") if effective else None,
	}


@frappe.whitelist(methods=["POST"])
def save_department(
	institution: str,
	department_name: str,
	department: str | None = None,
	parent_department: str | None = None,
	is_group: int | str = 1,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_department")
	institution_doc = frappe.get_doc("EduEdge Institution", institution)
	institution_doc.check_permission("read")
	if department:
		doc = frappe.get_doc("Department", department)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("Department", "create"):
			frappe.throw(_("You are not permitted to create Departments / School Sections."), frappe.PermissionError)
		doc = frappe.new_doc("Department")
	doc.department_name = str(department_name or "").strip()
	doc.company = institution_doc.company
	doc.parent_department = parent_department or None
	doc.is_group = cint(is_group)
	doc.set(INSTITUTION_FIELD, institution)
	doc.save()
	_validate_department(doc.name, institution)
	return {"name": doc.name, "department_name": doc.department_name, "parent_department": doc.parent_department, "is_group": cint(doc.is_group)}
