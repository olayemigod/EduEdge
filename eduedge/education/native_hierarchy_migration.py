from __future__ import annotations

from collections import defaultdict

import frappe

from eduedge.education import academic_fields
from eduedge.education.academic_fields import ACADEMIC_SECTION_FIELD, INSTITUTION_FIELD
from eduedge.education.academic_progression import ensure_academic_progression_foundation
from eduedge.education.native_identity import DISPLAY_FIELD
from eduedge.education.progression_terminology import ensure_progression_terminology


def ensure_native_academic_context_foundation() -> None:
	"""Install the canonical native academic schema, identity, progression, and migration layer."""
	academic_fields.ensure_academic_context_foundation()
	ensure_academic_progression_foundation()
	ensure_progression_terminology()


def backfill_legacy_sections_to_departments() -> None:
	if not (
		frappe.db.exists("DocType", "Department")
		and frappe.db.exists("DocType", "EduEdge Academic Section")
		and frappe.get_meta("Department").has_field(INSTITUTION_FIELD)
	):
		return
	sections = frappe.get_all(
		"EduEdge Academic Section",
		fields=["name", "section_name", "institution", "enabled"],
		order_by="creation asc",
	)
	institution_rows = {
		row.name: row
		for row in frappe.get_all(
			"EduEdge Institution",
			filters={"name": ["in", list({row.institution for row in sections if row.institution})]},
			fields=["name", "institution_code", "company"],
			page_length=max(len(sections), 1),
		)
	}
	owners_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
	for section in sections:
		institution = institution_rows.get(section.institution)
		if institution and section.section_name:
			owners_by_key[(institution.company, _normalise(section.section_name))].add(section.institution)

	mapping: dict[str, str] = {}
	for section in sections:
		institution = institution_rows.get(section.institution)
		if not institution or not institution.company or not section.section_name:
			continue
		department = _exact_owned_department(section.section_name, institution.company, section.institution)
		if not department:
			unowned = _unowned_department(section.section_name, institution.company)
			unambiguous = len(owners_by_key[(institution.company, _normalise(section.section_name))]) == 1
			if unowned and unambiguous:
				updates = {INSTITUTION_FIELD: section.institution}
				if frappe.get_meta("Department").has_field(DISPLAY_FIELD):
					updates[DISPLAY_FIELD] = section.section_name
				frappe.db.set_value("Department", unowned, updates, update_modified=False)
				department = unowned
		if not department:
			values = {
				"doctype": "Department",
				"department_name": section.section_name,
				"company": institution.company,
				"is_group": 1,
				INSTITUTION_FIELD: section.institution,
			}
			if frappe.get_meta("Department").has_field(DISPLAY_FIELD):
				values[DISPLAY_FIELD] = section.section_name
			doc = frappe.get_doc(values)
			doc.insert(ignore_permissions=True)
			department = doc.name
		mapping[section.name] = department

	if mapping and frappe.get_meta("Program").has_field(ACADEMIC_SECTION_FIELD):
		programmes = frappe.get_all(
			"Program",
			filters={ACADEMIC_SECTION_FIELD: ["is", "set"]},
			fields=["name", "department", ACADEMIC_SECTION_FIELD],
		)
		for programme in programmes:
			department = mapping.get(programme.get(ACADEMIC_SECTION_FIELD))
			if department and not programme.department:
				frappe.db.set_value("Program", programme.name, "department", department, update_modified=False)
	frappe.clear_cache(doctype="Department")
	frappe.clear_cache(doctype="Program")


def _exact_owned_department(display_name: str, company: str, institution: str) -> str | None:
	meta = frappe.get_meta("Department")
	if meta.has_field(DISPLAY_FIELD):
		name = frappe.db.get_value(
			"Department",
			{DISPLAY_FIELD: display_name, "company": company, INSTITUTION_FIELD: institution},
			"name",
		)
		if name:
			return name
	return frappe.db.get_value(
		"Department",
		{"department_name": display_name, "company": company, INSTITUTION_FIELD: institution},
		"name",
	)


def _unowned_department(display_name: str, company: str) -> str | None:
	meta = frappe.get_meta("Department")
	if meta.has_field(DISPLAY_FIELD):
		name = frappe.db.get_value(
			"Department",
			{DISPLAY_FIELD: display_name, "company": company, INSTITUTION_FIELD: ["is", "not set"]},
			"name",
		)
		if name:
			return name
	return frappe.db.get_value(
		"Department",
		{"department_name": display_name, "company": company, INSTITUTION_FIELD: ["is", "not set"]},
		"name",
	)


def _normalise(value: str) -> str:
	return " ".join(str(value or "").split()).casefold()
