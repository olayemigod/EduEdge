from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context

MAX_ROWS = 500


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
def get_academic_foundation() -> dict:
	_require_login()
	institutions = []
	if frappe.has_permission("EduEdge Institution", "read"):
		institutions = frappe.get_list(
			"EduEdge Institution",
			filters={"enabled": 1},
			fields=["name", "institution_name", "institution_code", "institution_type", "company"],
			order_by="institution_name asc",
			limit_page_length=MAX_ROWS,
		)
	sections = _safe_list(
		"EduEdge Academic Section",
		["name", "section_name", "section_code", "institution", "sequence", "enabled"],
		"institution asc, sequence asc, section_name asc",
	)
	levels = _safe_list(
		"EduEdge Academic Level",
		["name", "level_name", "level_code", "institution", "academic_section", "sequence", "next_level", "enabled"],
		"institution asc, sequence asc, level_name asc",
	)
	calendars = _safe_list(
		"EduEdge Institution Academic Calendar",
		["name", "institution", "academic_year", "is_current", "enabled", "start_date", "end_date"],
		"is_current desc, start_date desc",
	)
	return {
		"active_context": get_effective_institution_context(),
		"institutions": institutions,
		"sections": sections,
		"levels": levels,
		"calendars": calendars,
		"permissions": {
			"can_create_section": bool(frappe.has_permission("EduEdge Academic Section", "create")),
			"can_write_section": bool(frappe.has_permission("EduEdge Academic Section", "write")),
			"can_create_level": bool(frappe.has_permission("EduEdge Academic Level", "create")),
			"can_write_level": bool(frappe.has_permission("EduEdge Academic Level", "write")),
			"can_create_calendar": bool(frappe.has_permission("EduEdge Institution Academic Calendar", "create")),
		},
	}


def _safe_list(doctype: str, fields: list[str], order_by: str) -> list[dict]:
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	return frappe.get_list(
		doctype,
		fields=fields,
		order_by=order_by,
		limit_page_length=MAX_ROWS,
	)


@frappe.whitelist()
def save_academic_section(
	institution: str,
	section_name: str,
	section_code: str,
	section: str | None = None,
	sequence: int | str = 10,
	enabled: int | str = 1,
	description: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_section")
	if section:
		doc = frappe.get_doc("EduEdge Academic Section", section)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Academic Section", "create"):
			frappe.throw(_("You are not permitted to create Academic Sections."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Academic Section")
	doc.update(
		{
			"institution": institution,
			"section_name": str(section_name or "").strip(),
			"section_code": str(section_code or "").strip(),
			"sequence": cint(sequence) or 10,
			"enabled": cint(enabled),
			"description": description or "",
		}
	)
	doc.save()
	return {"name": doc.name, "section_name": doc.section_name}


@frappe.whitelist()
def save_academic_level(
	institution: str,
	level_name: str,
	level_code: str,
	level: str | None = None,
	academic_section: str | None = None,
	sequence: int | str = 10,
	next_level: str | None = None,
	enabled: int | str = 1,
	description: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_level")
	if level:
		doc = frappe.get_doc("EduEdge Academic Level", level)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Academic Level", "create"):
			frappe.throw(_("You are not permitted to create Academic Levels."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Academic Level")
	doc.update(
		{
			"institution": institution,
			"level_name": str(level_name or "").strip(),
			"level_code": str(level_code or "").strip(),
			"academic_section": academic_section or None,
			"sequence": cint(sequence) or 10,
			"next_level": next_level or None,
			"enabled": cint(enabled),
			"description": description or "",
		}
	)
	doc.save()
	return {"name": doc.name, "level_name": doc.level_name}
