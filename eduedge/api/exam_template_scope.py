from __future__ import annotations

import frappe
from frappe import _

from eduedge.api.exam_templates import (
	TEMPLATE_DOCTYPE,
	_allowed_branch_rows,
	_branch_options,
	_company_options,
	_institution_options,
	_parse_json,
	_require_allowed,
	_require_login,
)


@frappe.whitelist()
def get_scope_options(values: str | dict | None = None) -> dict:
	_require_login()
	if not any(
		frappe.has_permission(TEMPLATE_DOCTYPE, permission_type)
		for permission_type in ("read", "create", "write")
	):
		frappe.throw(_("You are not permitted to configure CBT exam templates."), frappe.PermissionError)

	payload = _parse_json(values)
	branches = _allowed_branch_rows()
	companies = _company_options(branches)
	company = _require_allowed(
		payload.get("company"),
		{row["value"] for row in companies},
		_("Company"),
	)
	institutions = _institution_options(branches, company)
	institution = _require_allowed(
		payload.get("institution"),
		{row["value"] for row in institutions},
		_("Institution"),
	)
	return {
		"company_options": companies,
		"institution_options": institutions,
		"allowed_branches": _branch_options(branches, company, institution),
	}
