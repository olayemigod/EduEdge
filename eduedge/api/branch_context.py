from __future__ import annotations

import frappe

from eduedge.platform.access import guard_eduedge_action
from eduedge.services.branch_context import (
	clear_school_branch as _clear_school_branch,
	get_active_branch_context as _get_active_branch_context,
	get_allowed_school_branches as _get_allowed_school_branches,
	get_branch_access_profile as _get_branch_access_profile,
	get_current_school_branch as _get_current_school_branch,
	switch_school_branch as _switch_school_branch,
)


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required.", frappe.PermissionError)


@frappe.whitelist()
def get_allowed_school_branches(company: str | None = None) -> list[dict]:
	_require_login()
	return _get_allowed_school_branches(company=company)


@frappe.whitelist()
def get_current_school_branch() -> dict | None:
	_require_login()
	return _get_current_school_branch()


@frappe.whitelist()
def get_active_branch_context() -> dict:
	_require_login()
	return _get_active_branch_context()


@frappe.whitelist()
def get_branch_access_profile() -> dict:
	_require_login()
	return _get_branch_access_profile()


@frappe.whitelist()
@guard_eduedge_action("school_branch", action="switch_school_branch")
def switch_school_branch(branch: str, company: str | None = None) -> dict:
	_require_login()
	return _switch_school_branch(branch, company=company)


@frappe.whitelist()
@guard_eduedge_action("school_branch", action="clear_school_branch")
def clear_school_branch() -> None:
	_require_login()
	_clear_school_branch()
