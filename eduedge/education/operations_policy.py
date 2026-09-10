from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.institution_types import DEFAULT_INSTITUTION_TYPE, normalize_institution_type_code


APPROVAL_MODES = ("Recommended", "Simple", "Standard")
MAX_BULK_QUESTIONS = 100
COMPANY_SETTINGS_DOCTYPE = "EduEdge Company Operations Settings"

QUESTION_GOVERNANCE_FIELDS = (
	"question_approval_mode",
	"allow_bulk_question_approval",
	"max_bulk_question_approval",
	"require_separate_question_approver",
	"allow_academic_admin_override",
)

QUESTION_GOVERNANCE_PRESETS: dict[str, dict[str, Any]] = {
	"PRIMARY": {
		"question_approval_mode": "Simple",
		"allow_bulk_question_approval": 1,
		"max_bulk_question_approval": 100,
		"require_separate_question_approver": 1,
		"allow_academic_admin_override": 1,
	},
	"SECONDARY": {
		"question_approval_mode": "Standard",
		"allow_bulk_question_approval": 1,
		"max_bulk_question_approval": 100,
		"require_separate_question_approver": 1,
		"allow_academic_admin_override": 1,
	},
	"TERTIARY": {
		"question_approval_mode": "Standard",
		"allow_bulk_question_approval": 1,
		"max_bulk_question_approval": 100,
		"require_separate_question_approver": 1,
		"allow_academic_admin_override": 1,
	},
	"TRAINING_CENTRE": {
		"question_approval_mode": "Simple",
		"allow_bulk_question_approval": 1,
		"max_bulk_question_approval": 100,
		"require_separate_question_approver": 1,
		"allow_academic_admin_override": 1,
	},
}


def recommended_question_governance(institution_type: str | None) -> dict[str, Any]:
	code = normalize_institution_type_code(institution_type) or DEFAULT_INSTITUTION_TYPE
	return deepcopy(QUESTION_GOVERNANCE_PRESETS.get(code) or QUESTION_GOVERNANCE_PRESETS[DEFAULT_INSTITUTION_TYPE])


def resolve_company_question_governance(company: str) -> dict[str, Any]:
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Select a valid Company."), frappe.ValidationError)
	institution_type = _company_institution_type(company)
	configuration, settings_name = _company_configuration(company)
	return _resolve_configuration(
		configuration,
		institution_type=institution_type,
		source="Company Default" if settings_name else "Recommended Default",
		company=company,
		institution=None,
		settings_name=settings_name,
		inherits_company=False,
	)


def resolve_question_governance(institution: str) -> dict[str, Any]:
	row = frappe.db.get_value(
		"EduEdge Institution",
		institution,
		[
			"name",
			"company",
			"institution_type",
			"use_company_question_governance_defaults",
			*QUESTION_GOVERNANCE_FIELDS,
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Select a valid EduEdge Institution."), frappe.ValidationError)

	inherits_company = bool(cint(row.get("use_company_question_governance_defaults")))
	if inherits_company:
		configuration, settings_name = _company_configuration(row.company)
		source = "Company Default" if settings_name else "Recommended Default"
	else:
		configuration = {fieldname: row.get(fieldname) for fieldname in QUESTION_GOVERNANCE_FIELDS}
		settings_name = None
		source = "Institution Preference"

	return _resolve_configuration(
		configuration,
		institution_type=row.institution_type,
		source=source,
		company=row.company,
		institution=row.name,
		settings_name=settings_name,
		inherits_company=inherits_company,
	)


def _company_configuration(company: str) -> tuple[dict[str, Any] | None, str | None]:
	if not frappe.db.exists("DocType", COMPANY_SETTINGS_DOCTYPE):
		return None, None
	settings_name = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, {"company": company}, "name")
	if not settings_name:
		return None, None
	values = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, settings_name, list(QUESTION_GOVERNANCE_FIELDS), as_dict=True)
	return dict(values or {}), settings_name


def _company_institution_type(company: str) -> str:
	meta = frappe.get_meta("Company")
	if meta.has_field("eduedge_institution_type"):
		value = frappe.db.get_value("Company", company, "eduedge_institution_type")
		if value:
			return value
	return DEFAULT_INSTITUTION_TYPE


def _resolve_configuration(
	configuration: dict[str, Any] | None,
	*,
	institution_type: str,
	source: str,
	company: str,
	institution: str | None,
	settings_name: str | None,
	inherits_company: bool,
) -> dict[str, Any]:
	preset = recommended_question_governance(institution_type)
	configuration = configuration or {}
	configured_mode = str(configuration.get("question_approval_mode") or "Recommended")
	if configured_mode not in APPROVAL_MODES:
		configured_mode = "Recommended"
	approval_mode = preset["question_approval_mode"] if configured_mode == "Recommended" else configured_mode

	allow_bulk = _check_value(configuration, "allow_bulk_question_approval", preset)
	bulk_limit = cint(configuration.get("max_bulk_question_approval") or preset["max_bulk_question_approval"])
	bulk_limit = min(MAX_BULK_QUESTIONS, max(1, bulk_limit))
	separate_approver = _check_value(configuration, "require_separate_question_approver", preset)
	academic_admin_override = _check_value(configuration, "allow_academic_admin_override", preset)

	return {
		"company": company,
		"institution": institution,
		"institution_type": normalize_institution_type_code(institution_type) or DEFAULT_INSTITUTION_TYPE,
		"source": source,
		"settings_name": settings_name,
		"inherits_company": inherits_company,
		"configured_question_approval_mode": configured_mode,
		"question_approval_mode": approval_mode,
		"approval_steps": 1 if approval_mode == "Simple" else 2,
		"requires_recommendation": approval_mode == "Standard",
		"allow_bulk_question_approval": bool(allow_bulk),
		"max_bulk_question_approval": bulk_limit,
		"require_separate_question_approver": bool(separate_approver),
		"allow_academic_admin_override": bool(academic_admin_override),
	}


def _check_value(configuration: dict[str, Any], fieldname: str, preset: dict[str, Any]) -> int:
	value = configuration.get(fieldname)
	return cint(preset[fieldname] if value is None else value)
