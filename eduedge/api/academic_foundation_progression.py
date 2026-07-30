from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import academic_foundation_display as display
from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD
from eduedge.education.academic_progression import (
	LEVEL_PROGRESSION,
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_NEXT_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRAM_SEQUENCE_FIELD,
	PROGRAM_TERMINAL_FIELD,
	get_program_progression,
)
from eduedge.platform.access import require_eduedge_access

MAX_ROWS = 1000


@frappe.whitelist()
def get_academic_foundation(institution: str | None = None) -> dict:
	payload = display.get_academic_foundation(institution=institution)
	selected = payload.get("selected_institution")
	programmes = payload.get("programmes") or []
	student_groups = payload.get("student_groups") or []
	_enrich_programmes(programmes)
	_enrich_student_groups(student_groups)
	levels = _levels(selected)
	payload["academic_levels"] = levels
	payload["hierarchy"] = _build_progression_hierarchy(payload.get("departments") or [], programmes, levels, student_groups)
	payload["readiness"] = _extend_readiness(payload.get("readiness") or {}, programmes, levels)
	payload["permissions"]["can_create_academic_level"] = bool(frappe.has_permission("EduEdge Academic Level", "create"))
	payload["permissions"]["can_write_academic_level"] = bool(frappe.has_permission("EduEdge Academic Level", "write"))
	return payload


def _enrich_programmes(programmes: list[dict]) -> None:
	for row in programmes:
		progression = get_program_progression(row.get("name"))
		row[PROGRAM_PROGRESSION_MODE_FIELD] = progression.get(PROGRAM_PROGRESSION_MODE_FIELD) or ""
		row[PROGRAM_SEQUENCE_FIELD] = cint(progression.get(PROGRAM_SEQUENCE_FIELD))
		row[PROGRAM_NEXT_FIELD] = progression.get(PROGRAM_NEXT_FIELD) or ""
		row[PROGRAM_TERMINAL_FIELD] = cint(progression.get(PROGRAM_TERMINAL_FIELD))
		row[PROGRAM_ALLOW_REPETITION_FIELD] = cint(progression.get(PROGRAM_ALLOW_REPETITION_FIELD))


def _enrich_student_groups(groups: list[dict]) -> None:
	names = [row.get("name") for row in groups if row.get("name")]
	if not names or not frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		return
	values = {
		row.name: row.get(ACADEMIC_LEVEL_FIELD)
		for row in frappe.get_all(
			"Student Group",
			filters={"name": ["in", names]},
			fields=["name", ACADEMIC_LEVEL_FIELD],
			page_length=max(len(names), 1),
		)
	}
	for row in groups:
		row[ACADEMIC_LEVEL_FIELD] = values.get(row.get("name")) or ""


def _levels(institution: str | None) -> list[dict]:
	if not institution or not frappe.has_permission("EduEdge Academic Level", "read"):
		return []
	return frappe.get_list(
		"EduEdge Academic Level",
		filters={"institution": institution, "enabled": 1},
		fields=["name", "level_name", "level_code", "institution", "program", "sequence", "next_level", "is_terminal", "enabled"],
		order_by="program asc, sequence asc, level_name asc",
		page_length=MAX_ROWS,
	)


def _build_progression_hierarchy(
	departments: list[dict],
	programmes: list[dict],
	levels: list[dict],
	groups: list[dict],
) -> list[dict]:
	groups_by_program: dict[str, list[dict]] = defaultdict(list)
	groups_by_level: dict[str, list[dict]] = defaultdict(list)
	for group in groups:
		row = dict(group)
		level = row.get(ACADEMIC_LEVEL_FIELD)
		if level:
			groups_by_level[level].append(row)
		else:
			groups_by_program[row.get("program")].append(row)

	levels_by_program: dict[str, list[dict]] = defaultdict(list)
	for level in levels:
		row = dict(level)
		row["student_groups"] = groups_by_level.get(level.get("name"), [])
		levels_by_program[level.get("program")].append(row)

	programmes_by_department: dict[str, list[dict]] = defaultdict(list)
	for programme in programmes:
		row = dict(programme)
		row["academic_levels"] = levels_by_program.get(programme.get("name"), [])
		row["student_groups"] = groups_by_program.get(programme.get("name"), [])
		programmes_by_department[programme.get("department")].append(row)

	children: dict[str | None, list[dict]] = defaultdict(list)
	for department in departments:
		row = dict(department)
		row["programmes"] = sorted(
			programmes_by_department.get(department.get("name"), []),
			key=lambda item: (cint(item.get(PROGRAM_SEQUENCE_FIELD)), str(item.get("display_name") or item.get("program_name") or "")),
		)
		row["children"] = []
		children[department.get("parent_department") or None].append(row)
	by_name = {row["name"]: row for rows in children.values() for row in rows}
	for parent, rows in children.items():
		if parent and parent in by_name:
			by_name[parent]["children"].extend(rows)
	return children.get(None, []) + [row for parent, rows in children.items() if parent and parent not in by_name for row in rows]


def _extend_readiness(readiness: dict, programmes: list[dict], levels: list[dict]) -> dict:
	issues = list(readiness.get("issues") or [])
	levels_by_program: dict[str, list[dict]] = defaultdict(list)
	for row in levels:
		levels_by_program[row.get("program")].append(row)
	missing_levels = [
		row for row in programmes
		if row.get(PROGRAM_PROGRESSION_MODE_FIELD) == LEVEL_PROGRESSION and not levels_by_program.get(row.get("name"))
	]
	if missing_levels:
		issues.append(
			{
				"code": "level_progression_without_levels",
				"severity": "danger",
				"message": _("{0} Level-progression Programme(s) have no Academic Levels configured.").format(len(missing_levels)),
			}
		)
	readiness["issues"] = issues
	readiness["ready"] = not any(row.get("severity") == "danger" for row in issues)
	readiness["academic_level_count"] = len(levels)
	readiness["level_progression_programme_count"] = sum(
		1 for row in programmes if row.get(PROGRAM_PROGRESSION_MODE_FIELD) == LEVEL_PROGRESSION
	)
	return readiness


@frappe.whitelist(methods=["POST"])
def save_academic_level(
	institution: str,
	program: str,
	level_name: str,
	level_code: str,
	academic_level: str | None = None,
	sequence: int | str = 10,
	next_level: str | None = None,
	is_terminal: int | str = 0,
	enabled: int | str = 1,
	description: str | None = None,
) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	require_eduedge_access(feature_key="academics", action="save_academic_level")
	institution_doc = frappe.get_doc("EduEdge Institution", institution)
	institution_doc.check_permission("read")
	program_doc = frappe.get_doc("Program", program)
	program_doc.check_permission("read")
	if program_doc.get(INSTITUTION_FIELD) != institution:
		frappe.throw(_("Programme must belong to the selected Institution."), frappe.ValidationError)
	if academic_level:
		doc = frappe.get_doc("EduEdge Academic Level", academic_level)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Academic Level", "create"):
			frappe.throw(_("You are not permitted to create Academic Levels."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Academic Level")
	doc.update(
		{
			"institution": institution,
			"program": program,
			"level_name": " ".join(str(level_name or "").split()),
			"level_code": str(level_code or "").strip(),
			"sequence": max(cint(sequence), 0),
			"next_level": next_level or None,
			"is_terminal": cint(is_terminal),
			"enabled": cint(enabled),
			"description": description or "",
		}
	)
	doc.save()
	return {"name": doc.name, "level_name": doc.level_name, "level_code": doc.level_code, "program": doc.program}
