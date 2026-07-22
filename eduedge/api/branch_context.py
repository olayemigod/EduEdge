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
from eduedge.services.institution_context import get_effective_institution_context


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required.", frappe.PermissionError)


def _institution_context_for_branch(branch: dict | None) -> dict:
	row = dict(branch or {})
	is_all_branches = bool(row.get("is_all_branches"))
	return get_effective_institution_context(
		company=row.get("company"),
		branch=None if is_all_branches else row.get("name"),
	)


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
	payload = dict(_get_active_branch_context() or {})
	payload["institution_context"] = _institution_context_for_branch(payload.get("current_branch"))
	return payload


@frappe.whitelist()
def get_branch_access_profile() -> dict:
	_require_login()
	return _get_branch_access_profile()


@frappe.whitelist()
@guard_eduedge_action("school_branch", action="switch_school_branch")
def switch_school_branch(branch: str, company: str | None = None) -> dict:
	_require_login()
	selected = dict(_switch_school_branch(branch, company=company) or {})
	selected["institution_context"] = _institution_context_for_branch(selected)
	return selected


@frappe.whitelist()
@guard_eduedge_action("school_branch", action="clear_school_branch")
def clear_school_branch() -> None:
	_require_login()
	_clear_school_branch()
