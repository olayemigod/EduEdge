from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.operations_policy import (
	APPROVAL_MODES,
	COMPANY_SETTINGS_DOCTYPE,
	MAX_BULK_QUESTIONS,
	QUESTION_GOVERNANCE_FIELDS,
	recommended_question_governance,
	resolve_company_question_governance,
	resolve_question_governance,
)
from eduedge.platform.access import require_eduedge_access


COMPANY_SCOPE = "Company Default"
INSTITUTION_SCOPE = "Institution Preference"
SCOPES = (COMPANY_SCOPE, INSTITUTION_SCOPE)
MAX_OPTIONS = 50


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _parse_json(value: Any) -> dict:
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Expected a JSON object."), frappe.ValidationError)
	return parsed


def _company_options() -> list[dict]:
	if not frappe.has_permission("Company", "read"):
		return []
	rows = frappe.get_list(
		"Company",
		filters={"is_group": 0},
		fields=["name", "company_name"],
		order_by="company_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [{"value": row.name, "label": row.company_name or row.name} for row in rows]


def _institution_options(company: str | None) -> list[dict]:
	if not company or not frappe.has_permission("EduEdge Institution", "read"):
		return []
	rows = frappe.get_list(
		"EduEdge Institution",
		filters={"company": company, "enabled": 1},
		fields=["name", "institution_name", "institution_type", "is_default"],
		order_by="is_default desc, institution_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{
			"value": row.name,
			"label": row.institution_name or row.name,
			"description": row.institution_type or "",
			"institution_type": row.institution_type or "",
			"is_default": bool(row.is_default),
		}
		for row in rows
	]


def _available_scopes() -> list[str]:
	scopes = []
	if frappe.has_permission("EduEdge Institution", "read"):
		scopes.append(INSTITUTION_SCOPE)
	if frappe.has_permission(COMPANY_SETTINGS_DOCTYPE, "read"):
		scopes.append(COMPANY_SCOPE)
	return scopes


def _select_option(requested: str | None, options: list[dict], fallback: str | None = None) -> str:
	ordered_values = [row.get("value") for row in options if row.get("value")]
	allowed = set(ordered_values)
	if requested and requested in allowed:
		return requested
	if fallback and fallback in allowed:
		return fallback
	return ordered_values[0] if ordered_values else ""


def _default_company(options: list[dict]) -> str:
	default_company = ""
	if frappe.db.exists("DocType", "EduEdge Settings"):
		default_company = frappe.db.get_single_value("EduEdge Settings", "default_company") or ""
	return _select_option(default_company, options)


def _company_values(company: str) -> dict:
	settings_name = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, {"company": company}, "name")
	if not settings_name:
		return {
			"question_approval_mode": "Recommended",
			"allow_bulk_question_approval": 1,
			"max_bulk_question_approval": MAX_BULK_QUESTIONS,
			"require_separate_question_approver": 1,
			"allow_academic_admin_override": 1,
		}
	values = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, settings_name, list(QUESTION_GOVERNANCE_FIELDS), as_dict=True)
	return dict(values or {})


def _institution_values(institution: str) -> dict:
	fields = ["use_company_question_governance_defaults", *QUESTION_GOVERNANCE_FIELDS]
	values = frappe.db.get_value("EduEdge Institution", institution, fields, as_dict=True)
	return dict(values or {})


def _effective_institution_values(values: dict, effective_policy: dict | None) -> dict:
	"""Show effective Company values when an Institution is inheriting.

	The Institution record retains its own stored override values. They must not be
	displayed in disabled controls while Company inheritance is active because that
	misrepresents the policy that EduEdge will actually enforce.
	"""
	if not cint(values.get("use_company_question_governance_defaults")) or not effective_policy:
		return values

	display_values = dict(values)
	display_values.update(
		{
			"question_approval_mode": effective_policy.get("question_approval_mode") or "Recommended",
			"allow_bulk_question_approval": cint(effective_policy.get("allow_bulk_question_approval")),
			"max_bulk_question_approval": cint(
				effective_policy.get("max_bulk_question_approval") or MAX_BULK_QUESTIONS
			),
			"require_separate_question_approver": cint(
				effective_policy.get("require_separate_question_approver")
			),
			"allow_academic_admin_override": cint(effective_policy.get("allow_academic_admin_override")),
		}
	)
	return display_values


def _company_can_write(company: str) -> bool:
	settings_name = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, {"company": company}, "name")
	if settings_name:
		doc = frappe.get_doc(COMPANY_SETTINGS_DOCTYPE, settings_name)
		return bool(doc.has_permission("write"))
	return bool(frappe.has_permission(COMPANY_SETTINGS_DOCTYPE, "create"))


def _institution_can_write(institution: str) -> bool:
	if not institution:
		return False
	doc = frappe.get_doc("EduEdge Institution", institution)
	return bool(doc.has_permission("write"))


def _settings_fields(scope: str) -> list[dict]:
	fields = []
	if scope == INSTITUTION_SCOPE:
		fields.append(
			{
				"fieldname": "use_company_question_governance_defaults",
				"type": "Check",
				"label": _("Use Company Question Governance Defaults"),
				"description": _("Keep enabled for the simplest setup. Disable only when this Institution needs a different approval process."),
			}
		)
	fields.extend(
		[
			{
				"fieldname": "question_approval_mode",
				"type": "Select",
				"label": _("Question Approval Mode"),
				"options": [{"value": value, "label": value} for value in APPROVAL_MODES],
				"description": _("Recommended follows the Institution Type. Simple has one approval stage; Standard separates review and final approval."),
			},
			{
				"fieldname": "allow_bulk_question_approval",
				"type": "Check",
				"label": _("Allow Bulk Question Approval"),
			},
			{
				"fieldname": "max_bulk_question_approval",
				"type": "Int",
				"label": _("Maximum Questions per Bulk Action"),
				"min": 1,
				"max": MAX_BULK_QUESTIONS,
			},
			{
				"fieldname": "require_separate_question_approver",
				"type": "Check",
				"label": _("Require Different Author and Approver"),
			},
			{
				"fieldname": "allow_academic_admin_override",
				"type": "Check",
				"label": _("Allow Academic Administrator Override"),
			},
		]
	)
	return fields


@frappe.whitelist()
def get_settings_context(
	scope: str | None = None,
	company: str | None = None,
	institution: str | None = None,
) -> dict:
	_require_login()
	scopes = _available_scopes()
	if not scopes:
		frappe.throw(_("You are not permitted to view Institution Operations Settings."), frappe.PermissionError)
	resolved_scope = scope if scope in scopes else (INSTITUTION_SCOPE if INSTITUTION_SCOPE in scopes else scopes[0])

	company_options = _company_options()
	selected_company = _select_option(company, company_options, _default_company(company_options))
	institution_options = _institution_options(selected_company)
	selected_institution = _select_option(institution, institution_options)

	if resolved_scope == COMPANY_SCOPE:
		if not selected_company:
			values = {}
			effective_policy = None
			can_write = False
		else:
			values = _company_values(selected_company)
			effective_policy = resolve_company_question_governance(selected_company)
			can_write = _company_can_write(selected_company)
	else:
		if not selected_institution:
			values = {}
			effective_policy = None
			can_write = False
		else:
			doc = frappe.get_doc("EduEdge Institution", selected_institution)
			doc.check_permission("read")
			if doc.company != selected_company:
				frappe.throw(_("The selected Institution does not belong to this Company."), frappe.ValidationError)
			values = _institution_values(selected_institution)
			effective_policy = resolve_question_governance(selected_institution)
			if cint(values.get("use_company_question_governance_defaults")) and effective_policy:
				effective_policy = dict(effective_policy)
				effective_policy["source"] = COMPANY_SCOPE
				values = _effective_institution_values(values, effective_policy)
			can_write = _institution_can_write(selected_institution)

	return {
		"scope": resolved_scope,
		"scope_options": [{"value": value, "label": value} for value in scopes],
		"company": selected_company,
		"company_options": company_options,
		"institution": selected_institution,
		"institution_options": institution_options,
		"fields": _settings_fields(resolved_scope),
		"values": values,
		"can_write": can_write,
		"effective_policy": effective_policy,
		"recommended_defaults": recommended_question_governance(
			(effective_policy or {}).get("institution_type")
		),
		"future_sections": [
			_("Assessment and Results"),
			_("Attendance and Timetable"),
			_("Admissions and Enrolment"),
			_("Fees and Accounting"),
			_("Student Safety"),
			_("Communication and Notifications"),
		],
	}


@frappe.whitelist()
def save_settings(
	scope: str,
	company: str,
	values: str | dict,
	institution: str | None = None,
) -> dict:
	_require_login()
	if scope not in SCOPES:
		frappe.throw(_("Select a valid settings level."), frappe.ValidationError)
	if scope not in _available_scopes():
		frappe.throw(_("You are not permitted to change this settings level."), frappe.PermissionError)
	company_names = {row.get("value") for row in _company_options()}
	if not company or company not in company_names:
		frappe.throw(_("Select a permitted Company."), frappe.PermissionError)

	payload = _parse_json(values)
	clean_values = _clean_question_governance_values(payload)
	require_eduedge_access(feature_key="foundation", action="save_institution_operations_settings")

	if scope == COMPANY_SCOPE:
		_save_company_settings(company, clean_values)
		resolved_institution = None
	else:
		resolved_institution = institution or ""
		institution_names = {row.get("value") for row in _institution_options(company)}
		if not resolved_institution or resolved_institution not in institution_names:
			frappe.throw(_("Select a permitted Institution."), frappe.PermissionError)
		_save_institution_settings(resolved_institution, company, payload, clean_values)

	return get_settings_context(scope=scope, company=company, institution=resolved_institution)


def _clean_question_governance_values(payload: dict) -> dict:
	mode = str(payload.get("question_approval_mode") or "Recommended")
	if mode not in APPROVAL_MODES:
		frappe.throw(_("Question Approval Mode must be Recommended, Simple, or Standard."), frappe.ValidationError)
	bulk_limit = cint(payload.get("max_bulk_question_approval") or MAX_BULK_QUESTIONS)
	if not 1 <= bulk_limit <= MAX_BULK_QUESTIONS:
		frappe.throw(
			_("Maximum Questions per Bulk Action must be between 1 and {0}.").format(MAX_BULK_QUESTIONS),
			frappe.ValidationError,
		)
	return {
		"question_approval_mode": mode,
		"allow_bulk_question_approval": cint(payload.get("allow_bulk_question_approval")),
		"max_bulk_question_approval": bulk_limit,
		"require_separate_question_approver": cint(payload.get("require_separate_question_approver")),
		"allow_academic_admin_override": cint(payload.get("allow_academic_admin_override")),
	}


def _save_company_settings(company: str, clean_values: dict) -> None:
	settings_name = frappe.db.get_value(COMPANY_SETTINGS_DOCTYPE, {"company": company}, "name")
	if settings_name:
		doc = frappe.get_doc(COMPANY_SETTINGS_DOCTYPE, settings_name)
		doc.check_permission("write")
		doc.update(clean_values)
		doc.save()
		return
	if not frappe.has_permission(COMPANY_SETTINGS_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create Company operations defaults."), frappe.PermissionError)
	doc = frappe.new_doc(COMPANY_SETTINGS_DOCTYPE)
	doc.company = company
	doc.update(clean_values)
	doc.insert()


def _save_institution_settings(institution: str, company: str, payload: dict, clean_values: dict) -> None:
	doc = frappe.get_doc("EduEdge Institution", institution)
	doc.check_permission("write")
	if doc.company != company:
		frappe.throw(_("The selected Institution does not belong to this Company."), frappe.ValidationError)
	doc.use_company_question_governance_defaults = cint(payload.get("use_company_question_governance_defaults"))
	doc.update(clean_values)
	doc.save()
