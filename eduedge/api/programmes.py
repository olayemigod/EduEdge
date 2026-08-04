from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_hierarchy import _validate_department
from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context

DEFAULT_PAGE_LENGTH = 25
MAX_PAGE_LENGTH = 50
MAX_OPTION_ROWS = 500
MAX_DEPARTMENT_OPTIONS = 100


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


@frappe.whitelist(methods=["POST"])
def save_programme(
	program_name: str,
	institution: str,
	department: str,
	programme: str | None = None,
	program_abbreviation: str | None = None,
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
	doc.save()
	return {
		"name": doc.name,
		"program_name": doc.program_name,
		"institution": doc.get(INSTITUTION_FIELD),
		"department": doc.department,
	}
