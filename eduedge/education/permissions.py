from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

BRANCH_AWARE_DOCTYPES = (
	"Student Admission",
	"Student Applicant",
	"Student",
	"Guardian",
	"Program Enrollment",
	"Student Group",
	"Room",
	"Course Schedule",
	"Student Attendance",
	"Assessment Plan",
	"Assessment Result",
	"EduEdge Result Publication",
	"EduEdge Report Card Review",
	"EduEdge Program Offering",
	"EduEdge Instructor Branch Assignment",
)
BRANCH_SCOPE_BYPASS_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def school_branch_query(user: str | None = None) -> str:
	if not is_branch_access_enforced():
		return ""
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tabEduEdge School Branch`.name in ({values})"


def student_admission_query(user: str | None = None) -> str:
	return _branch_condition("Student Admission", user)


def student_applicant_query(user: str | None = None) -> str:
	return _branch_condition("Student Applicant", user)


def student_query(user: str | None = None) -> str:
	return _branch_condition("Student", user)


def program_enrollment_query(user: str | None = None) -> str:
	return _branch_condition("Program Enrollment", user)


def student_group_query(user: str | None = None) -> str:
	return _branch_condition("Student Group", user)


def room_query(user: str | None = None) -> str:
	return _branch_condition("Room", user)


def course_schedule_query(user: str | None = None) -> str:
	return _branch_condition("Course Schedule", user)


def student_attendance_query(user: str | None = None) -> str:
	return _branch_condition("Student Attendance", user)


def assessment_plan_query(user: str | None = None) -> str:
	return _branch_condition("Assessment Plan", user)


def assessment_result_query(user: str | None = None) -> str:
	return _branch_condition("Assessment Result", user)


def result_publication_query(user: str | None = None) -> str:
	return _branch_condition("EduEdge Result Publication", user, fieldname="school_branch")


def result_publication_log_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
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
			from `tabEduEdge Result Publication` publication
			where publication.name = `tabEduEdge Result Publication Log`.result_publication
				and publication.school_branch in ({values})
		)
	"""


def report_card_review_query(user: str | None = None) -> str:
	return _branch_condition("EduEdge Report Card Review", user, fieldname="school_branch")


def program_offering_query(user: str | None = None) -> str:
	return _branch_condition("EduEdge Program Offering", user, fieldname="school_branch")


def instructor_assignment_query(user: str | None = None) -> str:
	return _branch_condition(
		"EduEdge Instructor Branch Assignment",
		user,
		fieldname="school_branch",
	)


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


def has_education_branch_permission(doc, user=None, permission_type=None) -> bool:
	"""Allow Role Permission Manager decisions unless branch isolation denies the record."""
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	if not doc:
		return True

	if doc.doctype == "Guardian":
		if doc.is_new():
			return True
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
		return bool(branches.intersection(allowed))

	if not _branch_field_exists(doc.doctype):
		return True
	branch = doc.get(BRANCH_FIELD)
	return branch in allowed


def has_school_branch_record_permission(doc, user=None, permission_type=None) -> bool:
	if not is_branch_access_enforced():
		return True
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	if not doc:
		return True
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	name = doc if isinstance(doc, str) else doc.name
	return name in allowed


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	if not doc:
		return True
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	return doc.get("school_branch") in allowed


def has_result_publication_log_permission(doc, user=None, permission_type=None) -> bool:
	if not doc:
		return True
	publication = frappe.db.get_value(
		"EduEdge Result Publication", doc.get("result_publication"), "school_branch"
	)
	if not publication:
		return False
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user):
		return True
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	return publication in allowed


def _branch_condition(
	doctype: str,
	user: str | None,
	*,
	fieldname: str = BRANCH_FIELD,
) -> str:
	resolved_user = user or frappe.session.user
	if not _should_apply_branch_scope(resolved_user) or not _branch_field_exists(
		doctype, fieldname
	):
		return ""
	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
	return f"`tab{doctype}`.`{fieldname}` in ({values})"


def _allowed_branch_names(user: str) -> set[str] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return {row["name"] for row in get_allowed_school_branches(user=user)}


def _should_apply_branch_scope(user: str) -> bool:
	if not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	if roles.intersection(BRANCH_SCOPE_BYPASS_ROLES):
		return False
	return any(
		user_has_role_permission(doctype, permission_type, user)
		for doctype in BRANCH_AWARE_DOCTYPES
		for permission_type in ("read", "create", "write", "report")
	)


def _branch_field_exists(doctype: str, fieldname: str = BRANCH_FIELD) -> bool:
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except frappe.DoesNotExistError:
		return False
