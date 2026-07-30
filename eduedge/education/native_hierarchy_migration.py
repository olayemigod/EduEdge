from __future__ import annotations

from collections import defaultdict
import re

import frappe

from eduedge.education import academic_fields
from eduedge.education.academic_fields import ACADEMIC_SECTION_FIELD, INSTITUTION_FIELD


def ensure_native_academic_context_foundation() -> None:
	"""Run the normal foundation installer with a collision-safe Section backfill.

	The temporary replacement keeps the canonical installer as the single schema and
	terminology entrypoint while preventing same-name Departments in a shared Company
	from being claimed by the wrong Institution.
	"""
	original = academic_fields.backfill_legacy_sections_to_departments
	academic_fields.backfill_legacy_sections_to_departments = backfill_legacy_sections_to_departments
	try:
		academic_fields.ensure_academic_context_foundation()
	finally:
		academic_fields.backfill_legacy_sections_to_departments = original


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
				frappe.db.set_value("Department", unowned, INSTITUTION_FIELD, section.institution, update_modified=False)
				department = unowned
		if not department:
			department_name = _available_department_name(
				section.section_name,
				institution.institution_code or section.institution,
				institution.company,
			)
			doc = frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": department_name,
					"company": institution.company,
					"is_group": 1,
					INSTITUTION_FIELD: section.institution,
				}
			)
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


def _exact_owned_department(department_name: str, company: str, institution: str) -> str | None:
	return frappe.db.get_value(
		"Department",
		{"department_name": department_name, "company": company, INSTITUTION_FIELD: institution},
		"name",
	)


def _unowned_department(department_name: str, company: str) -> str | None:
	return frappe.db.get_value(
		"Department",
		{"department_name": department_name, "company": company, INSTITUTION_FIELD: ["is", "not set"]},
		"name",
	)


def _available_department_name(base_name: str, institution_code: str, company: str) -> str:
	base_name = str(base_name or "").strip()
	code = re.sub(r"[^A-Za-z0-9]+", "-", str(institution_code or "").strip()).strip("-") or "Institution"
	candidate = base_name
	counter = 1
	while frappe.db.exists("Department", {"department_name": candidate, "company": company}):
		suffix = f" ({code})" if counter == 1 else f" ({code}-{counter})"
		candidate = f"{base_name}{suffix}"
		counter += 1
	return candidate


def _normalise(value: str) -> str:
	return " ".join(str(value or "").split()).casefold()
