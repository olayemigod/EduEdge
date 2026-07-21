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


def examination_centre_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge Examination Centre", user)


def cbt_question_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Question", user)


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not is_branch_access_enforced() or not _should_apply_branch_scope(resolved_user):
		return None
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return None
	branch = doc.get("school_branch") if doc else None
	return None if branch and branch in allowed else False


def _school_branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not is_branch_access_enforced() or not _should_apply_branch_scope(resolved_user):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`school_branch` in ({values})"


def _allowed_branch_names(user: str) -> set[str] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return {row["name"] for row in get_allowed_school_branches(user=user)}


def _should_apply_branch_scope(user: str) -> bool:
	if not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	if roles.intersection(
		{"System Manager", "EduEdge Super Administrator", "EduEdge Administrator"}
	):
		return False
	return bool(roles.intersection(CBT_OPERATIONAL_ROLES))
