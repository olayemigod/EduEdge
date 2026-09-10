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
from eduedge.education.instructor_assignment_capabilities import (
	assignment_capability_enforcement_enabled,
	get_user_capability_assignment_rows,
)
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
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


def _teacher_capability_rows(user: str, capability: str) -> list[dict]:
	return get_user_capability_assignment_rows(capability, user=user)


def _teacher_visible_courses(user: str) -> set[str]:
	if not assignment_capability_enforcement_enabled():
		return set(assigned_courses(user))
	return {
		row.get("course")
		for row in _teacher_capability_rows(user, "can_view_subject_content")
		if row.get("course")
	}


def course_query(user: str | None = None) -> str:
	resolved = user or frappe.session.user
	if not is_teacher_user(resolved):
		return institution_course_query(resolved)
	courses = _teacher_visible_courses(resolved)
	if not courses:
		return "1=0"
	return f"`tabCourse`.`name` in ({_sql_values(courses)})"


def _topic_conditions_for_rows(rows: list[dict]) -> list[str]:
	conditions: list[str] = []
	for row in rows:
		if not row.get("course") or not row.get("program_offering"):
			continue
		course = frappe.db.escape(row["course"])
		offering = frappe.db.escape(row["program_offering"])
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

		if row.get("assignment_scope") == CLASS_SCOPE:
			conditions.append(
				f"(`tabTopic`.`{TOPIC_COURSE_FIELD}` = {course} "
				f"AND `tabTopic`.`{TOPIC_OFFERING_FIELD}` = {offering} "
				f"AND `tabTopic`.`{TOPIC_SCOPE_FIELD}` = {frappe.db.escape(TOPIC_SCOPE_CLASS_ARM)})"
			)
		elif row.get("assignment_scope") == CLASS_ARM_SCOPE and row.get("student_group"):
			conditions.append(
				f"(`tabTopic`.`{TOPIC_COURSE_FIELD}` = {course} "
				f"AND `tabTopic`.`{TOPIC_OFFERING_FIELD}` = {offering} "
				f"AND `tabTopic`.`{TOPIC_GROUP_FIELD}` = {frappe.db.escape(row['student_group'])} "
				f"AND `tabTopic`.`{TOPIC_SCOPE_FIELD}` = {frappe.db.escape(TOPIC_SCOPE_CLASS_ARM)})"
			)
	return conditions


def _topic_assignment_conditions(user: str) -> list[str]:
	if assignment_capability_enforcement_enabled():
		return _topic_conditions_for_rows(_teacher_capability_rows(user, "can_view_subject_content"))
	return _topic_conditions_for_rows([dict(row) for row in active_assignment_rows(user)])


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
		if permission_type == "write" and getattr(frappe.flags, "in_eduedge_topic_link_update", False):
			return True
		if permission_type in {"create", "write", "delete", "submit", "cancel", "amend", "share", "import"}:
			return False
		courses = _teacher_visible_courses(resolved)
		if not doc:
			return bool(courses)
		return bool(doc.name in courses)
	return has_academic_institution_permission(doc, resolved, permission_type)


def _topic_match_for_rows(doc, rows: list[dict], *, writable: bool) -> bool:
	course = doc.get(TOPIC_COURSE_FIELD)
	if not course:
		return False
	scope = doc.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
	matching = [row for row in rows if row.get("course") == course]
	if scope == TOPIC_SCOPE_INSTITUTION:
		# An exact assignment may view institution-level reusable content for its
		# Subject, but limited Instructors do not edit institution-wide Topic truth.
		return bool(matching) and not writable

	offering = doc.get(TOPIC_OFFERING_FIELD)
	for row in matching:
		if row.get("program_offering") != offering:
			continue
		if scope == TOPIC_SCOPE_CLASS:
			return True
		if scope == TOPIC_SCOPE_CLASS_ARM:
			if row.get("assignment_scope") == CLASS_SCOPE:
				return True
			if row.get("assignment_scope") == CLASS_ARM_SCOPE and row.get("student_group") == doc.get(TOPIC_GROUP_FIELD):
				return True
	return False


def _topic_assignment_match(doc, user: str, *, writable: bool) -> bool:
	course = doc.get(TOPIC_COURSE_FIELD)
	if not course:
		return False
	rows = [dict(row) for row in active_assignment_rows(user, course=course) if row.get("course") == course]
	return _topic_match_for_rows(doc, rows, writable=writable)


def _topic_capability_match(doc, user: str, *, writable: bool) -> bool:
	capability = "can_manage_subject_topics" if writable else "can_view_subject_content"
	rows = _teacher_capability_rows(user, capability)
	return _topic_match_for_rows(doc, rows, writable=writable)


def has_topic_permission(doc, user=None, permission_type=None) -> bool:
	resolved = user or frappe.session.user
	if is_teacher_user(resolved):
		if permission_type in {"delete", "submit", "cancel", "amend", "share", "import"}:
			return False
		writable = permission_type in {"write", "create"}
		if assignment_capability_enforcement_enabled():
			capability = "can_manage_subject_topics" if writable else "can_view_subject_content"
			if not doc:
				return bool(_teacher_capability_rows(resolved, capability)) if permission_type in {None, "read", "create", "write", "report", "print"} else False
			return _topic_capability_match(doc, resolved, writable=writable)
		if not doc:
			return bool(active_assignment_rows(resolved)) if permission_type in {None, "read", "create", "write", "report", "print"} else False
		return _topic_assignment_match(doc, resolved, writable=writable)
	if not doc:
		return bool(resolved and resolved != "Guest")
	if not is_branch_access_enforced() or is_privileged_curriculum_user(resolved):
		return True
	institution = doc.get(INSTITUTION_FIELD)
	return bool(institution and institution in _allowed_institutions(resolved))
