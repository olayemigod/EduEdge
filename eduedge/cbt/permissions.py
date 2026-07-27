from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import can_assign_public_exams, can_author_public_exams
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

CBT_DOCTYPES = (
	"EduEdge Examination Centre",
	"EduEdge CBT Question",
	"EduEdge CBT Exam Template",
	"EduEdge CBT Exam Schedule",
	"EduEdge CBT Candidate Assignment",
	"EduEdge CBT Intervention Log",
	"EduEdge CBT Attempt",
	"EduEdge CBT Attempt Scoring Key",
	"EduEdge CBT Attempt Answer",
	"EduEdge CBT Sync Log",
)

PUBLIC_ASSIGNMENT_DOCTYPES = {
	"EduEdge CBT Candidate Assignment",
	"EduEdge CBT Intervention Log",
}


def examination_centre_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge Examination Centre", user)


def cbt_question_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Question", user)


def cbt_exam_template_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Exam Template", user)


def cbt_exam_schedule_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Exam Schedule", user)


def cbt_candidate_assignment_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Candidate Assignment", user)


def cbt_intervention_log_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Intervention Log", user)


def cbt_attempt_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Attempt", user)


def cbt_attempt_scoring_key_query(user: str | None = None) -> str:
	return _attempt_reference_condition("EduEdge CBT Attempt Scoring Key", user)


def cbt_attempt_answer_query(user: str | None = None) -> str:
	return _attempt_reference_condition("EduEdge CBT Attempt Answer", user)


def cbt_sync_log_query(user: str | None = None) -> str:
	return _attempt_reference_condition("EduEdge CBT Sync Log", user)


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool:
	"""Allow role permissions unless public-exam or Branch isolation denies the record."""
	resolved_user = user or frappe.session.user
	if not _is_cbt_operational_user(resolved_user):
		return True

	branch = doc.get("school_branch") if doc else None
	if not branch:
		return _has_public_record_access(doc.doctype if doc else None, resolved_user)
	if not is_branch_access_enforced():
		return True

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	return branch in allowed


def has_attempt_reference_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	attempt_name = doc.get("attempt") if doc else None
	if not attempt_name:
		return False
	attempt = frappe.db.get_value(
		"EduEdge CBT Attempt",
		attempt_name,
		["name", "school_branch", "exam_scope"],
		as_dict=True,
	)
	if not attempt:
		return False
	attempt.doctype = "EduEdge CBT Attempt"
	return has_school_branch_permission(attempt, resolved_user, permission_type)


def _school_branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _is_cbt_operational_user(resolved_user):
		return ""
	if _has_public_record_access(doctype, resolved_user):
		return ""

	if not is_branch_access_enforced():
		return f"`tab{doctype}`.`school_branch` is not null"

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return f"`tab{doctype}`.`school_branch` is not null"
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`school_branch` in ({values})"


def _attempt_reference_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _is_cbt_operational_user(resolved_user):
		return ""
	if can_author_public_exams(resolved_user):
		return ""

	if not is_branch_access_enforced():
		return (
			f"exists (select 1 from `tabEduEdge CBT Attempt` attempt "
			f"where attempt.name = `tab{doctype}`.`attempt` "
			"and attempt.school_branch is not null)"
		)

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return (
			f"exists (select 1 from `tabEduEdge CBT Attempt` attempt "
			f"where attempt.name = `tab{doctype}`.`attempt` "
			"and attempt.school_branch is not null)"
		)
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return (
		f"exists (select 1 from `tabEduEdge CBT Attempt` attempt "
		f"where attempt.name = `tab{doctype}`.`attempt` "
		f"and attempt.school_branch in ({values}))"
	)


def _has_public_record_access(doctype: str | None, user: str) -> bool:
	if doctype in PUBLIC_ASSIGNMENT_DOCTYPES:
		return can_assign_public_exams(user)
	return can_author_public_exams(user)


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
