from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD

PROGRESSION_LEVEL_FIELD = "eduedge_progression_level"
PROGRAM_PROGRESSION_MODE_FIELD = "eduedge_progression_mode"
PROGRAM_SEQUENCE_FIELD = "eduedge_progression_sequence"
PROGRAM_NEXT_FIELD = "eduedge_next_program"
PROGRAM_TERMINAL_FIELD = "eduedge_terminal_program"
PROGRAM_ALLOW_REPETITION_FIELD = "eduedge_allow_repetition"

PROGRAM_PROMOTION = "Program Promotion"
LEVEL_PROGRESSION = "Level Progression"
MANUAL_PROGRESSION = "Manual Progression"

PROGRAM_PROMOTION_TYPES = {"PRIMARY", "SECONDARY"}
LEVEL_PROGRESSION_TYPES = {"TERTIARY", "TRAINING_CENTRE"}


PROGRESSION_CUSTOM_FIELDS = {
	"Program": [
		{
			"fieldname": "eduedge_progression_section",
			"fieldtype": "Section Break",
			"label": "Academic Progression",
			"insert_after": INSTITUTION_FIELD,
			"collapsible": 1,
		},
		{
			"fieldname": PROGRAM_PROGRESSION_MODE_FIELD,
			"fieldtype": "Select",
			"label": "Progression Mode",
			"options": f"{PROGRAM_PROMOTION}\n{LEVEL_PROGRESSION}\n{MANUAL_PROGRESSION}",
			"in_standard_filter": 1,
			"description": "Primary/Secondary Classes normally progress to another Class. Tertiary/Training Programmes normally progress through Academic Levels.",
		},
		{
			"fieldname": PROGRAM_SEQUENCE_FIELD,
			"fieldtype": "Int",
			"label": "Progression Sequence",
			"default": 10,
		},
		{
			"fieldname": "eduedge_progression_column",
			"fieldtype": "Column Break",
		},
		{
			"fieldname": PROGRAM_NEXT_FIELD,
			"fieldtype": "Link",
			"label": "Next Program / Class",
			"options": "Program",
			"depends_on": f"eval:doc.{PROGRAM_PROGRESSION_MODE_FIELD}=='{PROGRAM_PROMOTION}' && !doc.{PROGRAM_TERMINAL_FIELD}",
			"description": "Configured next Class for the following Academic Session. It must belong to the same Institution.",
		},
		{
			"fieldname": PROGRAM_TERMINAL_FIELD,
			"fieldtype": "Check",
			"label": "Terminal Program / Class",
			"default": 0,
		},
		{
			"fieldname": PROGRAM_ALLOW_REPETITION_FIELD,
			"fieldtype": "Check",
			"label": "Allow Repetition",
			"default": 1,
		},
	],
	"Program Enrollment": [
		{
			"fieldname": PROGRESSION_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Progression Academic Level",
			"options": "EduEdge Academic Level",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Required for Level-progression Programmes such as tertiary or structured training programmes. New admissions default to the first configured Level when left blank.",
		},
	],
	"Student Group": [
		{
			"fieldname": PROGRESSION_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Progression Academic Level",
			"options": "EduEdge Academic Level",
			"in_standard_filter": 1,
			"description": "Optional Level identity for tertiary/training lecture groups. Primary/Secondary Class Arms normally leave this blank.",
		},
	],
}


def ensure_academic_progression_foundation() -> None:
	available = {
		doctype: fields
		for doctype, fields in PROGRESSION_CUSTOM_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}
	if available:
		create_custom_fields(available, update=True)
	_backfill_program_progression_modes()
	for doctype in available:
		frappe.clear_cache(doctype=doctype)


def _institution_type(institution: str | None) -> str:
	if not institution:
		return ""
	return str(frappe.db.get_value("EduEdge Institution", institution, "institution_type") or "").strip().upper()


def default_progression_mode(institution: str | None) -> str:
	type_code = _institution_type(institution)
	if type_code in PROGRAM_PROMOTION_TYPES:
		return PROGRAM_PROMOTION
	if type_code in LEVEL_PROGRESSION_TYPES:
		return LEVEL_PROGRESSION
	return MANUAL_PROGRESSION


def _backfill_program_progression_modes() -> None:
	if not frappe.db.exists("DocType", "Program"):
		return
	meta = frappe.get_meta("Program")
	if not meta.has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		return
	rows = frappe.get_all("Program", fields=["name", INSTITUTION_FIELD, PROGRAM_PROGRESSION_MODE_FIELD])
	for row in rows:
		if row.get(PROGRAM_PROGRESSION_MODE_FIELD) or not row.get(INSTITUTION_FIELD):
			continue
		frappe.db.set_value(
			"Program",
			row.name,
			PROGRAM_PROGRESSION_MODE_FIELD,
			default_progression_mode(row.get(INSTITUTION_FIELD)),
			update_modified=False,
		)


def get_program_progression(program: str | None) -> frappe._dict:
	if not program:
		return frappe._dict()
	meta = frappe.get_meta("Program")
	fields = ["name", "department", INSTITUTION_FIELD]
	for fieldname in (
		PROGRAM_PROGRESSION_MODE_FIELD,
		PROGRAM_SEQUENCE_FIELD,
		PROGRAM_NEXT_FIELD,
		PROGRAM_TERMINAL_FIELD,
		PROGRAM_ALLOW_REPETITION_FIELD,
	):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	row = frappe.db.get_value("Program", program, fields, as_dict=True) or frappe._dict()
	if row and not row.get(PROGRAM_PROGRESSION_MODE_FIELD):
		row[PROGRAM_PROGRESSION_MODE_FIELD] = default_progression_mode(row.get(INSTITUTION_FIELD))
	return row


def validate_program_progression(doc) -> None:
	if not doc.meta.has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		return
	institution = doc.get(INSTITUTION_FIELD)
	mode = doc.get(PROGRAM_PROGRESSION_MODE_FIELD) or default_progression_mode(institution)
	doc.set(PROGRAM_PROGRESSION_MODE_FIELD, mode)
	type_code = _institution_type(institution)

	if type_code in PROGRAM_PROMOTION_TYPES and mode == LEVEL_PROGRESSION:
		frappe.throw(_("Primary and Secondary Classes cannot use Level Progression."), frappe.ValidationError)
	if type_code in LEVEL_PROGRESSION_TYPES and mode == PROGRAM_PROMOTION:
		frappe.throw(_("Tertiary and Training Programmes progress through Academic Levels, not another Program."), frappe.ValidationError)

	next_program = doc.get(PROGRAM_NEXT_FIELD)
	terminal = cint(doc.get(PROGRAM_TERMINAL_FIELD))
	if terminal and next_program:
		frappe.throw(_("A terminal Program / Class cannot have a Next Program / Class."), frappe.ValidationError)
	if mode != PROGRAM_PROMOTION and next_program:
		frappe.throw(_("Next Program / Class is only valid for Program Promotion."), frappe.ValidationError)
	if next_program:
		if next_program == doc.name:
			frappe.throw(_("Next Program / Class cannot be the same record."), frappe.ValidationError)
		target = get_program_progression(next_program)
		if not target:
			frappe.throw(_("Select a valid Next Program / Class."), frappe.ValidationError)
		if target.get(INSTITUTION_FIELD) != institution:
			frappe.throw(_("Next Program / Class must belong to the same Institution."), frappe.ValidationError)
		_validate_program_cycle(doc.name, next_program)


def _validate_program_cycle(program: str | None, next_program: str) -> None:
	visited = {program} if program else set()
	current = next_program
	while current:
		if current in visited:
			frappe.throw(_("Program / Class progression cannot contain a cycle."), frappe.ValidationError)
		visited.add(current)
		current = frappe.db.get_value("Program", current, PROGRAM_NEXT_FIELD)


def validate_level_for_program(
	level: str | None,
	*,
	program: str | None,
	institution: str | None,
	required: bool = False,
) -> frappe._dict | None:
	if not level:
		if required:
			frappe.throw(_("Academic Level is required for this Programme."), frappe.ValidationError)
		return None
	row = frappe.db.get_value(
		"EduEdge Academic Level",
		level,
		["name", "level_name", "level_code", "institution", "program", "sequence", "next_level", "is_terminal", "enabled"],
		as_dict=True,
	)
	if not row or not cint(row.enabled):
		frappe.throw(_("Select an enabled Academic Level."), frappe.ValidationError)
	if institution and row.institution != institution:
		frappe.throw(_("Academic Level must belong to the selected Institution."), frappe.ValidationError)
	if program and row.program != program:
		frappe.throw(_("Academic Level must belong to the selected Programme."), frappe.ValidationError)
	return row


def initial_progression_level(program: str, institution: str | None) -> frappe._dict:
	rows = frappe.get_all(
		"EduEdge Academic Level",
		filters={"program": program, "institution": institution, "enabled": 1},
		fields=["name", "level_name", "level_code", "institution", "program", "sequence", "next_level", "is_terminal", "enabled"],
		order_by="sequence asc, level_name asc",
		limit_page_length=2,
	)
	if not rows:
		frappe.throw(
			_("Configure at least one enabled Academic Level for this Level-progression Programme before enrolling Students."),
			frappe.ValidationError,
		)
	return rows[0]


def progression_target(source_program: str, source_level: str | None = None) -> dict:
	program = get_program_progression(source_program)
	mode = program.get(PROGRAM_PROGRESSION_MODE_FIELD)
	if mode == PROGRAM_PROMOTION:
		if cint(program.get(PROGRAM_TERMINAL_FIELD)):
			return {"mode": mode, "terminal": True, "program": None, "progression_level": None}
		return {
			"mode": mode,
			"terminal": False,
			"program": program.get(PROGRAM_NEXT_FIELD),
			"progression_level": None,
		}
	if mode == LEVEL_PROGRESSION:
		level = validate_level_for_program(
			source_level,
			program=source_program,
			institution=program.get(INSTITUTION_FIELD),
			required=True,
		)
		if cint(level.is_terminal):
			return {"mode": mode, "terminal": True, "program": source_program, "progression_level": None}
		if not level.next_level:
			return {"mode": mode, "terminal": False, "program": None, "progression_level": None, "configuration_missing": True}
		return {
			"mode": mode,
			"terminal": False,
			"program": source_program,
			"progression_level": level.next_level,
		}
	return {"mode": mode, "terminal": False, "program": None, "progression_level": None}


def validate_progression_level_on_enrollment(doc) -> None:
	if not doc.meta.has_field(PROGRESSION_LEVEL_FIELD):
		return
	program = get_program_progression(doc.program)
	mode = program.get(PROGRAM_PROGRESSION_MODE_FIELD)
	level = doc.get(PROGRESSION_LEVEL_FIELD)
	if mode == LEVEL_PROGRESSION:
		if not level:
			level = initial_progression_level(doc.program, program.get(INSTITUTION_FIELD)).name
			doc.set(PROGRESSION_LEVEL_FIELD, level)
		validate_level_for_program(level, program=doc.program, institution=program.get(INSTITUTION_FIELD), required=True)
	elif level:
		frappe.throw(_("Academic Level is only valid for a Level-progression Programme."), frappe.ValidationError)


def validate_progression_level_on_student_group(doc) -> None:
	if not doc.meta.has_field(PROGRESSION_LEVEL_FIELD) or not doc.get(PROGRESSION_LEVEL_FIELD):
		return
	program = get_program_progression(doc.program)
	if program.get(PROGRAM_PROGRESSION_MODE_FIELD) != LEVEL_PROGRESSION:
		frappe.throw(_("Academic Level is only valid for a Level-progression Programme."), frappe.ValidationError)
	validate_level_for_program(
		doc.get(PROGRESSION_LEVEL_FIELD),
		program=doc.program,
		institution=program.get(INSTITUTION_FIELD),
		required=True,
	)
