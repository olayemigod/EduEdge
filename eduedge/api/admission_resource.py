from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import resource_center as base
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import validate_program_offering
from eduedge.services.branch_context import get_allowed_school_branches

PROGRAMS_FIELD = "admission_programs"


def _normalize_list(value: Any) -> list[str]:
	if value in (None, ""):
		return []
	if isinstance(value, str):
		try:
			parsed = frappe.parse_json(value)
		except Exception:
			parsed = [item.strip() for item in value.split(",")]
		value = parsed
	if not isinstance(value, (list, tuple, set)):
		value = [value]
	result: list[str] = []
	for item in value:
		resolved = str(item or "").strip()
		if resolved and resolved not in result:
			result.append(resolved)
	return result


def _assert_branch_access(branch: str | None) -> None:
	if not branch:
		return
	allowed = {row.get("name") for row in get_allowed_school_branches() if row.get("name")}
	if branch not in allowed:
		frappe.throw(
			_("You are not permitted to manage admissions for School Branch / Campus {0}.").format(
				branch
			),
			frappe.PermissionError,
		)


def _assert_program_option_permission() -> None:
	admission_allowed = any(
		frappe.has_permission("Student Admission", permission_type)
		for permission_type in ("read", "create", "write")
	)
	offering_allowed = frappe.has_permission("EduEdge Program Offering", "read")
	if admission_allowed and offering_allowed:
		return
	frappe.throw(
		_("You are not permitted to view admission programme options."),
		frappe.PermissionError,
	)


def get_program_options(
	*,
	branch: str | None,
	academic_year: str | None,
	txt: str = "",
) -> list[dict]:
	if not branch or not academic_year:
		return []
	_assert_program_option_permission()
	_assert_branch_access(branch)
	if not frappe.db.exists("DocType", "EduEdge Program Offering"):
		return []

	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters={
			"school_branch": branch,
			"academic_year": academic_year,
			"is_active": 1,
			"admission_enabled": 1,
		},
		fields=["program", "modified"],
		order_by="modified desc",
		limit_page_length=base.MAX_OPTIONS * 4,
	)
	programs: list[str] = []
	for row in rows:
		program = str(row.get("program") or "").strip()
		if program and program not in programs:
			programs.append(program)

	needle = str(txt or "").strip().lower()
	result: list[dict] = []
	for program in programs:
		label = frappe.db.get_value("Program", program, "program_name") or program
		if needle and needle not in program.lower() and needle not in str(label).lower():
			continue
		result.append(
			{
				"value": program,
				"label": label,
				"description": program if label != program else "",
			}
		)
		if len(result) >= base.MAX_OPTIONS:
			break
	return result


def _with_refresh(field: dict) -> dict:
	field = dict(field)
	clear_fields = list(field.get("clear_fields") or [])
	refresh_fields = list(field.get("refresh_fields") or [])
	if PROGRAMS_FIELD not in clear_fields:
		clear_fields.append(PROGRAMS_FIELD)
	if PROGRAMS_FIELD not in refresh_fields:
		refresh_fields.append(PROGRAMS_FIELD)
	field["clear_fields"] = clear_fields
	field["refresh_fields"] = refresh_fields
	return field


def enrich_editor(result: dict, *, name: str | None = None) -> dict:
	values = dict(result.get("values") or {})
	if name:
		doc = frappe.get_doc("Student Admission", name)
		values[PROGRAMS_FIELD] = [
			row.program for row in (doc.get("program_details") or []) if row.program
		]
	else:
		values[PROGRAMS_FIELD] = []

	fields: list[dict] = []
	inserted = False
	for source in result.get("fields") or []:
		field = dict(source)
		if field.get("fieldname") in {"academic_year", BRANCH_FIELD}:
			field = _with_refresh(field)
		if field.get("fieldname") in {"admission_start_date", "admission_end_date"}:
			field["required_when"] = {
				"field": "enable_admission_application",
				"equals": 1,
			}
		fields.append(field)
		if field.get("fieldname") == BRANCH_FIELD:
			fields.append(
				{
					"fieldname": PROGRAMS_FIELD,
					"label": _("Programmes Accepting Applications"),
					"type": "MultiSelect",
					"required_when": {
						"field": "enable_admission_application",
						"equals": 1,
					},
					"options": get_program_options(
						branch=values.get(BRANCH_FIELD),
						academic_year=values.get("academic_year"),
					),
					"description": _(
						"Only active, admission-enabled Programme Offerings for the selected campus and academic year are shown."
					),
					"empty_message": _(
						"Select a campus and academic year, then configure an admission-enabled Programme Offering if no programme appears."
					),
				}
			)
			inserted = True
	if not inserted:
		fields.append(
			{
				"fieldname": PROGRAMS_FIELD,
				"label": _("Programmes Accepting Applications"),
				"type": "MultiSelect",
				"options": [],
			}
		)

	result["fields"] = fields
	result["values"] = values
	result["advanced_note"] = _(
		"Each admission belongs to one branch/campus. Users with access to several campuses may create separate admission records for each permitted campus. Use a branch-specific title when creating the same admission cycle for more than one campus."
	)
	return result


def search_program_options(values: str | dict | None = None, txt: str = "") -> list[dict]:
	parsed = base._parse_json(values)
	return get_program_options(
		branch=parsed.get(BRANCH_FIELD),
		academic_year=parsed.get("academic_year"),
		txt=txt,
	)


def save_admission(values: str | dict, name: str | None = None) -> dict:
	config = base._config("admissions")
	payload = base._parse_json(values)
	programs_supplied = PROGRAMS_FIELD in payload
	programs = _normalize_list(payload.pop(PROGRAMS_FIELD, []))
	allowed_fields = base._field_map(config)
	clean_values = {
		fieldname: base._coerce(allowed_fields[fieldname], value)
		for fieldname, value in payload.items()
		if fieldname in allowed_fields
	}
	base._validate_branch_value(config, clean_values)

	if name:
		doc = frappe.get_doc("Student Admission", name)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("Student Admission", "create"):
			frappe.throw(
				_("You are not permitted to create Student Admission."),
				frappe.PermissionError,
			)
		doc = frappe.new_doc("Student Admission")

	if cint(doc.docstatus) == 1:
		frappe.throw(
			_("Submitted records cannot be changed from the quick editor."),
			frappe.ValidationError,
		)

	doc.update(clean_values)
	branch = doc.get(BRANCH_FIELD)
	academic_year = doc.get("academic_year")
	_assert_branch_access(branch)

	if programs_supplied:
		doc.set("program_details", [])
		for program in programs:
			validate_program_offering(
				branch=branch,
				program=program,
				academic_year=academic_year,
				purpose="admission",
			)
			doc.append("program_details", {"program": program})

	if cint(doc.get("enable_admission_application")) and not doc.get("program_details"):
		frappe.throw(
			_(
				"Select at least one admission-enabled programme for this campus and academic year before enabling applications."
			),
			frappe.ValidationError,
		)

	if not name and doc.get("title") and frappe.db.exists("Student Admission", doc.get("title")):
		frappe.throw(
			_(
				"Student Admission title {0} already exists. Use a branch-specific title, for example {0} - Campus Name."
			).format(doc.get("title")),
			frappe.DuplicateEntryError,
		)

	if name:
		doc.save()
	else:
		doc.insert()

	return {
		"resource": "admissions",
		"doctype": "Student Admission",
		"name": doc.name,
		"programs": [row.program for row in (doc.get("program_details") or []) if row.program],
		"full_form_route": base._full_form_route(config, doc.name),
	}
