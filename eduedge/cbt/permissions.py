from __future__ import annotations

import frappe

from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

CBT_OPERATIONAL_ROLES = {
	"Academics User",
	"Education Manager",
	"Instructor",
	"Teacher",
	"School Administrator",
	"Academic Administrator",
	"CBT Invigilator",
}
PLATFORM_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def examination_centre_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge Examination Centre", user)


def cbt_question_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Question", user)


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if _is_platform_manager(resolved_user) or not _is_cbt_operational_user(resolved_user):
		return None

	branch = doc.get("school_branch") if doc else None
	if not branch:
		# Platform-level centres and questions must never be exposed through
		# ordinary school-role DocPerms, even before strict branch enforcement.
		return False
	if not is_branch_access_enforced():
		return None

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return None
	return None if branch in allowed else False


def _school_branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if _is_platform_manager(resolved_user) or not _is_cbt_operational_user(resolved_user):
		return ""

	# Keep platform-owned records hidden from school roles even when the site
	# is still using the legacy branch-access fallback.
	if not is_branch_access_enforced():
		return f"`tab{doctype}`.`school_branch` is not null"

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return f"`tab{doctype}`.`school_branch` is not null"
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`school_branch` in ({values})"


def _allowed_branch_names(user: str) -> set[str] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return {row["name"] for row in get_allowed_school_branches(user=user)}


def _is_platform_manager(user: str) -> bool:
	if user == "Administrator":
		return True
	if not user or user == "Guest":
		return False
	return bool(set(frappe.get_roles(user)).intersection(PLATFORM_MANAGER_ROLES))


def _is_cbt_operational_user(user: str) -> bool:
	if not user or user in {"Guest", "Administrator"}:
		return False
	return bool(set(frappe.get_roles(user)).intersection(CBT_OPERATIONAL_ROLES))
