from __future__ import annotations

import frappe

from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

CBT_STAFF_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Teacher",
	"CBT Invigilator",
}
CBT_UNSCOPED_ROLES = {"System Manager", "EduEdge Administrator"}


def cbt_question_query(user: str | None = None) -> str:
	return _branch_query("EduEdge CBT Question", user)


def cbt_exam_query(user: str | None = None) -> str:
	return _branch_query("EduEdge CBT Exam", user)


def cbt_attempt_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if _is_student(resolved_user):
		return f"`tabEduEdge CBT Attempt`.`user` = {frappe.db.escape(resolved_user)}"
	return _branch_query("EduEdge CBT Attempt", resolved_user)


def cbt_answer_query(user: str | None = None) -> str:
	return _attempt_child_query("EduEdge CBT Attempt Answer", user)


def cbt_sync_log_query(user: str | None = None) -> str:
	return _attempt_child_query("EduEdge CBT Sync Log", user)


def has_cbt_question_permission(doc, user=None, permission_type=None) -> bool | None:
	return _has_branch_permission(doc.get("school_branch"), user)


def has_cbt_exam_permission(doc, user=None, permission_type=None) -> bool | None:
	return _has_branch_permission(doc.get("school_branch"), user)


def has_cbt_attempt_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if _is_student(resolved_user):
		return None if doc.get("user") == resolved_user else False
	return _has_branch_permission(doc.get("school_branch"), resolved_user)


def has_cbt_answer_permission(doc, user=None, permission_type=None) -> bool | None:
	return _has_attempt_child_permission(doc, user)


def has_cbt_sync_log_permission(doc, user=None, permission_type=None) -> bool | None:
	return _has_attempt_child_permission(doc, user)


def _has_attempt_child_permission(doc, user=None) -> bool | None:
	resolved_user = user or frappe.session.user
	attempt_name = doc.get("attempt")
	if not attempt_name:
		return False
	attempt = frappe.db.get_value(
		"EduEdge CBT Attempt",
		attempt_name,
		["user", "school_branch"],
		as_dict=True,
	)
	if not attempt:
		return False
	if _is_student(resolved_user):
		return None if attempt.user == resolved_user else False
	return _has_branch_permission(attempt.school_branch, resolved_user)


def _attempt_child_query(doctype: str, user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if _is_student(resolved_user):
		return f"""
			exists (
				select 1
				from `tabEduEdge CBT Attempt` attempt
				where attempt.name = `tab{doctype}`.attempt
					and attempt.user = {frappe.db.escape(resolved_user)}
			)
		"""
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"""
		exists (
			select 1
			from `tabEduEdge CBT Attempt` attempt
			where attempt.name = `tab{doctype}`.attempt
				and attempt.school_branch in ({values})
		)
	"""


def _branch_query(doctype: str, user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if _is_student(resolved_user):
		return "1=0"
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`school_branch` in ({values})"


def _has_branch_permission(branch: str | None, user: str | None = None) -> bool | None:
	resolved_user = user or frappe.session.user
	if _is_student(resolved_user):
		return False
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return None
	return None if branch in allowed else False


def _allowed_branches(user: str) -> set[str] | None:
	if not user or user in {"Guest", "Administrator"}:
		return None
	roles = set(frappe.get_roles(user))
	if roles.intersection(CBT_UNSCOPED_ROLES):
		return None
	if not roles.intersection(CBT_STAFF_ROLES):
		return set()
	if not is_branch_access_enforced():
		return None
	return {row["name"] for row in get_allowed_school_branches(user=user)}


def _is_student(user: str) -> bool:
	return bool(user and user != "Administrator" and "Student" in frappe.get_roles(user))
