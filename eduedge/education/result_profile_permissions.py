from __future__ import annotations

import frappe

from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

BYPASS_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def result_profile_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if resolved_user == "Guest":
		return "1=0"
	if not _should_scope(resolved_user):
		return ""

	branches = _allowed_branches(resolved_user)
	if not branches:
		return "1=0"
	branch_values = ", ".join(frappe.db.escape(name) for name in sorted(branches))
	institutions = _institutions_for_branches(branches)
	institution_condition = "1=0"
	if institutions:
		institution_values = ", ".join(
			frappe.db.escape(name) for name in sorted(institutions)
		)
		institution_condition = (
			f"(coalesce(`tabEduEdge Result Profile`.school_branch, '') = '' "
			f"and `tabEduEdge Result Profile`.institution in ({institution_values}))"
		)
	return (
		f"(`tabEduEdge Result Profile`.school_branch in ({branch_values}) "
		f"or {institution_condition})"
	)


def has_result_profile_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if resolved_user == "Guest":
		return False
	if not _should_scope(resolved_user):
		return True
	if not doc:
		return True
	branches = _allowed_branches(resolved_user)
	if not branches:
		return False
	if doc.get("school_branch"):
		return doc.get("school_branch") in branches
	return doc.get("institution") in _institutions_for_branches(branches)


def _allowed_branches(user: str) -> set[str]:
	return {
		row.get("name")
		for row in get_allowed_school_branches(user=user)
		if row.get("name")
	}


def _institutions_for_branches(branches: set[str]) -> set[str]:
	if not branches:
		return set()
	return {
		value
		for value in frappe.get_all(
			"EduEdge School Branch",
			filters={"name": ["in", sorted(branches)]},
			pluck="institution",
		)
		if value
	}


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced():
		return False
	if not user or user in {"Guest", "Administrator"}:
		return False
	return not bool(BYPASS_ROLES.intersection(frappe.get_roles(user)))
