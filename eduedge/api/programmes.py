from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_hierarchy import _validate_department
from eduedge.education.academic_progression import (
	LEVEL_PROGRESSION,
	MANUAL_PROGRESSION,
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_PROMOTION,
	PROGRAM_SEQUENCE_FIELD,
	PROGRAM_TERMINAL_FIELD,
	default_progression_mode,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context

DEFAULT_PAGE_LENGTH = 25
MAX_PAGE_LENGTH = 50
MAX_OPTION_ROWS = 500
MAX_DEPARTMENT_OPTIONS = 100
MAX_CURRICULUM_OPTIONS = 1000
PROGRESSION_FIELDS = (
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_SEQUENCE_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_TERMINAL_FIELD,
	PROGRAM_ALLOW_REPETITION_FIELD,
)


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_programme_read() -> None:
	_require_login()
	if not frappe.has_permission("Program", "read"):
		frappe.throw(_("You are not permitted to view Classes / Programmes."), frappe.PermissionError)


@frappe.whitelist()
def get_programmes_page(
	institution: str | None = None,
	department: str | None = None,
	search: str | None = None,
	start: int | str = 0,
	page_length: int | str = DEFAULT_PAGE_LENGTH,
	**_legacy_filters,
) -> dict:
	_require_programme_read()
	start = max(cint(start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
	institution = str(institution or "").strip() or None
	department = str(department or "").strip() or None
	search = str(search or "").strip()

	if institution:
		_assert_institution_access(institution)
	if department:
		_assert_department_context(department, institution)

	filters: dict[str, Any] = {}
	if institution:
		filters[INSTITUTION_FIELD] = institution
	if department:
		filters["department"] = department
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {
			"name": ["like", like],
			"program_name": ["like", like],
			"program_abbreviation": ["like", like],
			"department": ["like", like],
		}

	fields = ["name", "program_name", "program_abbreviation", "department", INSTITUTION_FIELD, "modified"]
	meta = frappe.get_meta("Program")
	if meta.has_field("enabled"):
		fields.append("enabled")
	for fieldname in PROGRESSION_FIELDS:
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Program",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="department asc, program_name asc, name asc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	_attach_programme_counts(rows)
	institutions = _list_institutions()
	departments = _list_departments(institution)
	return {
		"active_context": get_effective_institution_context(institution=institution),
		"filters": {"institution": institution, "department": department, "search": search},
		"programmes": rows,
		"institutions": institutions,
		"departments": departments,
		"progression_modes": [PROGRAM_PROMOTION, LEVEL_PROGRESSION, MANUAL_PROGRESSION],
		"summary": {
			"total_programmes": _count_programmes(filters, or_filters),
			"visible_programmes": len(rows),
			"course_rows": sum(cint(row.get("course_count")) for row in rows),
			"active_offerings": sum(cint(row.get("active_offering_count")) for row in rows),
			"unclassified_visible": sum(
				1 for row in rows if not row.get(INSTITUTION_FIELD) or not row.get("department")
			),
		},
		"paging": {
			"start": start,
			"page_length": page_length,
			"has_more": has_more,
			"next_start": start + len(rows),
		},
		"permissions": {
			"can_create": bool(frappe.has_permission("Program", "create")),
			"can_write": bool(frappe.has_permission("Program", "write")),
			"can_create_department": bool(frappe.has_permission("Department", "create")),
			"can_write_department": bool(frappe.has_permission("Department", "write")),
		},
	}


def _count_programmes(filters: dict, or_filters: dict | None) -> int:
	rows = frappe.get_list(
		"Program",
		filters=filters,
		or_filters=or_filters,
		fields=[{"COUNT": "name", "as": "record_count"}],
		page_length=1,
	)
	return cint(rows[0].record_count) if rows else 0


def _attach_programme_counts(rows: list[dict]) -> None:
	names = [row.name for row in rows]
	if not names:
		return
	course_counts = {}
	if frappe.db.exists("DocType", "Program Course"):
		counts = frappe.get_all(
			"Program Course",
			filters={"parent": ["in", names], "parenttype": "Program"},
			fields=["parent", {"COUNT": "name", "as": "record_count"}],
			group_by="parent",
		)
		course_counts = {row.parent: cint(row.record_count) for row in counts}
	offering_counts = {}
	if frappe.db.exists("DocType", "EduEdge Program Offering") and frappe.has_permission("EduEdge Program Offering", "read"):
		counts = frappe.get_list(
			"EduEdge Program Offering",
			filters={"program": ["in", names], "is_active": 1},
			fields=["program", {"COUNT": "name", "as": "record_count"}],
			group_by="program",
			page_length=max(len(names), 1),
		)
		offering_counts = {row.program: cint(row.record_count) for row in counts}
	for row in rows:
		row["course_count"] = course_counts.get(row.name, 0)
		row["active_offering_count"] = offering_counts.get(row.name, 0)


def _list_institutions() -> list[dict]:
	if not frappe.has_permission("EduEdge Institution", "read"):
		return []
	rows = frappe.get_list(
		"EduEdge Institution",
		filters={"enabled": 1},
		fields=["name", "institution_name", "institution_type", "company"],
		order_by="institution_name asc",
		page_length=MAX_OPTION_ROWS,
	)
	for row in rows:
		context = get_effective_institution_context(institution=row.name)
		row["institution_type_name"] = context.get("institution_type_name") or row.get("institution_type")
		row["context"] = context
	return rows


def _list_departments(institution: str | None = None) -> list[dict]:
	if not frappe.db.exists("DocType", "Department") or not frappe.has_permission("Department", "read"):
		return []
	meta = frappe.get_meta("Department")
	filters: dict = {}
	if meta.has_field("disabled"):
		filters["disabled"] = 0
	if institution and meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = institution
	elif institution and meta.has_field("company"):
		filters["company"] = _institution_company(institution)
	fields = ["name", "department_name", "parent_department", "is_group", "company"]
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	return frappe.get_list(
		"Department",
		filters=filters,
		fields=fields,
		order_by="lft asc, department_name asc",
		page_length=MAX_OPTION_ROWS,
	)


def _assert_institution_access(institution: str) -> None:
	doc = frappe.get_doc("EduEdge Institution", institution)
	doc.check_permission("read")
	if not cint(doc.enabled):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)


def _institution_company(institution: str | None) -> str | None:
	return frappe.db.get_value("EduEdge Institution", institution, "company") if institution else None


def _assert_department_context(department: str, institution: str | None) -> None:
	if not frappe.db.exists("DocType", "Department"):
		frappe.throw(_("Department is unavailable."), frappe.DoesNotExistError)
	doc = frappe.get_doc("Department", department)
	doc.check_permission("read")
	if institution:
		_validate_department(department, institution)


def _programme_doc(programme: str, permission_type: str = "read"):
	name = str(programme or "").strip()
	if not name:
		frappe.throw(_("Select a Class / Programme."), frappe.ValidationError)
	doc = frappe.get_doc("Program", name)
	doc.check_permission(permission_type)
	institution = str(doc.get(INSTITUTION_FIELD) or "").strip()
	if not institution:
		frappe.throw(_("The selected Class / Programme has no Institution context."), frappe.ValidationError)
	_assert_institution_access(institution)
	return doc, institution


def _course_fields() -> list[str]:
	fields = ["name", "course_name", "department", "description", "default_grading_scale"]
	if frappe.get_meta("Course").has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	return fields


def _programme_curriculum_payload(programme: str) -> dict:
	doc, institution = _programme_doc(programme, "read")
	configured_names = [str(row.course or "").strip() for row in doc.get("courses") or [] if row.course]
	course_rows = frappe.get_list(
		"Course",
		filters={"name": ["in", configured_names]} if configured_names else {"name": ["in", ["__none__"]]},
		fields=_course_fields(),
		order_by="course_name asc",
		page_length=max(len(configured_names), 1),
	) if frappe.has_permission("Course", "read") else []
	course_map = {row.name: dict(row) for row in course_rows}
	configured = []
	for child in doc.get("courses") or []:
		name = str(child.course or "").strip()
		if not name:
			continue
		details = course_map.get(name, {})
		configured.append({
			"name": name,
			"course_name": details.get("course_name") or name,
			"department": details.get("department") or "",
			"default_grading_scale": details.get("default_grading_scale") or "",
			"required": cint(child.get("required", 1)),
			"idx": cint(child.idx),
			"institution_mismatch": bool(details.get(INSTITUTION_FIELD) and details.get(INSTITUTION_FIELD) != institution),
		})

	available_filters: dict[str, Any] = {"name": ["not in", configured_names]} if configured_names else {}
	if frappe.get_meta("Course").has_field(INSTITUTION_FIELD):
		available_filters[INSTITUTION_FIELD] = institution
	available = frappe.get_list(
		"Course",
		filters=available_filters,
		fields=_course_fields(),
		order_by="course_name asc",
		page_length=MAX_CURRICULUM_OPTIONS,
	) if frappe.has_permission("Course", "read") else []

	active_offerings = frappe.get_list(
		"EduEdge Program Offering",
		filters={"program": doc.name, "is_active": 1},
		fields=["name", "offering_title", "school_branch", "academic_year", "academic_term"],
		order_by="academic_year desc, offering_title asc",
		page_length=MAX_OPTION_ROWS,
	) if frappe.db.exists("DocType", "EduEdge Program Offering") and frappe.has_permission("EduEdge Program Offering", "read") else []

	return {
		"programme": {
			"name": doc.name,
			"program_name": doc.program_name,
			"institution": institution,
			"department": doc.department,
		},
		"context": get_effective_institution_context(institution=institution),
		"configured_courses": configured,
		"available_courses": available,
		"active_offerings": active_offerings,
		"permissions": {
			"can_add_courses": bool(
				frappe.has_permission("Program", "write")
				and frappe.has_permission("Course", "read")
			),
			"can_remove_courses": False,
		},
		"governance_note": _(
			"Curriculum additions update the Class / Programme master and apply to its current and future Class / Programme Offerings. Subject removal requires a separate impact review."
		),
	}


@frappe.whitelist()
def get_programme_curriculum(programme: str) -> dict:
	_require_programme_read()
	return _programme_curriculum_payload(programme)


def _list_values(value) -> list[str]:
	if isinstance(value, str):
		try:
			parsed = frappe.parse_json(value)
		except Exception:
			parsed = [value]
		value = parsed
	if not isinstance(value, (list, tuple, set)):
		return []
	result = []
	for entry in value:
		name = str(entry or "").strip()
		if name and name not in result:
			result.append(name)
	return result


@frappe.whitelist(methods=["POST"])
def add_programme_curriculum_courses(programme: str, courses: str | list | None = None) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="add_programme_curriculum_courses")
	doc, institution = _programme_doc(programme, "write")
	selected = _list_values(courses)
	if not selected:
		frappe.throw(_("Select at least one Institution Subject / Course to add."), frappe.ValidationError)
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to view Subjects / Courses."), frappe.PermissionError)

	existing = {str(row.course or "").strip() for row in doc.get("courses") or [] if row.course}
	created = []
	for course in selected:
		course_doc = frappe.get_doc("Course", course)
		course_doc.check_permission("read")
		course_institution = str(course_doc.get(INSTITUTION_FIELD) or "").strip()
		if course_institution and course_institution != institution:
			frappe.throw(
				_("Subject / Course {0} belongs to another Institution.").format(course_doc.course_name or course),
				frappe.ValidationError,
			)
		if course in existing:
			continue
		doc.append("courses", {"course": course, "required": 1})
		existing.add(course)
		created.append(course)
	if created:
		doc.save()
	return {
		"added": created,
		"added_count": len(created),
		"curriculum": _programme_curriculum_payload(doc.name),
	}


@frappe.whitelist()
def get_programme_terminology(institution: str | None = None) -> dict:
	"""Return the permission-checked terminology for a Program document or editor."""
	_require_programme_read()
	institution = str(institution or "").strip() or None
	if institution:
		_assert_institution_access(institution)
	return get_effective_institution_context(institution=institution)


@frappe.whitelist()
def search_departments(txt: str | None = None, institution: str | None = None) -> list[dict]:
	_require_programme_read()
	institution = str(institution or "").strip() or None
	if institution:
		_assert_institution_access(institution)
	txt = str(txt or "").strip()
	rows = _list_departments(institution)
	if txt:
		needle = txt.casefold()
		rows = [
			row for row in rows
			if needle in str(row.get("name") or "").casefold()
			or needle in str(row.get("department_name") or "").casefold()
		]
	return [
		{
			"value": row.name,
			"label": row.get("department_name") or row.name,
			"parent_department": row.get("parent_department") or "",
			"is_group": cint(row.get("is_group")),
		}
		for row in rows[:MAX_DEPARTMENT_OPTIONS]
	]


@frappe.whitelist()
def get_programme_progression_options(institution: str, programme: str | None = None) -> dict:
	"""Return permission-aware same-Institution progression targets for the smart Class editor."""
	_require_programme_read()
	institution = str(institution or "").strip()
	if not institution:
		frappe.throw(_("Select an Institution before choosing a progression target."), frappe.ValidationError)
	_assert_institution_access(institution)
	filters: dict[str, Any] = {INSTITUTION_FIELD: institution}
	if programme:
		filters["name"] = ["!=", str(programme).strip()]
	meta = frappe.get_meta("Program")
	fields = ["name", "program_name", "program_abbreviation"]
	for fieldname in (PROGRAM_PROGRESSION_MODE_FIELD, PROGRAM_TERMINAL_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Program",
		filters=filters,
		fields=fields,
		order_by="program_name asc, name asc",
		page_length=MAX_OPTION_ROWS,
	)
	return {
		"institution": institution,
		"programme": str(programme or "").strip() or None,
		"default_mode": default_progression_mode(institution),
		"modes": [PROGRAM_PROMOTION, LEVEL_PROGRESSION, MANUAL_PROGRESSION],
		"programmes": rows,
	}


@frappe.whitelist(methods=["POST"])
def save_programme(
	program_name: str,
	institution: str,
	department: str,
	programme: str | None = None,
	program_abbreviation: str | None = None,
	progression_mode: str | None = None,
	progression_sequence: int | str | None = None,
	next_program: str | None = None,
	terminal_program: int | str = 0,
	allow_repetition: int | str = 1,
	**_legacy_values,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_programme")
	_assert_institution_access(institution)
	_assert_department_context(department, institution)
	if programme:
		doc = frappe.get_doc("Program", programme)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("Program", "create"):
			frappe.throw(_("You are not permitted to create Classes / Programmes."), frappe.PermissionError)
		doc = frappe.new_doc("Program")
	doc.program_name = str(program_name or "").strip()
	doc.program_abbreviation = str(program_abbreviation or "").strip() or None
	doc.department = str(department or "").strip()
	doc.set(INSTITUTION_FIELD, institution)
	meta = frappe.get_meta("Program")
	if meta.has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		doc.set(PROGRAM_PROGRESSION_MODE_FIELD, str(progression_mode or "").strip() or default_progression_mode(institution))
	if meta.has_field(PROGRAM_SEQUENCE_FIELD):
		doc.set(PROGRAM_SEQUENCE_FIELD, cint(progression_sequence) or 10)
	if meta.has_field(PROGRAM_NEXT_FIELD):
		doc.set(PROGRAM_NEXT_FIELD, str(next_program or "").strip() or None)
	if meta.has_field(PROGRAM_TERMINAL_FIELD):
		doc.set(PROGRAM_TERMINAL_FIELD, cint(terminal_program))
	if meta.has_field(PROGRAM_ALLOW_REPETITION_FIELD):
		doc.set(PROGRAM_ALLOW_REPETITION_FIELD, cint(allow_repetition))
	doc.save()
	return {
		"name": doc.name,
		"program_name": doc.program_name,
		"institution": doc.get(INSTITUTION_FIELD),
		"department": doc.department,
		"progression_mode": doc.get(PROGRAM_PROGRESSION_MODE_FIELD),
		"progression_sequence": doc.get(PROGRAM_SEQUENCE_FIELD),
		"next_program": doc.get(PROGRAM_NEXT_FIELD),
		"terminal_program": cint(doc.get(PROGRAM_TERMINAL_FIELD)),
		"allow_repetition": cint(doc.get(PROGRAM_ALLOW_REPETITION_FIELD)),
	}
