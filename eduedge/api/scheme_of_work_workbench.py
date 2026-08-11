from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.api.scheme_of_work import _is_manager, get_schemes
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.curriculum_fields import (
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import assignment_capability_enforcement_enabled
from eduedge.education.instructor_scope import get_active_instructor_names_for_user, is_limited_instructor_user
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch


def _label_rows(rows, value_field: str, label_field: str) -> list[dict]:
	return [
		{
			"value": row.get(value_field),
			"label": row.get(label_field) or row.get(value_field),
			**{key: value for key, value in dict(row).items() if key not in {value_field, label_field}},
		}
		for row in rows
		if row.get(value_field)
	]


def _assignment_rows(branch: str) -> list[dict]:
	if not is_limited_instructor_user():
		return []
	instructors = get_active_instructor_names_for_user()
	if len(instructors) != 1:
		return []
	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters={
			"instructor": instructors[0],
			"school_branch": branch,
			"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
			"enabled": 1,
		},
		fields=[
			"name", "program_offering", "assignment_scope", "student_group", "course",
			"valid_from", "valid_to", "can_view_subject_content", "can_manage_subject_topics",
		],
		limit_page_length=0,
	)
	today = getdate(nowdate())
	return [dict(row) for row in rows if not row.valid_to or getdate(row.valid_to) >= today]


def _offering_options(branch: str, assignments: list[dict]) -> list[dict]:
	filters = {"school_branch": branch, "is_active": 1}
	if is_limited_instructor_user():
		names = sorted({row.get("program_offering") for row in assignments if row.get("program_offering")})
		filters["name"] = ["in", names or ["__none__"]]
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name", "offering_title", "program", "academic_year", "academic_term",
			"school_branch", "institution", "period_start_date", "period_end_date",
		],
		order_by="period_start_date desc, offering_title asc",
		limit_page_length=500,
	)
	return _label_rows(rows, "name", "offering_title")


def _group_options(branch: str, offering: str, assignments: list[dict]) -> list[dict]:
	if not offering:
		return []
	meta = frappe.get_meta("Student Group")
	filters = {BRANCH_FIELD: branch, "disabled": 0}
	if meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = offering
	if is_limited_instructor_user():
		offering_rows = [row for row in assignments if row.get("program_offering") == offering]
		class_wide = any((row.get("assignment_scope") or CLASS_ARM_SCOPE) == CLASS_SCOPE for row in offering_rows)
		if not class_wide:
			groups = sorted({row.get("student_group") for row in offering_rows if row.get("student_group")})
			filters["name"] = ["in", groups or ["__none__"]]
	fields = ["name", "student_group_name", BRANCH_FIELD]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	if meta.has_field("eduedge_display_name"):
		fields.append("eduedge_display_name")
	rows = frappe.get_list("Student Group", filters=filters, fields=fields, order_by="student_group_name asc", limit_page_length=500)
	return [
		{
			"value": row.name,
			"label": row.get("eduedge_display_name") or row.student_group_name or row.name,
		}
		for row in rows
	]


def _course_options(offering: str, student_group: str, assignments: list[dict]) -> list[dict]:
	if not offering:
		return []
	program = frappe.db.get_value("EduEdge Program Offering", offering, "program")
	curriculum = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		order_by="idx asc",
		limit_page_length=0,
	)
	allowed = set(curriculum)
	writable: set[str] = set(curriculum)
	if is_limited_instructor_user():
		context_rows = []
		for row in assignments:
			if row.get("program_offering") != offering or row.get("course") not in allowed:
				continue
			scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
			if student_group and scope == CLASS_ARM_SCOPE and row.get("student_group") != student_group:
				continue
			if not student_group and scope == CLASS_ARM_SCOPE:
				continue
			context_rows.append(row)
		allowed = {row.get("course") for row in context_rows if row.get("course")}
		if assignment_capability_enforcement_enabled():
			allowed = {row.get("course") for row in context_rows if cint(row.get("can_view_subject_content"))}
			writable = {row.get("course") for row in context_rows if cint(row.get("can_manage_subject_topics"))}
		else:
			writable = set(allowed)
	rows = frappe.get_list(
		"Course",
		filters={"name": ["in", sorted(allowed) or ["__none__"]]},
		fields=["name", "course_name"],
		order_by="course_name asc",
		limit_page_length=500,
	)
	return [
		{"value": row.name, "label": row.course_name or row.name, "can_manage": row.name in writable}
		for row in rows
	]


def _topic_options(course: str, offering: str, student_group: str) -> list[dict]:
	if not course:
		return []
	topic_names = frappe.get_all(
		"Course Topic",
		filters={"parent": course, "parenttype": "Course", "parentfield": "topics"},
		pluck="topic",
		order_by="idx asc",
		limit_page_length=0,
	)
	if not topic_names:
		return []
	meta = frappe.get_meta("Topic")
	fields = ["name", "topic_name", "description"]
	for fieldname in (TOPIC_SCOPE_FIELD, TOPIC_OFFERING_FIELD, TOPIC_GROUP_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list("Topic", filters={"name": ["in", topic_names]}, fields=fields, order_by="topic_name asc", limit_page_length=500)
	visible = []
	for row in rows:
		scope = row.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
		if scope == TOPIC_SCOPE_CLASS and row.get(TOPIC_OFFERING_FIELD) != offering:
			continue
		if scope == TOPIC_SCOPE_CLASS_ARM and (
			row.get(TOPIC_OFFERING_FIELD) != offering or row.get(TOPIC_GROUP_FIELD) != student_group
		):
			continue
		visible.append({"value": row.name, "label": row.topic_name or row.name, "description": row.description or "", "scope": scope})
	return visible


@frappe.whitelist()
def get_scheme_workbench(
	school_branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	status: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	require_eduedge_access(feature_key="academics", action="view_scheme_of_work")
	branches = get_allowed_school_branches() or []
	branch_names = {row.get("name") for row in branches if row.get("name")}
	current = get_current_school_branch() or {}
	branch = str(school_branch or current.get("name") or "").strip()
	if not branch and len(branch_names) == 1:
		branch = next(iter(branch_names))
	if not branch or branch not in branch_names:
		frappe.throw(_("Select a permitted Branch / Campus."), frappe.PermissionError)
	assert_branch_access(branch)
	assignments = _assignment_rows(branch)
	offerings = _offering_options(branch, assignments)
	offering_names = {row["value"] for row in offerings}
	offering = str(program_offering or "").strip()
	if offering and offering not in offering_names:
		frappe.throw(_("Select a permitted Class / Programme Offering."), frappe.PermissionError)
	groups = _group_options(branch, offering, assignments)
	group_names = {row["value"] for row in groups}
	group = str(student_group or "").strip()
	if group and group not in group_names:
		frappe.throw(_("Select a permitted Class Arm / Student Group."), frappe.PermissionError)
	courses = _course_options(offering, group, assignments)
	course_names = {row["value"] for row in courses}
	subject = str(course or "").strip()
	if subject and subject not in course_names:
		frappe.throw(_("Select a permitted Subject / Course."), frappe.PermissionError)
	topics = _topic_options(subject, offering, group)
	schemes = get_schemes(
		school_branch=branch,
		program_offering=offering or None,
		student_group=group or None,
		course=subject or None,
		status=status or None,
		start=start,
		page_length=page_length,
	)
	selected_course = next((row for row in courses if row["value"] == subject), None)
	return {
		"filters": {
			"school_branch": branch,
			"program_offering": offering,
			"student_group": group,
			"course": subject,
			"status": status or "",
		},
		"allowed_branches": branches,
		"offerings": offerings,
		"groups": groups,
		"courses": courses,
		"topics": topics,
		"schemes": schemes.get("rows") or [],
		"paging": {"start": cint(start), "page_length": min(max(cint(page_length) or 25, 1), 50), "has_more": bool(schemes.get("has_more"))},
		"permissions": {
			"is_manager": _is_manager(),
			"is_limited_instructor": is_limited_instructor_user(),
			"can_create_in_context": bool(subject and (selected_course or {}).get("can_manage", _is_manager())),
		},
	}
