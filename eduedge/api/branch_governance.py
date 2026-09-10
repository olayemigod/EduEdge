from __future__ import annotations

import frappe
from frappe import _

from eduedge.access_control import user_has_role_permission
from eduedge.services.branch_governance import (
	get_branch_governance_context as _get_branch_governance_context,
	save_branch_access as _save_branch_access,
	set_branch_access_enabled as _set_branch_access_enabled,
	set_branch_enforcement as _set_branch_enforcement,
)


VIEW_REQUIREMENTS = (
	("EduEdge School Branch", "read"),
	("EduEdge User Branch Access", "read"),
	("EduEdge Instructor Branch Assignment", "read"),
)


def _has(permission_type: str, doctype: str) -> bool:
	return user_has_role_permission(doctype, permission_type, frappe.session.user)


def _require_any(requirements: tuple[tuple[str, str], ...], message: str) -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not any(_has(permission_type, doctype) for doctype, permission_type in requirements):
		frappe.throw(_(message), frappe.PermissionError)


@frappe.whitelist()
def get_governance_context(company: str | None = None) -> dict:
	_require_any(VIEW_REQUIREMENTS, "You are not permitted to view EduEdge branch governance.")
	can_read_access = _has("read", "EduEdge User Branch Access")
	can_manage_access = _has("create", "EduEdge User Branch Access") or _has(
		"write", "EduEdge User Branch Access"
	)
	can_manage_accounting = _has("write", "EduEdge School Branch")
	can_manage_enforcement = _has("write", "EduEdge Settings")
	context = _get_branch_governance_context(
		company=company,
		include_assignment_details=can_read_access,
		include_all_branches=can_manage_access or can_manage_accounting or can_manage_enforcement,
	)
	context["permissions"] = {
		"can_manage_access": can_manage_access,
		"can_view_access_details": can_read_access,
		"can_manage_accounting": can_manage_accounting,
		"can_manage_enforcement": can_manage_enforcement,
	}
	return context


@frappe.whitelist()
def save_branch_access(payload: str) -> dict:
	_require_any(
		(
			("EduEdge User Branch Access", "create"),
			("EduEdge User Branch Access", "write"),
		),
		"You are not permitted to manage EduEdge branch assignments.",
	)
	return _save_branch_access(payload)


@frappe.whitelist()
def set_branch_access_enabled(name: str, enabled: int | str) -> dict:
	_require_any(
		(("EduEdge User Branch Access", "write"),),
		"You are not permitted to change EduEdge branch assignments.",
	)
	return _set_branch_access_enabled(name, enabled)


@frappe.whitelist()
def set_branch_enforcement(enabled: int | str, confirmed: int | str = 0) -> dict:
	_require_any(
		(("EduEdge Settings", "write"),),
		"You are not permitted to change EduEdge branch enforcement.",
	)
	return _set_branch_enforcement(enabled, confirmed=confirmed)
