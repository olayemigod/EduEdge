from __future__ import annotations

import frappe
from frappe import _

from eduedge.services.branch_governance import (
	get_branch_governance_context as _get_branch_governance_context,
	save_branch_access as _save_branch_access,
	set_branch_access_enabled as _set_branch_access_enabled,
	set_branch_enforcement as _set_branch_enforcement,
)

VIEW_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Bursar",
}
MANAGE_ROLES = {"System Manager", "EduEdge Administrator"}


def _require_roles(allowed_roles: set[str]) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not allowed_roles.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to use EduEdge branch governance."), frappe.PermissionError)


@frappe.whitelist()
def get_governance_context(company: str | None = None) -> dict:
	_require_roles(VIEW_ROLES)
	context = _get_branch_governance_context(company=company)
	roles = set(frappe.get_roles(frappe.session.user))
	context["permissions"] = {
		"can_manage_access": bool(MANAGE_ROLES.intersection(roles)),
		"can_manage_accounting": bool(
			{"System Manager", "EduEdge Administrator", "School Administrator"}.intersection(roles)
		),
	}
	return context


@frappe.whitelist()
def save_branch_access(payload: str) -> dict:
	_require_roles(MANAGE_ROLES)
	return _save_branch_access(payload)


@frappe.whitelist()
def set_branch_access_enabled(name: str, enabled: int | str) -> dict:
	_require_roles(MANAGE_ROLES)
	return _set_branch_access_enabled(name, enabled)


@frappe.whitelist()
def set_branch_enforcement(enabled: int | str, confirmed: int | str = 0) -> dict:
	_require_roles(MANAGE_ROLES)
	return _set_branch_enforcement(enabled, confirmed=confirmed)
