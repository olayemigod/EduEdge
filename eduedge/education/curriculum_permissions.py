from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_permissions import course_query as institution_course_query
from eduedge.education.academic_permissions import has_academic_institution_permission
from eduedge.education.curriculum_fields import TOPIC_COURSE_FIELD
from eduedge.services.branch_context import get_allowed_institutions, is_branch_access_enforced

PRIVILEGED_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}
MANAGER_ROLES = PRIVILEGED_ROLES | {
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
}
TEACHER_ROLES = {"Teacher", "Instructor"}


def _roles(user: str) -> set[str]:
	return set(frappe.get_roles(user))


def is_privileged_curriculum_user(user: str | None = None) -> bool:
	resolved = user or frappe.session.user
	return resolved == "Administrator" or bool(_roles(resolved).intersection(PRIVILEGED_ROLES))


def is_curriculum_manager(user: str | None = None) -> bool:
	resolved = user or frappe.session.user
	return resolved == "Administrator" or bool(_roles(resolved).intersection(MANAGER_ROLES))


def is_teacher_user(user: str | None = None) -> bool:
	resolved = user or frappe.session.user
	roles = _roles(resolved)
	return bool(roles.intersection(TEACHER_ROLES)) and not is_curriculum_manager(resolved)


def current_user_instructors(user: str | None = None) -> list[str]:
	resolved = user or frappe.session.user
	if not resolved or resolved == "Guest" or not frappe.db.exists("DocType", "Instructor"):
		return []
	instructors: set[str] = set()
	if frappe.get_meta("Instructor").has_field("eduedge_email"):
		instructors.update(
			frappe.get_all("Instructor", filters={"eduedge_email": resolved, "status": "Active"}, pluck="name")
		)
	if frappe.db.exists("DocType", "Employee") and frappe.get_meta("Employee").has_field("user_id"):
		employees = frappe.get_all("Employee", filters={"user_id": resolved, "status": "Active"}, pluck="name")
		if employees:
			instructors.update(
				frappe.get_all("Instructor", filters={"employee": ["in", employees], "status": "Active"}, pluck="name")
			)
	return sorted(instructors)


def assigned_course_rows(user: str | None = None, branch: str | None = None) -> list[dict]:
	resolved = user or frappe.session.user
	instructors = current_user_instructors(resolved)
	if not instructors or not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
		return []
	filters: dict = {
		"instructor": ["in", instructors],
		"enabled": 1,
		"course": ["is", "set"],
	}
	if branch:
		filters["school_branch"] = branch
	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters=filters,
		fields=["name", "course", "school_branch", "institution", "program_offering", "student_group", "academic_year", "academic_term", "valid_from", "valid_to", "assignment_type"],
		order_by="modified desc",
		limit_page_length=0,
	)
	today = getdate(nowdate())
	return [
		row for row in rows
		if (not row.valid_from or getdate(row.valid_from) <= today)
		and (not row.valid_to or getdate(row.valid_to) >= today)
	]


def assigned_courses(user: str | None = None, branch: str | None = None) -> set[str]:
	return {row.course for row in assigned_course_rows(user, branch) if row.course}


def _allowed_institutions(user: str) -> set[str]:
	return {
		row.get("name") for row in get_allowed_institutions(user=user) if row.get("name")
	}


def course_query(user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not is_teacher_user(resolved):
		return institution_course_query(resolved)
	courses = assigned_courses(resolved)
	if not courses:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(courses))
	return f"`tabCourse`.`name` in ({values})"


def topic_query(user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not resolved or resolved == "Guest":
		return "1=0"
	if is_teacher_user(resolved):
		courses = assigned_courses(resolved)
		if not courses:
			return "1=0"
		values = ", ".join(frappe.db.escape(value) for value in sorted(courses))
		return f"`tabTopic`.`{TOPIC_COURSE_FIELD}` in ({values})"
	if not is_branch_access_enforced() or is_privileged_curriculum_user(resolved):
		return ""
	institutions = _allowed_institutions(resolved)
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	return f"`tabTopic`.`{INSTITUTION_FIELD}` in ({values})"


def has_course_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if is_teacher_user(resolved):
		if permission_type in {"create", "delete", "submit", "cancel", "amend"}:
			return False
		courses = assigned_courses(resolved)
		if not doc:
			return bool(courses)
		return bool(doc.name in courses)
	return has_academic_institution_permission(doc, resolved, permission_type)


def has_topic_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if is_teacher_user(resolved):
		if permission_type in {"delete", "submit", "cancel", "amend"}:
			return False
		courses = assigned_courses(resolved)
		if not doc:
			return bool(courses) if permission_type in {"read", "create", "write", "report", "print"} else False
		course = doc.get(TOPIC_COURSE_FIELD)
		return bool(course and course in courses)
	if not doc:
		return bool(resolved and resolved != "Guest")
	if not is_branch_access_enforced() or is_privileged_curriculum_user(resolved):
		return True
	institution = doc.get(INSTITUTION_FIELD)
	return bool(institution and institution in _allowed_institutions(resolved))
