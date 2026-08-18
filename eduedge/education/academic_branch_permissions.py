from __future__ import annotations

import frappe

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}
SCOPED_ROLES = {
	"Academics User",
	"Education Manager",
	"Instructor",
	"School Administrator",
	"Academic Administrator",
	"Bursar",
	"Accounts User",
	"Accounts Manager",
	"Teacher",
	"Registrar",
	"Student Safety Officer",
}


def fee_schedule_query(user: str | None = None) -> str:
	return _branch_query("Fee Schedule", user)


def fees_query(user: str | None = None) -> str:
	return _branch_query("Fees", user)


def student_leave_query(user: str | None = None) -> str:
	return _branch_query("Student Leave Application", user)


def student_log_query(user: str | None = None) -> str:
	return _branch_query("Student Log", user)


def enrollment_status_log_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"""
		exists (
			select 1
			from `tabProgram Enrollment` enrollment
			where enrollment.name = `tabEduEdge Enrollment Status Log`.program_enrollment
				and enrollment.`{BRANCH_FIELD}` in ({values})
		)
	"""


def has_branch_context_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user) or not doc:
		return None
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return None
	branch = doc.get(BRANCH_FIELD)
	if not branch:
		return None
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return None
	return None if branch in allowed else False


def has_enrollment_status_log_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user) or not doc:
		return None
	branch = frappe.db.get_value(
		"Program Enrollment",
		doc.get("program_enrollment"),
		BRANCH_FIELD,
	)
	if not branch:
		return False
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return None
	return None if branch in allowed else False


def _branch_query(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(BRANCH_FIELD):
		return ""
	allowed = _allowed_branches(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`{BRANCH_FIELD}` in ({values})"


def _allowed_branches(user: str) -> set[str] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return {row.get("name") for row in get_allowed_school_branches(user=user) if row.get("name")}


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	if roles.intersection(PRIVILEGED_ROLES):
		return False
	return bool(roles.intersection(SCOPED_ROLES))
