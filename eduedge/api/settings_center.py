from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

MAX_OPTIONS = 50

TAB_CONFIG = {
	"defaults": {
		"label": _("School Defaults"),
		"description": _("Choose the default school company and campus used when no user-specific branch is active."),
		"fields": [
			{"fieldname": "default_company", "label": _("Default Company"), "type": "Link", "options_doctype": "Company"},
			{"fieldname": "default_school_branch", "label": _("Default School Branch"), "type": "Link", "options_doctype": "EduEdge School Branch"},
		],
	},
	"branding": {
		"label": _("Branding"),
		"description": _("Control the EduEdge product mark shown inside the school workspace."),
		"fields": [
			{"fieldname": "eduedge_logo", "label": _("EduEdge Logo"), "type": "Attach Image"},
		],
	},
	"branch_access": {
		"label": _("Branch Access"),
		"description": _("Control HQ visibility. Enforcement activation remains protected by Branch Governance readiness checks."),
		"fields": [
			{"fieldname": "allow_hq_all_branch_view", "label": _("Allow Authorised HQ All-Branch View"), "type": "Check"},
		],
	},
	"report_cards": {
		"label": _("Report Cards"),
		"description": _("Configure marks, comments, letterhead, and progression suggestion rules."),
		"fields": [
			{"fieldname": "report_card_show_marks", "label": _("Show Marks on Report Cards"), "type": "Check"},
			{"fieldname": "report_card_letter_head", "label": _("Report Card Letter Head"), "type": "Link", "options_doctype": "Letter Head"},
			{"fieldname": "promotion_pass_average", "label": _("Promotion Pass Average"), "type": "Percent", "min": 0, "max": 100},
			{"fieldname": "require_class_teacher_comment", "label": _("Require Class Teacher Comment"), "type": "Check"},
			{"fieldname": "require_principal_comment", "label": _("Require Principal Comment Before Approval"), "type": "Check"},
		],
	},
	"features": {
		"label": _("Feature Activation"),
		"description": _("Turn optional EduEdge capability areas on or off without changing academic records."),
		"fields": [
			{"fieldname": "enable_cbt", "label": _("Enable CBT"), "type": "Check"},
			{"fieldname": "enable_student_pickup", "label": _("Enable Student Pickup"), "type": "Check"},
			{"fieldname": "enable_school_intelligence", "label": _("Enable School Intelligence"), "type": "Check"},
			{"fieldname": "enable_edgefinder_publication", "label": _("Enable EdgeFinder Publication"), "type": "Check"},
		],
	},
}


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


def _field_map(tab: str) -> dict[str, dict]:
	return {field["fieldname"]: field for field in TAB_CONFIG[tab]["fields"]}


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
	return [
		{"value": row.name, "label": row.company_name or row.name}
		for row in rows
	]


def _branch_options(company: str | None = None) -> list[dict]:
	rows = get_allowed_school_branches(company=company)
	return [
		{"value": row.get("name"), "label": row.get("branch_name") or row.get("name"), "description": row.get("company") or ""}
		for row in rows[:MAX_OPTIONS]
	]


def _letter_head_options() -> list[dict]:
	if not frappe.db.exists("DocType", "Letter Head") or not frappe.has_permission("Letter Head", "read"):
		return []
	rows = frappe.get_list(
		"Letter Head",
		fields=["name", "is_default", "disabled"],
		order_by="is_default desc, name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{"value": row.name, "label": row.name, "description": _("Default") if row.is_default else ""}
		for row in rows
		if not row.disabled
	]


def _with_options(fields: list[dict], values: dict) -> list[dict]:
	result = deepcopy(fields)
	for field in result:
		if field.get("fieldname") == "default_company":
			field["options"] = _company_options()
		elif field.get("fieldname") == "default_school_branch":
			field["options"] = _branch_options(values.get("default_company"))
		elif field.get("fieldname") == "report_card_letter_head":
			field["options"] = _letter_head_options()
	return result


@frappe.whitelist()
def get_settings_center() -> dict:
	_require_login()
	if not frappe.has_permission("EduEdge Settings", "read"):
		frappe.throw(_("You are not permitted to view EduEdge Settings."), frappe.PermissionError)
	doc = frappe.get_single("EduEdge Settings")
	values = {
		fieldname: doc.get(fieldname)
		for config in TAB_CONFIG.values()
		for fieldname in {field["fieldname"] for field in config["fields"]}
	}
	tabs = []
	for key, config in TAB_CONFIG.items():
		tabs.append(
			{
				"key": key,
				"label": config["label"],
				"description": config["description"],
				"fields": _with_options(config["fields"], values),
			}
		)
	return {
		"tabs": tabs,
		"values": values,
		"can_write": bool(frappe.has_permission("EduEdge Settings", "write")),
		"branch_enforcement": {
			"enabled": is_branch_access_enforced(),
			"manage_route": "/app/eduedge-branch-governance",
		},
	}


@frappe.whitelist()
def get_default_branch_options(company: str | None = None) -> list[dict]:
	_require_login()
	if not frappe.has_permission("EduEdge Settings", "read"):
		frappe.throw(_("You are not permitted to view EduEdge Settings."), frappe.PermissionError)
	return _branch_options(company)


@frappe.whitelist()
def save_settings_tab(tab: str, values: str | dict) -> dict:
	_require_login()
	if tab not in TAB_CONFIG:
		frappe.throw(_("This settings section is not available."), frappe.PermissionError)
	if not frappe.has_permission("EduEdge Settings", "write"):
		frappe.throw(_("You are not permitted to change EduEdge Settings."), frappe.PermissionError)
	payload = _parse_json(values)
	allowed = _field_map(tab)
	clean_values = {
		fieldname: cint(value) if str(field.get("type", "")).lower() == "check" else value
		for fieldname, value in payload.items()
		if (field := allowed.get(fieldname))
	}
	if tab == "defaults":
		company = clean_values.get("default_company")
		branch = clean_values.get("default_school_branch")
		if branch:
			branch_company = frappe.db.get_value("EduEdge School Branch", branch, "company")
			if company and branch_company != company:
				frappe.throw(_("Default School Branch must belong to the selected Default Company."), frappe.ValidationError)
			if branch not in {row.get("name") for row in get_allowed_school_branches(company=company)}:
				frappe.throw(_("You are not permitted to select this School Branch."), frappe.PermissionError)
	doc = frappe.get_single("EduEdge Settings")
	doc.check_permission("write")
	doc.update(clean_values)
	doc.save()
	return {
		"tab": tab,
		"values": {fieldname: doc.get(fieldname) for fieldname in allowed},
	}
