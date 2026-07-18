from __future__ import annotations

import frappe

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches

OPERATIONAL_ROLES = {
	"Academics User",
	"Instructor",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Bursar",
	"Teacher",
	"CBT Invigilator",
	"Student Safety Officer",
}


def student_applicant_query(user: str | None = None) -> str:
	return _branch_condition("Student Applicant", user)


def student_query(user: str | None = None) -> str:
	return _branch_condition("Student", user)


def program_enrollment_query(user: str | None = None) -> str:
	return _branch_condition("Program Enrollment", user)


def guardian_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user) or not _branch_field_exists("Student"):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"""
		exists (
			select 1
			from `tabGuardian Student` guardian_student
			inner join `tabStudent` student on student.name = guardian_student.student
			where guardian_student.parent = `tabGuardian`.name
				and guardian_student.parenttype = 'Guardian'
				and student.`{BRANCH_FIELD}` in ({values})
		)
	"""


def has_education_branch_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return None
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return None

	if doc.doctype == "Guardian":
		if doc.is_new():
			return None
		student_names = [row.student for row in (doc.get("students") or []) if row.student]
		if not student_names:
			return False
		branches = set(
			frappe.get_all(
				"Student",
				filters={"name": ["in", student_names]},
				pluck=BRANCH_FIELD,
			)
		)
		return None if branches.intersection(allowed) else False

	if not _branch_field_exists(doc.doctype):
		return None
	branch = doc.get(BRANCH_FIELD)
	return None if branch in allowed else False


def _branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user) or not _branch_field_exists(doctype):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`{BRANCH_FIELD}` in ({values})"


def _allowed_branch_names(user: str) -> set[str] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return {row["name"] for row in get_allowed_school_branches(user=user)}


def _should_apply_branch_scope(user: str) -> bool:
	if not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	if "System Manager" in roles:
		return False
	return bool(roles.intersection(OPERATIONAL_ROLES))


def _branch_field_exists(doctype: str) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(BRANCH_FIELD))
	except frappe.DoesNotExistError:
		return False
