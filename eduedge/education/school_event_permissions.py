from __future__ import annotations

import frappe

from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced


BRANCH_SCOPE_BYPASS_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def _should_apply_branch_scope(user: str) -> bool:
	if not is_branch_access_enforced():
		return False
	if not user or user in {"Administrator", "Guest"}:
		return user != "Administrator"
	return not bool(BRANCH_SCOPE_BYPASS_ROLES.intersection(frappe.get_roles(user)))


def _allowed_branch_names(user: str) -> set[str]:
	return {
		row.get("name")
		for row in get_allowed_school_branches(user=user)
		if row.get("name")
	}


def school_event_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tabEduEdge School Event`.`school_branch` in ({values})"


def has_school_event_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	if not doc:
		return True
	allowed = _allowed_branch_names(resolved_user)
	branch = doc.get("school_branch") if hasattr(doc, "get") else None
	return bool(branch and branch in allowed)
