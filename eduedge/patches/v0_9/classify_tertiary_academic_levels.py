from __future__ import annotations

from collections import defaultdict

import frappe

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD
from eduedge.education.academic_progression import LEVEL_PROGRESSION, PROGRAM_PROGRESSION_MODE_FIELD

LEVEL_TYPES = {"TERTIARY", "TRAINING_CENTRE"}


def execute() -> None:
	"""Attach legacy Levels to a Programme only where operational history is unambiguous.

	Primary/Secondary legacy Levels remain untouched because their Class master is
	the native Program. Tertiary/Training Levels are attached only when exactly one
	Programme is referenced by existing Offering or Student Group history.
	"""
	if not (
		frappe.db.exists("DocType", "EduEdge Academic Level")
		and frappe.get_meta("EduEdge Academic Level").has_field("program")
	):
		return
	levels = frappe.get_all(
		"EduEdge Academic Level",
		filters={"program": ["is", "not set"]},
		fields=["name", "institution"],
	)
	if not levels:
		return
	institution_types = {
		row.name: str(row.institution_type or "").upper()
		for row in frappe.get_all(
			"EduEdge Institution",
			filters={"name": ["in", list({row.institution for row in levels if row.institution})]},
			fields=["name", "institution_type"],
			page_length=max(len(levels), 1),
		)
	}
	candidates = _candidate_programmes([row.name for row in levels])
	for level in levels:
		if institution_types.get(level.institution) not in LEVEL_TYPES:
			continue
		programmes = candidates.get(level.name, set())
		if len(programmes) != 1:
			continue
		program = next(iter(programmes))
		program_institution = frappe.db.get_value("Program", program, INSTITUTION_FIELD)
		if program_institution != level.institution:
			continue
		frappe.db.set_value("EduEdge Academic Level", level.name, "program", program, update_modified=False)
		if frappe.get_meta("Program").has_field(PROGRAM_PROGRESSION_MODE_FIELD):
			frappe.db.set_value("Program", program, PROGRAM_PROGRESSION_MODE_FIELD, LEVEL_PROGRESSION, update_modified=False)
	frappe.clear_cache(doctype="EduEdge Academic Level")
	frappe.clear_cache(doctype="Program")


def _candidate_programmes(level_names: list[str]) -> dict[str, set[str]]:
	candidates: dict[str, set[str]] = defaultdict(set)
	if frappe.db.exists("DocType", "EduEdge Program Offering"):
		for row in frappe.get_all(
			"EduEdge Program Offering",
			filters={"academic_level": ["in", level_names]},
			fields=["academic_level", "program"],
			page_length=0,
		):
			if row.academic_level and row.program:
				candidates[row.academic_level].add(row.program)
	if frappe.db.exists("DocType", "Student Group") and frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		for row in frappe.get_all(
			"Student Group",
			filters={ACADEMIC_LEVEL_FIELD: ["in", level_names]},
			fields=[ACADEMIC_LEVEL_FIELD, "program"],
			page_length=0,
		):
			level = row.get(ACADEMIC_LEVEL_FIELD)
			if level and row.program:
				candidates[level].add(row.program)
	return candidates
