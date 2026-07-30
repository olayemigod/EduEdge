from __future__ import annotations

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint, flt

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD, OFFERING_FIELD

PROGRAM_PROGRESSION_MODE_FIELD = "eduedge_progression_mode"
PROGRAM_SEQUENCE_FIELD = "eduedge_progression_sequence"
PROGRAM_NEXT_FIELD = "eduedge_next_program"
PROGRAM_TERMINAL_FIELD = "eduedge_terminal_program"
PROGRAM_ALLOW_REPETITION_FIELD = "eduedge_allow_repetition"

PROGRAM_COURSE_PERIOD_FIELD = "eduedge_period_number"
PROGRAM_COURSE_TYPE_FIELD = "eduedge_course_type"
PROGRAM_COURSE_CREDIT_FIELD = "eduedge_credit_units"

PROGRAM_PROMOTION = "Program Promotion"
LEVEL_PROGRESSION = "Level Progression"
NO_AUTOMATIC_PROGRESSION = "No Automatic Progression"

PROGRAM_PROMOTION_TYPES = {"PRIMARY", "SECONDARY"}
LEVEL_PROGRESSION_TYPES = {"TERTIARY", "TRAINING_CENTRE"}


def _level_field(*, read_only: bool, insert_after: str | None = None) -> dict:
	field = {
		"fieldname": ACADEMIC_LEVEL_FIELD,
		"fieldtype": "Link",
		"label": "Academic Level",
		"options": "EduEdge Academic Level",
		"read_only": cint(read_only),
		"hidden": 0,
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": "Required only where the selected Programme uses structured Level progression.",
	}
	if insert_after:
		field["insert_after"] = insert_after
	return field


ACADEMIC_PROGRESSION_CUSTOM_FIELDS = {
	"Program": [
		{
			"fieldname": "eduedge_progression_section",
			"fieldtype": "Section Break",
			"label": "Academic Progression",
			"insert_after": "program_abbreviation",
			"collapsible": 1,
		},
		{
			"fieldname": PROGRAM_PROGRESSION_MODE_FIELD,
			"fieldtype": "Select",
			"label": "Progression Mode",
			"options": f"{PROGRAM_PROMOTION}\n{LEVEL_PROGRESSION}\n{NO_AUTOMATIC_PROGRESSION}",
			"default": NO_AUTOMATIC_PROGRESSION,
			"in_standard_filter": 1,
			"description": "Primary/Secondary Classes progress to another Program. Tertiary/Training Programmes progress through Academic Levels.",
		},
		{
			"fieldname": PROGRAM_SEQUENCE_FIELD,
			"fieldtype": "Int",
			"label": "Progression Sequence",
			"default": 10,
			"description": "Display and review order for Classes or Programmes. The explicit Next Program or Next Level remains authoritative.",
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
			"description": "The next Class used by the promotion workflow. It must belong to the same Institution.",
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
	"Program Course": [
		{
			"fieldname": ACADEMIC_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Academic Level",
			"options": "EduEdge Academic Level",
			"in_list_view": 1,
			"description": "Optional for Primary/Secondary. For tertiary curricula, identifies the Level where this Course is offered.",
		},
		{
			"fieldname": PROGRAM_COURSE_PERIOD_FIELD,
			"fieldtype": "Int",
			"label": "Curriculum Period No.",
			"default": 0,
			"in_list_view": 1,
			"description": "Zero means year-wide or not classified. Otherwise use Term/Semester sequence such as 1 or 2.",
		},
		{
			"fieldname": PROGRAM_COURSE_TYPE_FIELD,
			"fieldtype": "Select",
			"label": "Course Type",
			"options": "Core\nElective\nOptional",
			"default": "Core",
			"in_list_view": 1,
		},
		{
			"fieldname": PROGRAM_COURSE_CREDIT_FIELD,
			"fieldtype": "Float",
			"label": "Credit Units",
			"default": 0,
			"in_list_view": 1,
		},
	],
	"Student Applicant": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Program Enrollment": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Student Group": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Fee Structure": [_level_field(read_only=False, insert_after=OFFERING_FIELD)],
	"Fee Schedule": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Fees": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Assessment Plan": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Assessment Result": [_level_field(read_only=True, insert_after=OFFERING_FIELD)],
	"Course Schedule": [_level_field(read_only=True, insert_after="student_group")],
}


def ensure_academic_progression_foundation() -> None:
	available = {
		doctype: fields
		for doctype, fields in ACADEMIC_PROGRESSION_CUSTOM_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}
	if available:
		create_custom_fields(available, update=True)
	_backfill_program_progression_modes()
	for doctype in available:
		frappe.clear_cache(doctype=doctype)


def _backfill_program_progression_modes() -> None:
	if not frappe.db.exists("DocType", "Program") or not frappe.get_meta("Program").has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		return
	rows = frappe.get_all("Program", fields=["name", INSTITUTION_FIELD, PROGRAM_PROGRESSION_MODE_FIELD])
	for row in rows:
		if row.get(PROGRAM_PROGRESSION_MODE_FIELD) or not row.get(INSTITUTION_FIELD):
			continue
		mode = default_progression_mode(row.get(INSTITUTION_FIELD))
		frappe.db.set_value("Program", row.name, PROGRAM_PROGRESSION_MODE_FIELD, mode, update_modified=False)


def institution_type(institution: str | None) -> str:
	return str(frappe.db.get_value("EduEdge Institution", institution, "institution_type") or "").strip().upper() if institution else ""


def default_progression_mode(institution: str | None) -> str:
	type_code = institution_type(institution)
	if type_code in PROGRAM_PROMOTION_TYPES:
		return PROGRAM_PROMOTION
	if type_code in LEVEL_PROGRESSION_TYPES:
		return LEVEL_PROGRESSION
	return NO_AUTOMATIC_PROGRESSION


def get_program_progression(program: str | None) -> frappe._dict:
	if not program:
		return frappe._dict()
	fields = ["name", "department", INSTITUTION_FIELD]
	meta = frappe.get_meta("Program")
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
	type_code = institution_type(institution)
	mode = doc.get(PROGRAM_PROGRESSION_MODE_FIELD) or default_progression_mode(institution)
	doc.set(PROGRAM_PROGRESSION_MODE_FIELD, mode)

	if type_code in PROGRAM_PROMOTION_TYPES and mode not in {PROGRAM_PROMOTION, NO_AUTOMATIC_PROGRESSION}:
		frappe.throw(_("Primary and Secondary Classes must use Program Promotion or No Automatic Progression."), frappe.ValidationError)
	if type_code in LEVEL_PROGRESSION_TYPES and mode == PROGRAM_PROMOTION:
		frappe.throw(_("Tertiary and Training Programmes progress through Academic Levels, not through another Program."), frappe.ValidationError)

	next_program = doc.get(PROGRAM_NEXT_FIELD)
	terminal = cint(doc.get(PROGRAM_TERMINAL_FIELD))
	if terminal and next_program:
		frappe.throw(_("A terminal Program / Class cannot have a Next Program."), frappe.ValidationError)
	if mode != PROGRAM_PROMOTION and next_program:
		frappe.throw(_("Next Program / Class is only valid when Progression Mode is Program Promotion."), frappe.ValidationError)
	if next_program:
		if next_program == doc.name:
			frappe.throw(_("Next Program / Class cannot be the same record."), frappe.ValidationError)
		target = get_program_progression(next_program)
		if not target:
			frappe.throw(_("Select a valid Next Program / Class."), frappe.ValidationError)
		if target.get(INSTITUTION_FIELD) != institution:
			frappe.throw(_("Next Program / Class must belong to the same Institution."), frappe.ValidationError)
		_validate_program_cycle(doc.name, next_program)

	_validate_program_courses(doc, mode, institution)


def _validate_program_cycle(program: str | None, next_program: str) -> None:
	visited = {program} if program else set()
	current = next_program
	while current:
		if current in visited:
			frappe.throw(_("Program / Class progression cannot contain a cycle."), frappe.ValidationError)
		visited.add(current)
		current = frappe.db.get_value("Program", current, PROGRAM_NEXT_FIELD)


def _validate_program_courses(doc, mode: str, institution: str | None) -> None:
	for row in doc.get("courses") or []:
		level = row.get(ACADEMIC_LEVEL_FIELD)
		if level:
			if mode != LEVEL_PROGRESSION:
				frappe.throw(_("Academic Level on Program Course is only valid for a Level-progression Programme."), frappe.ValidationError)
			validate_level_for_program(level, program=doc.name, institution=institution, required=True)
		if cint(row.get(PROGRAM_COURSE_PERIOD_FIELD)) < 0:
			frappe.throw(_("Curriculum Period No. cannot be negative."), frappe.ValidationError)
		if flt(row.get(PROGRAM_COURSE_CREDIT_FIELD)) < 0:
			frappe.throw(_("Credit Units cannot be negative."), frappe.ValidationError)


def validate_level_for_program(
	level: str | None,
	*,
	program: str | None,
	institution: str | None,
	required: bool = False,
) -> frappe._dict | None:
	if not level:
		if required:
			frappe.throw(_("Academic Level is required for the selected Programme."), frappe.ValidationError)
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


def requires_academic_level(program: str | None) -> bool:
	return get_program_progression(program).get(PROGRAM_PROGRESSION_MODE_FIELD) == LEVEL_PROGRESSION


def progression_target(source_program: str, source_level: str | None = None) -> dict:
	program = get_program_progression(source_program)
	mode = program.get(PROGRAM_PROGRESSION_MODE_FIELD)
	if mode == PROGRAM_PROMOTION:
		return {"mode": mode, "program": program.get(PROGRAM_NEXT_FIELD), "academic_level": None}
	if mode == LEVEL_PROGRESSION:
		level = validate_level_for_program(source_level, program=source_program, institution=program.get(INSTITUTION_FIELD), required=True)
		return {"mode": mode, "program": source_program, "academic_level": level.next_level if level else None}
	return {"mode": mode, "program": None, "academic_level": None}


def programme_course_filters(program: str, academic_level: str | None = None, period_number: int | None = None) -> dict:
	filters: dict = {"parent": program, "parenttype": "Program"}
	meta = frappe.get_meta("Program Course")
	if academic_level and meta.has_field(ACADEMIC_LEVEL_FIELD):
		filters[ACADEMIC_LEVEL_FIELD] = ["in", ["", academic_level]]
	if period_number and meta.has_field(PROGRAM_COURSE_PERIOD_FIELD):
		filters[PROGRAM_COURSE_PERIOD_FIELD] = ["in", [0, cint(period_number)]]
	return filters
