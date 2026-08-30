from __future__ import annotations

import re

import frappe

from eduedge.education.academic_fields import (
	ACADEMIC_LEVEL_FIELD,
	ACADEMIC_SECTION_FIELD,
	INSTITUTION_FIELD,
)
from eduedge.education.native_hierarchy_migration import ensure_native_academic_context_foundation

SCHOOL_TYPES = {"PRIMARY", "SECONDARY"}


def execute() -> None:
	"""Migrate unambiguous legacy hierarchy records without deleting history.

	- Legacy Academic Sections become native Departments through the idempotent,
	  collision-safe foundation installer.
	- Primary/Secondary Academic Levels become native Programs beneath the mapped
	  Department because JSS 1 / Nursery 1 are Classes in the agreed native model.
	- Blank Student Group.program values linked to those legacy Levels are filled.
	- Tertiary Levels are deliberately not auto-created because 100/200 Level needs
	  Branch, Session and Term context as a native Student Group.
	"""
	ensure_native_academic_context_foundation()
	if not (
		frappe.db.exists("DocType", "EduEdge Academic Section")
		and frappe.db.exists("DocType", "EduEdge Academic Level")
		and frappe.db.exists("DocType", "Department")
		and frappe.db.exists("DocType", "Program")
	):
		return

	section_map = _section_department_map()
	levels = frappe.get_all(
		"EduEdge Academic Level",
		filters={"enabled": 1},
		fields=["name", "level_name", "level_code", "institution", "academic_section"],
		order_by="creation asc",
	)
	for level in levels:
		institution_type = frappe.db.get_value("EduEdge Institution", level.institution, "institution_type")
		if institution_type not in SCHOOL_TYPES:
			continue
		department = section_map.get(level.academic_section)
		if not department or not level.level_name:
			continue
		program = _get_or_create_program(level, department)
		_backfill_student_groups(level.name, program)
	frappe.clear_cache(doctype="Program")
	frappe.clear_cache(doctype="Student Group")


def _section_department_map() -> dict[str, str]:
	mapping: dict[str, str] = {}
	sections = frappe.get_all(
		"EduEdge Academic Section",
		fields=["name", "section_name", "institution"],
		order_by="creation asc",
	)
	for section in sections:
		if not section.section_name or not section.institution:
			continue
		filters = {"department_name": section.section_name}
		department_meta = frappe.get_meta("Department")
		if department_meta.has_field(INSTITUTION_FIELD):
			filters[INSTITUTION_FIELD] = section.institution
		else:
			filters["company"] = frappe.db.get_value("EduEdge Institution", section.institution, "company")
		department = frappe.db.get_value("Department", filters, "name")
		if not department and department_meta.has_field(INSTITUTION_FIELD):
			# Collision-safe migration may append the Institution code to the visible
			# Department name. The ownership field remains the authoritative lookup.
			department = frappe.db.get_value(
				"Department",
				{INSTITUTION_FIELD: section.institution, "department_name": ["like", f"{section.section_name}%"]},
				"name",
			)
		if department:
			mapping[section.name] = department
	return mapping


def _get_or_create_program(level, department: str) -> str:
	program_meta = frappe.get_meta("Program")
	filters = {"program_name": level.level_name}
	if program_meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = level.institution
	program = frappe.db.get_value("Program", filters, "name")
	if program:
		_sync_program_context(program, level, department, program_meta)
		return program

	# ERPNext Education names Program from unique program_name. A legacy site can
	# therefore already contain "Primary 1" while its new Institution field is
	# blank or owned by another school. Reuse only when ownership/context is
	# compatible; otherwise create a deterministic collision-safe visible name.
	existing_fields = ["name", "department"]
	if program_meta.has_field(INSTITUTION_FIELD):
		existing_fields.append(INSTITUTION_FIELD)
	if program_meta.has_field(ACADEMIC_SECTION_FIELD):
		existing_fields.append(ACADEMIC_SECTION_FIELD)
	existing = frappe.db.get_value(
		"Program",
		{"program_name": level.level_name},
		existing_fields,
		as_dict=True,
	)
	if existing and _program_is_compatible(existing, level, department, program_meta):
		program = existing.name
		_sync_program_context(program, level, department, program_meta)
		return program

	program_name = _available_program_name(level.level_name, level.institution)
	abbreviation = str(level.level_code or "").strip() or _abbreviation(program_name)
	values = {
		"doctype": "Program",
		"program_name": program_name,
		"program_abbreviation": abbreviation,
		"department": department,
	}
	if program_meta.has_field(INSTITUTION_FIELD):
		values[INSTITUTION_FIELD] = level.institution
	if program_meta.has_field(ACADEMIC_SECTION_FIELD):
		values[ACADEMIC_SECTION_FIELD] = level.academic_section
	doc = frappe.get_doc(values)
	doc.insert(ignore_permissions=True)
	return doc.name


def _program_is_compatible(existing, level, department: str, program_meta) -> bool:
	if not existing:
		return False
	if not program_meta.has_field(INSTITUTION_FIELD):
		return True
	owner = existing.get(INSTITUTION_FIELD)
	if owner:
		return owner == level.institution
	# Do not silently claim an unowned global Program unless its legacy Section or
	# Department already ties it to this exact academic hierarchy.
	if existing.get("department") and existing.get("department") == department:
		return True
	if program_meta.has_field(ACADEMIC_SECTION_FIELD):
		section = existing.get(ACADEMIC_SECTION_FIELD)
		if section and section == level.academic_section:
			return True
	return False


def _sync_program_context(program: str, level, department: str, program_meta) -> None:
	updates = {}
	current_department = frappe.db.get_value("Program", program, "department")
	if not current_department:
		updates["department"] = department
	if program_meta.has_field(INSTITUTION_FIELD) and not frappe.db.get_value("Program", program, INSTITUTION_FIELD):
		updates[INSTITUTION_FIELD] = level.institution
	if program_meta.has_field(ACADEMIC_SECTION_FIELD) and not frappe.db.get_value("Program", program, ACADEMIC_SECTION_FIELD):
		updates[ACADEMIC_SECTION_FIELD] = level.academic_section
	if updates:
		frappe.db.set_value("Program", program, updates, update_modified=False)


def _available_program_name(base_name: str, institution: str) -> str:
	base_name = str(base_name or "").strip()
	institution_code = frappe.db.get_value("EduEdge Institution", institution, "institution_code") or institution
	code = re.sub(r"[^A-Za-z0-9]+", "-", str(institution_code or "").strip()).strip("-") or "Institution"
	candidate = base_name
	counter = 1
	while frappe.db.exists("Program", {"program_name": candidate}):
		suffix = f" ({code})" if counter == 1 else f" ({code}-{counter})"
		candidate = f"{base_name}{suffix}"
		counter += 1
	return candidate


def _backfill_student_groups(level: str, program: str) -> None:
	meta = frappe.get_meta("Student Group")
	if not meta.has_field(ACADEMIC_LEVEL_FIELD):
		return
	groups = frappe.get_all(
		"Student Group",
		filters={ACADEMIC_LEVEL_FIELD: level, "program": ["is", "not set"]},
		pluck="name",
	)
	for group in groups:
		frappe.db.set_value("Student Group", group, "program", program, update_modified=False)


def _abbreviation(value: str) -> str:
	parts = re.findall(r"[A-Za-z0-9]+", str(value or ""))
	if not parts:
		return "CLASS"
	candidate = "".join(part[0] for part in parts).upper()
	return (candidate or re.sub(r"\W+", "", value).upper() or "CLASS")[:12]
