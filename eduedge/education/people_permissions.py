from __future__ import annotations

import frappe

from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

BYPASS_ROLES = {"System Manager", "EduEdge Super Administrator", "EduEdge Administrator"}


def _scope_applies(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	return not bool(BYPASS_ROLES.intersection(frappe.get_roles(user)))


def _allowed(user: str) -> set[str]:
	return {row.get("name") for row in get_allowed_school_branches(user=user) if row.get("name")}


def _query(doctype: str, user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not _scope_applies(resolved):
		return ""
	allowed = _allowed(resolved)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`school_branch` in ({values})"


def instructor_assignment_query(user: str | None = None) -> str:
	return _query("EduEdge Instructor Assignment", user)


def student_photo_review_log_query(user: str | None = None) -> str:
	return _query("EduEdge Student Photo Review Log", user)


def has_people_branch_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if not _scope_applies(resolved):
		return True
	if not doc:
		return True
	return doc.get("school_branch") in _allowed(resolved)
