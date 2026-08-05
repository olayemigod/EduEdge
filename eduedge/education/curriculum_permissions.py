from __future__ import annotations

import frappe

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_permissions import course_query as institution_course_query
from eduedge.education.academic_permissions import has_academic_institution_permission
from eduedge.education.curriculum_fields import (
	TOPIC_COURSE_FIELD,
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
)
from eduedge.education.teaching_assignments import (
	active_assignment_rows,
	assigned_course_rows,
	assigned_courses,
	current_user_instructors,
)
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


def _allowed_institutions(user: str) -> set[str]:
	return {row.get("name") for row in get_allowed_institutions(user=user) if row.get("name")}


def _sql_values(values: set[str] | list[str]) -> str:
	return ", ".join(frappe.db.escape(value) for value in sorted(set(values)))


def course_query(user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not is_teacher_user(resolved):
		return institution_course_query(resolved)
	courses = assigned_courses(resolved)
	if not courses:
		return "1=0"
	return f"`tabCourse`.`name` in ({_sql_values(courses)})"


def _topic_assignment_conditions(user: str) -> list[str]:
	conditions: list[str] = []
	for row in active_assignment_rows(user):
		if not row.get("course"):
			continue
		course = frappe.db.escape(row.course)
		offering = frappe.db.escape(row.program_offering)
		global_clause = (
			f"(`tabTopic`.`{TOPIC_COURSE_FIELD}` = {course} "
			f"AND (`tabTopic`.`{TOPIC_SCOPE_FIELD}` = {frappe.db.escape(TOPIC_SCOPE_INSTITUTION)} "
			f"OR `tabTopic`.`{TOPIC_SCOPE_FIELD}` is null OR `tabTopic`.`{TOPIC_SCOPE_FIELD}` = ''))"
		)
		class_clause = (
			f"(`tabTopic`.`{TOPIC_COURSE_FIELD}` = {course} "
			f"AND `tabTopic`.`{TOPIC_OFFERING_FIELD}` = {offering} "
			f"AND `tabTopic`.`{TOPIC_SCOPE_FIELD}` = {frappe.db.escape(TOPIC_SCOPE_CLASS)})"
		)
		conditions.extend([global_clause, class_clause])
		if row.get("student_group"):
			conditions.append(
				f"(`tabTopic`.`{TOPIC_COURSE_FIELD}` = {course} "
				f"AND `tabTopic`.`{TOPIC_OFFERING_FIELD}` = {offering} "
				f"AND `tabTopic`.`{TOPIC_GROUP_FIELD}` = {frappe.db.escape(row.student_group)} "
				f"AND `tabTopic`.`{TOPIC_SCOPE_FIELD}` = {frappe.db.escape(TOPIC_SCOPE_CLASS_ARM)})"
			)
	return conditions


def topic_query(user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not resolved or resolved == "Guest":
		return "1=0"
	if is_teacher_user(resolved):
		conditions = _topic_assignment_conditions(resolved)
		return "(" + " OR ".join(conditions) + ")" if conditions else "1=0"
	if not is_branch_access_enforced() or is_privileged_curriculum_user(resolved):
		return ""
	institutions = _allowed_institutions(resolved)
	if not institutions:
		return "1=0"
	return f"`tabTopic`.`{INSTITUTION_FIELD}` in ({_sql_values(institutions)})"


def has_course_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if is_teacher_user(resolved):
		if permission_type in {"create", "write", "delete", "submit", "cancel", "amend", "share", "import"}:
			return False
		courses = assigned_courses(resolved)
		if not doc:
			return bool(courses)
		return bool(doc.name in courses)
	return has_academic_institution_permission(doc, resolved, permission_type)


def _topic_assignment_match(doc, user: str, *, writable: bool) -> bool:
	course = doc.get(TOPIC_COURSE_FIELD)
	if not course:
		return False
	scope = doc.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
	rows = [row for row in active_assignment_rows(user, course=course) if row.get("course") == course]
	if scope == TOPIC_SCOPE_INSTITUTION:
		return bool(rows) and not writable
	offering = doc.get(TOPIC_OFFERING_FIELD)
	for row in rows:
		if row.get("program_offering") != offering:
			continue
		if scope == TOPIC_SCOPE_CLASS:
			return True
		if scope == TOPIC_SCOPE_CLASS_ARM and row.get("student_group") == doc.get(TOPIC_GROUP_FIELD):
			return True
	return False


def has_topic_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if is_teacher_user(resolved):
		if permission_type in {"delete", "submit", "cancel", "amend", "share", "import"}:
			return False
		if not doc:
			return bool(active_assignment_rows(resolved)) if permission_type in {"read", "create", "write", "report", "print"} else False
		return _topic_assignment_match(doc, resolved, writable=permission_type in {"write", "create"})
	if not doc:
		return bool(resolved and resolved != "Guest")
	if not is_branch_access_enforced() or is_privileged_curriculum_user(resolved):
		return True
	institution = doc.get(INSTITUTION_FIELD)
	return bool(institution and institution in _allowed_institutions(resolved))
