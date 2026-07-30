from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import programmes as base
from eduedge.api import programmes_display as display
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_progression import (
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_SEQUENCE_FIELD,
	PROGRAM_TERMINAL_FIELD,
	default_progression_mode,
)
from eduedge.education.native_identity import DISPLAY_FIELD
from eduedge.platform.access import require_eduedge_access


@frappe.whitelist()
def get_programmes_page(**kwargs) -> dict:
	payload = display.get_programmes_page(**kwargs)
	_enrich_programmes(payload)
	return payload


def _enrich_programmes(payload: dict) -> None:
	rows = payload.get("programmes") or []
	names = [row.get("name") for row in rows if row.get("name")]
	fields = [
		"name", PROGRAM_PROGRESSION_MODE_FIELD, PROGRAM_SEQUENCE_FIELD, PROGRAM_NEXT_FIELD,
		PROGRAM_TERMINAL_FIELD, PROGRAM_ALLOW_REPETITION_FIELD,
	]
	values = {
		row.name: row
		for row in frappe.get_all(
			"Program",
			filters={"name": ["in", names]},
			fields=fields,
			page_length=max(len(names), 1),
		)
	} if names else {}
	for row in rows:
		progression = values.get(row.get("name")) or {}
		row[PROGRAM_PROGRESSION_MODE_FIELD] = progression.get(PROGRAM_PROGRESSION_MODE_FIELD) or default_progression_mode(row.get(INSTITUTION_FIELD))
		row[PROGRAM_SEQUENCE_FIELD] = cint(progression.get(PROGRAM_SEQUENCE_FIELD))
		row[PROGRAM_NEXT_FIELD] = progression.get(PROGRAM_NEXT_FIELD) or ""
		row[PROGRAM_TERMINAL_FIELD] = cint(progression.get(PROGRAM_TERMINAL_FIELD))
		row[PROGRAM_ALLOW_REPETITION_FIELD] = cint(progression.get(PROGRAM_ALLOW_REPETITION_FIELD))
	institutions = {row.get("name"): row for row in payload.get("institutions") or []}
	for institution_name, institution in institutions.items():
		institution["default_progression_mode"] = default_progression_mode(institution_name)


@frappe.whitelist(methods=["POST"])
def save_programme(
	program_name: str,
	institution: str,
	department: str,
	programme: str | None = None,
	program_abbreviation: str | None = None,
	progression_mode: str | None = None,
	progression_sequence: int | str = 10,
	next_program: str | None = None,
	terminal_program: int | str = 0,
	allow_repetition: int | str = 1,
	**_legacy_values,
) -> dict:
	base._require_login()
	require_eduedge_access(feature_key="academics", action="save_programme")
	base._assert_institution_access(institution)
	base._assert_department_context(department, institution)
	friendly = " ".join(str(program_name or "").split())
	if not friendly:
		frappe.throw(_("Programme / Class Name is required."), frappe.ValidationError)
	if programme:
		doc = frappe.get_doc("Program", programme)
		doc.check_permission("write")
		doc.set(DISPLAY_FIELD, friendly)
	else:
		if not frappe.has_permission("Program", "create"):
			frappe.throw(_("You are not permitted to create Programmes / Classes."), frappe.PermissionError)
		doc = frappe.new_doc("Program")
		doc.program_name = friendly
		doc.set(DISPLAY_FIELD, friendly)
	doc.program_abbreviation = str(program_abbreviation or "").strip() or None
	doc.department = str(department or "").strip()
	doc.set(INSTITUTION_FIELD, institution)
	if doc.meta.has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		doc.set(PROGRAM_PROGRESSION_MODE_FIELD, progression_mode or default_progression_mode(institution))
		doc.set(PROGRAM_SEQUENCE_FIELD, max(cint(progression_sequence), 0))
		doc.set(PROGRAM_NEXT_FIELD, next_program or None)
		doc.set(PROGRAM_TERMINAL_FIELD, cint(terminal_program))
		doc.set(PROGRAM_ALLOW_REPETITION_FIELD, cint(allow_repetition))
	doc.save()
	return {
		"name": doc.name,
		"program_name": doc.get(DISPLAY_FIELD) or doc.program_name,
		"technical_name": doc.program_name,
		"institution": doc.get(INSTITUTION_FIELD),
		"department": doc.department,
		"progression_mode": doc.get(PROGRAM_PROGRESSION_MODE_FIELD),
		"next_program": doc.get(PROGRAM_NEXT_FIELD),
	}
