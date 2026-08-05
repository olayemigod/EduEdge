from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.curriculum_fields import TOPIC_COURSE_FIELD
from eduedge.education.curriculum_permissions import (
	assigned_course_rows,
	assigned_courses,
	is_curriculum_manager,
	is_teacher_user,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_PAGE_LENGTH = 100


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid curriculum payload is required."), frappe.ValidationError)
	return payload


def _allowed_branches() -> list[dict]:
	result: list[dict] = []
	for source in get_allowed_school_branches() or []:
		row = dict(source)
		name = str(row.get("name") or "").strip()
		if not name:
			continue
		details = frappe.db.get_value(
			"EduEdge School Branch",
			name,
			["branch_name", "institution", "enabled"],
			as_dict=True,
		) or {}
		row.update(details)
		if not cint(row.get("enabled", 1)):
			continue
		if row.get("institution"):
			institution = frappe.db.get_value(
				"EduEdge Institution",
				row["institution"],
				["institution_name", "institution_type"],
				as_dict=True,
			) or {}
			row.update(institution)
		result.append(row)
	return result


def _resolve_branch(branch: str | None) -> tuple[str, dict, list[dict]]:
	allowed = _allowed_branches()
	by_name = {row["name"]: row for row in allowed}
	resolved = str(branch or "").strip()
	if not resolved:
		resolved = str((get_current_school_branch() or {}).get("name") or "").strip()
	if not resolved and len(allowed) == 1:
		resolved = allowed[0]["name"]
	if not resolved:
		frappe.throw(_("Select a permitted School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(resolved)
	if resolved not in by_name:
		frappe.throw(_("The selected Branch is not available to your user."), frappe.PermissionError)
	return resolved, by_name[resolved], allowed


def _course_can_manage(course: str, branch: str | None = None) -> bool:
	return is_curriculum_manager() or course in assigned_courses(branch=branch)


def _teacher_assignment_map(branch: str | None = None) -> dict[str, list[dict]]:
	mapping: dict[str, list[dict]] = {}
	for row in assigned_course_rows(branch=branch):
		mapping.setdefault(row.course, []).append(row)
	return mapping


def _course_detail(name: str, branch: str) -> dict:
	doc = frappe.get_doc("Course", name)
	doc.check_permission("read")
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if doc.get(INSTITUTION_FIELD) != institution:
		frappe.throw(_("The selected Course / Subject does not belong to this Institution."), frappe.PermissionError)
	result = doc.as_dict(no_nulls=False)
	result["can_manage"] = _course_can_manage(doc.name, branch)
	result["can_edit_identity"] = is_curriculum_manager()
	result["topics"] = _course_topics(doc.name)
	return result


def _course_topics(course: str) -> list[dict]:
	links = frappe.get_all(
		"Course Topic",
		filters={"parent": course, "parenttype": "Course"},
		fields=["name", "topic", "topic_name", "idx"],
		order_by="idx asc",
		limit_page_length=0,
	)
	if not links:
		return []
	names = [row.topic for row in links if row.topic]
	details = {
		row.name: row
		for row in frappe.get_all(
			"Topic",
			filters={"name": ["in", names]},
			fields=["name", "topic_name", "description", TOPIC_COURSE_FIELD, INSTITUTION_FIELD, "modified"],
			limit_page_length=0,
		)
	}
	return [
		{
			**dict(row),
			**dict(details.get(row.topic) or {}),
			"link_name": row.name,
		}
		for row in links
		if row.topic in details
	]


def _topic_detail(name: str, course: str, branch: str) -> dict:
	doc = frappe.get_doc("Topic", name)
	doc.check_permission("read")
	if doc.get(TOPIC_COURSE_FIELD) and doc.get(TOPIC_COURSE_FIELD) != course:
		frappe.throw(_("The selected Topic belongs to another Course / Subject."), frappe.PermissionError)
	if not frappe.db.exists("Course Topic", {"parent": course, "topic": name}):
		frappe.throw(_("The selected Topic is not linked to this Course / Subject."), frappe.PermissionError)
	result = doc.as_dict(no_nulls=False)
	result["can_manage"] = _course_can_manage(course, branch)
	return result


@frappe.whitelist()
def get_curriculum_page(
	branch: str | None = None,
	course: str | None = None,
	topic: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to view Courses / Subjects."), frappe.PermissionError)
	resolved, selected, allowed = _resolve_branch(branch)
	institution = selected.get("institution")
	teacher_map = _teacher_assignment_map(resolved) if is_teacher_user() else {}
	filters: dict[str, Any] = {INSTITUTION_FIELD: institution}
	if is_teacher_user():
		course_names = sorted(teacher_map)
		if not course_names:
			rows = []
		else:
			filters["name"] = ["in", course_names]
			rows = None
	else:
		rows = None
	if str(search or "").strip():
		filters["course_name"] = ["like", f"%{str(search).strip()}%"]
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	if rows is None:
		rows = frappe.get_list(
			"Course",
			filters=filters,
			fields=["name", "course_name", "department", "description", INSTITUTION_FIELD, "modified"],
			order_by="course_name asc",
			start=start,
			page_length=length + 1,
		)
	has_more = len(rows) > length
	rows = rows[:length]
	for row in rows:
		row["can_manage"] = _course_can_manage(row.name, resolved)
		row["assignments"] = teacher_map.get(row.name, [])
	selected_course = str(course or "").strip()
	if selected_course and selected_course not in {row.name for row in rows}:
		if is_teacher_user() and selected_course not in teacher_map:
			frappe.throw(_("This Course / Subject is not actively assigned to you."), frappe.PermissionError)
	course_detail = _course_detail(selected_course, resolved) if selected_course else None
	topic_detail = _topic_detail(topic, selected_course, resolved) if topic and selected_course else None
	departments = frappe.get_list(
		"Department",
		filters={INSTITUTION_FIELD: institution} if frappe.get_meta("Department").has_field(INSTITUTION_FIELD) else {},
		fields=["name", "department_name"],
		order_by="department_name asc",
		limit_page_length=500,
	)
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"courses": rows,
		"course": course_detail,
		"topic": topic_detail,
		"departments": departments,
		"permissions": {
			"is_manager": is_curriculum_manager(),
			"is_assigned_teacher": is_teacher_user(),
			"can_create_course": is_curriculum_manager() and frappe.has_permission("Course", "create"),
			"can_write_course": frappe.has_permission("Course", "write"),
			"can_create_topic": frappe.has_permission("Topic", "create"),
			"can_write_topic": frappe.has_permission("Topic", "write"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


@frappe.whitelist(methods=["POST"])
def save_course(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_course")
	data = _parse_payload(payload)
	branch, selected, _allowed = _resolve_branch(data.get("branch"))
	institution = selected.get("institution")
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Course", name)
		doc.check_permission("write")
		if doc.get(INSTITUTION_FIELD) != institution:
			frappe.throw(_("The selected Course / Subject does not belong to this Institution."), frappe.PermissionError)
		if not _course_can_manage(doc.name, branch):
			frappe.throw(_("This Course / Subject is not actively assigned to you."), frappe.PermissionError)
	else:
		if not is_curriculum_manager() or not frappe.has_permission("Course", "create"):
			frappe.throw(_("Only authorised academic managers can create a new Course / Subject."), frappe.PermissionError)
		doc = frappe.new_doc("Course")
	if is_curriculum_manager():
		course_name = str(data.get("course_name") or "").strip()
		if not course_name:
			frappe.throw(_("Course / Subject Name is required."), frappe.ValidationError)
		doc.course_name = course_name
		department = str(data.get("department") or "").strip()
		if department:
			department_institution = frappe.db.get_value("Department", department, INSTITUTION_FIELD)
			if department_institution and department_institution != institution:
				frappe.throw(_("Department / School Section must belong to the selected Institution."), frappe.ValidationError)
		doc.department = department or None
		doc.set(INSTITUTION_FIELD, institution)
	doc.description = data.get("description") or ""
	doc.save()
	return _course_detail(doc.name, branch)


def _ensure_course_topic_link(course: str, topic: str) -> None:
	if frappe.db.exists("Course Topic", {"parent": course, "parenttype": "Course", "topic": topic}):
		return
	course_doc = frappe.get_doc("Course", course)
	course_doc.check_permission("write")
	course_doc.append("topics", {"topic": topic})
	course_doc.save()


@frappe.whitelist(methods=["POST"])
def save_topic(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_topic")
	data = _parse_payload(payload)
	branch, selected, _allowed = _resolve_branch(data.get("branch"))
	course = str(data.get("course") or "").strip()
	if not course:
		frappe.throw(_("Select a Course / Subject before managing Topics."), frappe.ValidationError)
	course_doc = frappe.get_doc("Course", course)
	course_doc.check_permission("read")
	institution = selected.get("institution")
	if course_doc.get(INSTITUTION_FIELD) != institution:
		frappe.throw(_("Course / Subject and Branch must belong to the same Institution."), frappe.ValidationError)
	if not _course_can_manage(course, branch):
		frappe.throw(_("You can manage Topics only for Courses / Subjects actively assigned to you."), frappe.PermissionError)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Topic", name)
		doc.check_permission("write")
		owner_course = doc.get(TOPIC_COURSE_FIELD)
		if owner_course and owner_course != course:
			frappe.throw(_("This Topic is governed by another Course / Subject."), frappe.PermissionError)
	else:
		if not frappe.has_permission("Topic", "create"):
			frappe.throw(_("You are not permitted to create Topics."), frappe.PermissionError)
		doc = frappe.new_doc("Topic")
		topic_name = str(data.get("topic_name") or "").strip()
		if not topic_name:
			frappe.throw(_("Topic Name is required."), frappe.ValidationError)
		doc.topic_name = topic_name
	if is_curriculum_manager() and not name:
		doc.topic_name = str(data.get("topic_name") or "").strip()
	doc.description = data.get("description") or ""
	doc.set(TOPIC_COURSE_FIELD, course)
	doc.set(INSTITUTION_FIELD, institution)
	doc.save()
	_ensure_course_topic_link(course, doc.name)
	return _topic_detail(doc.name, course, branch)
