from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import can_author_public_exams
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

CBT_DOCTYPES = (
	"EduEdge Examination Centre",
	"EduEdge CBT Question",
	"EduEdge CBT Exam Template",
	"EduEdge CBT Exam Schedule",
)


def examination_centre_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge Examination Centre", user)


def cbt_question_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Question", user)


def cbt_exam_template_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Exam Template", user)


def cbt_exam_schedule_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Exam Schedule", user)


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool:
	"""Allow role permissions unless tenant/public or branch isolation denies the record."""
	resolved_user = user or frappe.session.user
	if can_author_public_exams(resolved_user) or not _is_cbt_operational_user(resolved_user):
		return True

	branch = doc.get("school_branch") if doc else None
	if not branch:
		# Public centres, questions, templates, and schedules are visible only to
		# identities with the CoreEdge author capability and an explicit role.
		return False
	if not is_branch_access_enforced():
		return True

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	return branch in allowed


def _school_branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if can_author_public_exams(resolved_user) or not _is_cbt_operational_user(resolved_user):
		return ""

	# Keep centrally owned public records hidden from tenant and standalone
	# school roles even when the site is still using legacy branch fallback.
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


def _is_cbt_operational_user(user: str) -> bool:
	if not user or user == "Guest":
		return False
	return any(
		user_has_role_permission(doctype, permission_type, user)
		for doctype in CBT_DOCTYPES
		for permission_type in ("read", "create", "write", "report")
	)
