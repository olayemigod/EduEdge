from __future__ import annotations

import frappe
from frappe import _

PROGRAM_RESOURCE = "programs"
PROGRAM_OFFERING_RESOURCE = "program_offerings"
INSTITUTION_FIELD = "eduedge_institution"
LEGACY_SECTION_FIELD = "eduedge_academic_section"


def ensure_contract(base) -> None:
	_ensure_program_contract(base)
	_ensure_offering_contract(base)


def _ensure_program_contract(base) -> None:
	config = base.RESOURCE_CONFIG.get(PROGRAM_RESOURCE)
	if not config:
		return
	for fieldname in ("program_name", "program_abbreviation", INSTITUTION_FIELD, "department"):
		if fieldname not in config.setdefault("search_fields", []):
			config["search_fields"].append(fieldname)
	config["columns"] = [
		{"fieldname": "program_name", "label": _("Program")},
		{"fieldname": "program_abbreviation", "label": _("Abbreviation")},
		{"fieldname": INSTITUTION_FIELD, "label": _("Institution")},
		{"fieldname": "department", "label": _("Department")},
	]
	config["filters"] = [
		{
			"fieldname": INSTITUTION_FIELD,
			"label": _("Institution"),
			"type": "Link",
			"options_doctype": "EduEdge Institution",
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"type": "Link",
			"options_doctype": "Department",
		},
	]
	config["editor_fields"] = [
		{
			"fieldname": INSTITUTION_FIELD,
			"label": _("Institution"),
			"type": "Link",
			"options_doctype": "EduEdge Institution",
			"required": True,
			"clear_fields": ["department"],
			"refresh_fields": ["department"],
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"type": "Link",
			"options_doctype": "Department",
			"required": True,
		},
		{"fieldname": "program_name", "label": _("Program Name"), "type": "Data", "required": True},
		{"fieldname": "program_abbreviation", "label": _("Program Abbreviation"), "type": "Data"},
	]
	config["advanced_note"] = _(
		"Select the Institution first, then its valid Faculty, Department, or School Section. Curriculum courses remain in the full Program form."
	)


def _ensure_offering_contract(base) -> None:
	config = base.RESOURCE_CONFIG.get(PROGRAM_OFFERING_RESOURCE)
	if not config:
		return
	config["title_field"] = "offering_title"
	for fieldname in (
		"offering_title",
		"offering_code",
		"study_mode",
		"delivery_mode",
		"student_batch",
		"academic_level",
	):
		if fieldname not in config.setdefault("search_fields", []):
			config["search_fields"].append(fieldname)
	config["columns"] = [
		{"fieldname": "offering_title", "label": _("Offering")},
		{"fieldname": "offering_code", "label": _("Code")},
		{"fieldname": "program", "label": _("Programme")},
		{"fieldname": "school_branch", "label": _("Branch")},
		{"fieldname": "academic_year", "label": _("Academic Year")},
		{"fieldname": "academic_term", "label": _("Term")},
		{"fieldname": "study_mode", "label": _("Study Mode")},
		{"fieldname": "delivery_mode", "label": _("Delivery Mode")},
		{"fieldname": "is_active", "label": _("Active"), "type": "Check"},
	]
	config["editor_fields"] = [
		{
			"fieldname": "school_branch",
			"label": _("School Branch / Campus"),
			"type": "Link",
			"options_doctype": "EduEdge School Branch",
			"required": True,
			"clear_fields": [
				"program",
				"academic_year",
				"academic_term",
				"academic_level",
				"student_batch",
			],
			"refresh_fields": [
				"program",
				"academic_year",
				"academic_term",
				"academic_level",
				"student_batch",
			],
		},
		{
			"fieldname": "program",
			"label": _("Program"),
			"type": "Link",
			"options_doctype": "Program",
			"required": True,
			"clear_fields": ["academic_level"],
			"refresh_fields": ["academic_level"],
		},
		{
			"fieldname": "academic_year",
			"label": _("Academic Year"),
			"type": "Link",
			"options_doctype": "Academic Year",
			"required": True,
			"clear_fields": ["academic_term"],
			"refresh_fields": ["academic_term"],
		},
		{
			"fieldname": "academic_term",
			"label": _("Academic Term"),
			"type": "Link",
			"options_doctype": "Academic Term",
		},
		{
			"fieldname": "academic_level",
			"label": _("Academic Level"),
			"type": "Link",
			"options_doctype": "EduEdge Academic Level",
		},
		{
			"fieldname": "student_batch",
			"label": _("Student Batch / Cohort"),
			"type": "Link",
			"options_doctype": "Student Batch Name",
		},
		{"fieldname": "offering_title", "label": _("Offering Title"), "type": "Data"},
		{"fieldname": "offering_code", "label": _("Offering Code"), "type": "Data"},
		{
			"fieldname": "study_mode",
			"label": _("Study Mode"),
			"type": "Select",
			"options": ["Full-Time", "Part-Time", "Weekend", "Evening", "Short Course", "Flexible"],
			"default": "Full-Time",
		},
		{
			"fieldname": "delivery_mode",
			"label": _("Delivery Mode"),
			"type": "Select",
			"options": ["Onsite", "Online", "Hybrid"],
			"default": "Onsite",
		},
		{"fieldname": "start_date", "label": _("Start Date"), "type": "Date"},
		{"fieldname": "end_date", "label": _("End Date"), "type": "Date"},
		{"fieldname": "is_active", "label": _("Active"), "type": "Check", "default": 1},
		{"fieldname": "admission_enabled", "label": _("Available for Admission"), "type": "Check", "default": 1},
		{"fieldname": "enrollment_enabled", "label": _("Available for Enrollment"), "type": "Check", "default": 1},
		{"fieldname": "capacity", "label": _("Capacity"), "type": "Int", "default": 0, "min": 0},
		{"fieldname": "application_start_date", "label": _("Application Start Date"), "type": "Date"},
		{"fieldname": "application_end_date", "label": _("Application End Date"), "type": "Date"},
		{"fieldname": "notes", "label": _("Notes"), "type": "Small Text"},
	]


def enrich_editor(base, result: dict, resource: str) -> dict:
	if resource not in {PROGRAM_RESOURCE, PROGRAM_OFFERING_RESOURCE}:
		return result
	values = result.get("values") or {}
	for field in result.get("fields") or []:
		options = search_options(base, resource, field.get("fieldname"), "", values)
		if options is not None:
			field["options"] = options
	return result


def search_options(base, resource: str, fieldname: str, txt: str, values: dict) -> list[dict] | None:
	if resource == PROGRAM_RESOURCE:
		institution = values.get(INSTITUTION_FIELD)
		if fieldname == INSTITUTION_FIELD:
			return _link_rows("EduEdge Institution", "institution_name", txt, {"enabled": 1})
		if fieldname == "department":
			if not institution:
				return []
			return _link_rows("Department", "department_name", txt, {INSTITUTION_FIELD: institution})
		return None

	if resource != PROGRAM_OFFERING_RESOURCE:
		return None
	branch = values.get("school_branch")
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution") if branch else None
	program = values.get("program")
	academic_year = values.get("academic_year")

	if fieldname == "program":
		if not institution:
			return []
		filters = {INSTITUTION_FIELD: institution} if frappe.get_meta("Program").has_field(INSTITUTION_FIELD) else {}
		return _link_rows("Program", "program_name", txt, filters)
	if fieldname == "academic_year":
		return _calendar_year_options(institution, txt)
	if fieldname == "academic_term":
		return _calendar_term_options(institution, academic_year, txt)
	if fieldname == "academic_level":
		if not institution or not program:
			return []
		filters = {"institution": institution, "enabled": 1}
		level_meta = frappe.get_meta("EduEdge Academic Level")
		if level_meta.has_field("program"):
			filters["program"] = program
		elif level_meta.has_field("eduedge_program"):
			filters["eduedge_program"] = program
		elif level_meta.has_field("academic_section"):
			section = frappe.db.get_value("Program", program, LEGACY_SECTION_FIELD)
			if section:
				filters["academic_section"] = section
		return _link_rows("EduEdge Academic Level", "level_name", txt, filters)
	if fieldname == "student_batch":
		if not institution:
			return []
		filters = {}
		if frappe.get_meta("Student Batch Name").has_field(INSTITUTION_FIELD):
			filters[INSTITUTION_FIELD] = institution
		return _link_rows("Student Batch Name", "name", txt, filters)
	return None


def _calendar_year_options(institution: str | None, txt: str) -> list[dict]:
	if not institution:
		return []
	calendars = frappe.get_list(
		"EduEdge Institution Academic Calendar",
		filters={"institution": institution, "enabled": 1},
		fields=["academic_year"],
		order_by="is_current desc, start_date desc",
		limit_page_length=30,
	)
	allowed = [row.academic_year for row in calendars if row.academic_year]
	if not allowed:
		return []
	return _link_rows("Academic Year", "name", txt, {"name": ["in", allowed]})


def _calendar_term_options(institution: str | None, academic_year: str | None, txt: str) -> list[dict]:
	if not institution or not academic_year:
		return []
	calendar = frappe.db.get_value(
		"EduEdge Institution Academic Calendar",
		{"institution": institution, "academic_year": academic_year, "enabled": 1},
		"name",
	)
	if not calendar:
		return []
	terms = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={
			"parent": calendar,
			"parenttype": "EduEdge Institution Academic Calendar",
			"parentfield": "periods",
		},
		pluck="academic_term",
		order_by="sequence asc, start_date asc",
		limit_page_length=30,
	)
	allowed = [term for term in terms if term]
	if not allowed:
		return []
	return _link_rows("Academic Term", "name", txt, {"name": ["in", allowed]})


def _link_rows(doctype: str, label_field: str, txt: str, filters: dict) -> list[dict]:
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	if label_field != "name" and meta.has_field(label_field):
		fields.append(label_field)
	or_filters = None
	if str(txt or "").strip():
		needle = f"%{str(txt).strip()}%"
		or_filters = [[field, "like", needle] for field in fields]
	rows = frappe.get_list(
		doctype,
		filters={key: value for key, value in filters.items() if value not in (None, "")},
		or_filters=or_filters,
		fields=fields,
		order_by=f"{label_field} asc" if label_field in fields else "modified desc",
		limit_page_length=30,
	)
	return [
		{
			"value": row.name,
			"label": row.get(label_field) or row.name,
			"description": row.name if label_field != "name" else "",
		}
		for row in rows
	]
