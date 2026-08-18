from __future__ import annotations

import frappe

from eduedge.services.branch_context import (
	get_allowed_institutions,
	is_branch_access_enforced,
)

PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}


def institution_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	institutions = {
		row.get("name")
		for row in get_allowed_institutions(user=resolved_user)
		if row.get("name")
	}
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	return f"`tabEduEdge Institution`.name in ({values})"


def has_institution_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not doc or not _should_scope(resolved_user):
		return True
	allowed = {
		row.get("name")
		for row in get_allowed_institutions(user=resolved_user)
		if row.get("name")
	}
	return doc.name in allowed


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	return not bool(roles.intersection(PRIVILEGED_ROLES))
