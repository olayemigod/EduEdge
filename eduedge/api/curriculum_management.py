from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.curriculum_fields import (
	TOPIC_COURSE_FIELD,
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
)
from eduedge.education.curriculum_permissions import is_curriculum_manager, is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	active_assignment_rows,
	has_course_assignment,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_PAGE_LENGTH = 100


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid curriculum payload is required."), frappe.ValidationError)
	return payload


def _list_payload(value) -> list[dict]:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, list):
		return []
	return [dict(row or {}) for row in value if isinstance(row, dict)]


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


def _offerings(branch: str) -> list[dict]:
	return frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "is_active": 1},
		fields=[
			"name", "offering_title", "offering_code", "institution", "school_branch", "program",
			"academic_year", "academic_term", "student_batch",
		],
		order_by="academic_year desc, offering_title asc",
		limit_page_length=500,
	)


def _groups(branch: str, offering: str | None) -> list[dict]:
	filters: dict[str, Any] = {BRANCH_FIELD: branch, "disabled": 0}
	meta = frappe.get_meta("Student Group")
	if offering and meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = offering
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD]
	for fieldname in ("eduedge_display_name", OFFERING_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return frappe.get_list(
		"Student Group",
		filters=filters,
		fields=fields,
		order_by="student_group_name asc",
		limit_page_length=500,
	)


def _resolve_context(branch: str, offering: str | None, student_group: str | None) -> tuple[dict | None, dict | None, list[dict], list[dict]]:
	offerings = _offerings(branch)
	selected_offering = next((row for row in offerings if row.name == offering), None) if offering else None
	if offering and not selected_offering:
		frappe.throw(_("The selected Class / Programme Offering is not available in this Branch."), frappe.PermissionError)
	groups = _groups(branch, offering)
	selected_group = next((row for row in groups if row.name == student_group), None) if student_group else None
	if student_group and not selected_group:
		frappe.throw(_("The selected Class Arm is not available in this Class and Branch."), frappe.PermissionError)
	if is_teacher_user() and not selected_offering:
		assignment_rows = active_assignment_rows(branch=branch)
		assigned_offerings = {row.program_offering for row in assignment_rows if row.get("program_offering")}
		offerings = [row for row in offerings if row.name in assigned_offerings]
	return selected_offering, selected_group, offerings, groups


def _program_courses(program: str | None) -> list[str]:
	if not program:
		return []
	return frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		order_by="idx asc",
		limit_page_length=0,
	)


def _teacher_assignment_map(branch: str, offering: str | None, group: str | None) -> dict[str, list[dict]]:
	mapping: dict[str, list[dict]] = {}
	for row in active_assignment_rows(branch=branch, program_offering=offering, student_group=group):
		if row.get("course"):
			mapping.setdefault(row.course, []).append(dict(row))
	return mapping


def _course_names(institution: str, offering: dict | None, teacher_map: dict[str, list[dict]]) -> list[str] | None:
	if is_teacher_user():
		return sorted(teacher_map)
	if offering:
		return _program_courses(offering.get("program"))
	return None


def _course_topics(course: str, offering: str | None, group: str | None) -> list[dict]:
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
	fields = ["name", "topic_name", "description", TOPIC_COURSE_FIELD, INSTITUTION_FIELD, "modified"]
	for fieldname in (TOPIC_SCOPE_FIELD, TOPIC_OFFERING_FIELD, TOPIC_GROUP_FIELD):
		if frappe.get_meta("Topic").has_field(fieldname):
			fields.append(fieldname)
	details = {
		row.name: row
		for row in frappe.get_all(
			"Topic",
			filters={"name": ["in", names]},
			fields=fields,
			limit_page_length=0,
		)
	}
	result: list[dict] = []
	for link in links:
		row = details.get(link.topic)
		if not row:
			continue
		scope = row.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
		visible = scope == TOPIC_SCOPE_INSTITUTION
		if scope == TOPIC_SCOPE_CLASS and offering and row.get(TOPIC_OFFERING_FIELD) == offering:
			visible = True
		if scope == TOPIC_SCOPE_CLASS_ARM and group and row.get(TOPIC_OFFERING_FIELD) == offering and row.get(TOPIC_GROUP_FIELD) == group:
			visible = True
		if not visible:
			continue
		payload = {**dict(link), **dict(row), "link_name": link.name, "scope": scope}
		payload["can_manage"] = _topic_can_manage(payload, course, offering, group)
		result.append(payload)
	return result


def _topic_can_manage(topic: dict, course: str, offering: str | None, group: str | None) -> bool:
	if is_curriculum_manager():
		return True
	if not is_teacher_user():
		return False
	scope = topic.get(TOPIC_SCOPE_FIELD) or topic.get("scope") or TOPIC_SCOPE_INSTITUTION
	if scope == TOPIC_SCOPE_INSTITUTION:
		return False
	return has_course_assignment(course, branch=frappe.db.get_value("EduEdge Program Offering", offering, "school_branch") if offering else None, program_offering=offering, student_group=group)


def _course_detail(name: str, institution: str, branch: str, offering: str | None, group: str | None) -> dict:
	doc = frappe.get_doc("Course", name)
	doc.check_permission("read")
	if doc.get(INSTITUTION_FIELD) != institution:
		frappe.throw(_("The selected Subject / Course does not belong to this Institution."), frappe.PermissionError)
	result = doc.as_dict(no_nulls=False)
	result["assessment_criteria"] = [
		{"assessment_criteria": row.assessment_criteria, "weightage": flt(row.weightage)}
		for row in doc.get("assessment_criteria") or []
	]
	result["topics"] = _course_topics(doc.name, offering, group)
	result["can_manage_master"] = is_curriculum_manager()
	result["assignments"] = [
		dict(row)
		for row in active_assignment_rows(branch=branch, program_offering=offering, student_group=group, course=doc.name)
	]
	return result


def _topic_detail(name: str, course: str, branch: str, offering: str | None, group: str | None) -> dict:
	doc = frappe.get_doc("Topic", name)
	doc.check_permission("read")
	if doc.get(TOPIC_COURSE_FIELD) and doc.get(TOPIC_COURSE_FIELD) != course:
		frappe.throw(_("The selected Topic belongs to another Subject / Course."), frappe.PermissionError)
	if not frappe.db.exists("Course Topic", {"parent": course, "topic": name}):
		frappe.throw(_("The selected Topic is not linked to this Subject / Course."), frappe.PermissionError)
	result = doc.as_dict(no_nulls=False)
	result["scope"] = doc.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
	result["can_manage"] = _topic_can_manage(result, course, offering, group)
	return result


def _assessment_options(institution: str) -> tuple[list[dict], list[dict]]:
	grading_filters = {INSTITUTION_FIELD: institution} if frappe.get_meta("Grading Scale").has_field(INSTITUTION_FIELD) else {}
	grading_scales = frappe.get_list(
		"Grading Scale",
		filters=grading_filters,
		fields=["name", "grading_scale_name"],
		order_by="grading_scale_name asc",
		limit_page_length=500,
	) if frappe.has_permission("Grading Scale", "read") else []
	criteria = frappe.get_list(
		"Assessment Criteria",
		fields=["name", "assessment_criteria", "assessment_criteria_group"],
		order_by="assessment_criteria asc",
		limit_page_length=1000,
	) if frappe.has_permission("Assessment Criteria", "read") else []
	return grading_scales, criteria


@frappe.whitelist()
def get_curriculum_page(
	branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	topic: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to view Subjects / Courses."), frappe.PermissionError)
	resolved, selected, allowed = _resolve_branch(branch)
	institution = selected.get("institution")
	selected_offering, selected_group, offerings, groups = _resolve_context(resolved, program_offering, student_group)
	teacher_map = _teacher_assignment_map(resolved, program_offering, student_group) if is_teacher_user() else {}
	course_names = _course_names(institution, selected_offering, teacher_map)
	filters: dict[str, Any] = {INSTITUTION_FIELD: institution}
	if course_names is not None:
		filters["name"] = ["in", course_names] if course_names else ["in", ["__none__"]]
	if str(search or "").strip():
		filters["course_name"] = ["like", f"%{str(search).strip()}%"]
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	rows = frappe.get_list(
		"Course",
		filters=filters,
		fields=["name", "course_name", "department", "description", "default_grading_scale", INSTITUTION_FIELD, "modified"],
		order_by="course_name asc",
		start=start,
		page_length=length + 1,
	)
	has_more = len(rows) > length
	rows = rows[:length]
	for row in rows:
		row["assignments"] = teacher_map.get(row.name, [])
		row["can_manage_master"] = is_curriculum_manager()
	selected_course = str(course or "").strip()
	if selected_course and selected_course not in {row.name for row in rows}:
		frappe.throw(_("This Subject / Course is not available in the selected Class context."), frappe.PermissionError)
	course_detail = _course_detail(selected_course, institution, resolved, program_offering, student_group) if selected_course else None
	topic_detail = _topic_detail(topic, selected_course, resolved, program_offering, student_group) if topic and selected_course else None
	departments = frappe.get_list(
		"Department",
		filters={INSTITUTION_FIELD: institution} if frappe.get_meta("Department").has_field(INSTITUTION_FIELD) else {},
		fields=["name", "department_name"],
		order_by="department_name asc",
		limit_page_length=500,
	)
	grading_scales, assessment_criteria = _assessment_options(institution)
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"offerings": offerings,
		"selected_offering": selected_offering,
		"groups": groups,
		"selected_group": selected_group,
		"courses": rows,
		"course": course_detail,
		"topic": topic_detail,
		"departments": departments,
		"grading_scales": grading_scales,
		"assessment_criteria_options": assessment_criteria,
		"topic_scopes": [TOPIC_SCOPE_INSTITUTION, TOPIC_SCOPE_CLASS, TOPIC_SCOPE_CLASS_ARM] if is_curriculum_manager() else [TOPIC_SCOPE_CLASS, TOPIC_SCOPE_CLASS_ARM],
		"permissions": {
			"is_manager": is_curriculum_manager(),
			"is_assigned_teacher": is_teacher_user(),
			"can_create_course": is_curriculum_manager() and frappe.has_permission("Course", "create"),
			"can_write_course": is_curriculum_manager() and frappe.has_permission("Course", "write"),
			"can_create_topic": frappe.has_permission("Topic", "create"),
			"can_write_topic": frappe.has_permission("Topic", "write"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


def _validate_assessment_rows(rows: list[dict]) -> list[dict]:
	result: list[dict] = []
	seen: set[str] = set()
	for row in rows:
		criterion = str(row.get("assessment_criteria") or "").strip()
		if not criterion:
			continue
		if criterion in seen:
			frappe.throw(_("Assessment Criteria cannot be repeated."), frappe.ValidationError)
		if not frappe.db.exists("Assessment Criteria", criterion):
			frappe.throw(_("Select a valid Assessment Criteria."), frappe.ValidationError)
		weightage = flt(row.get("weightage"))
		if weightage <= 0:
			frappe.throw(_("Assessment Criteria weightage must be greater than zero."), frappe.ValidationError)
		seen.add(criterion)
		result.append({"assessment_criteria": criterion, "weightage": weightage})
	if result and abs(sum(row["weightage"] for row in result) - 100) > 0.001:
		frappe.throw(_("Assessment Criteria weightage must total 100%."), frappe.ValidationError)
	return result


@frappe.whitelist(methods=["POST"])
def save_course(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_course")
	if not is_curriculum_manager():
		frappe.throw(_("Only authorised academic managers can change Institution-wide Subject / Course masters and grading governance."), frappe.PermissionError)
	data = _parse_payload(payload)
	branch, selected, _allowed = _resolve_branch(data.get("branch"))
	institution = selected.get("institution")
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Course", name)
		doc.check_permission("write")
		if doc.get(INSTITUTION_FIELD) != institution:
			frappe.throw(_("The selected Subject / Course does not belong to this Institution."), frappe.PermissionError)
	else:
		if not frappe.has_permission("Course", "create"):
			frappe.throw(_("You are not permitted to create a new Subject / Course."), frappe.PermissionError)
		doc = frappe.new_doc("Course")
	course_name = str(data.get("course_name") or "").strip()
	if not course_name:
		frappe.throw(_("Subject / Course Name is required."), frappe.ValidationError)
	doc.course_name = course_name
	department = str(data.get("department") or "").strip()
	if department:
		department_institution = frappe.db.get_value("Department", department, INSTITUTION_FIELD)
		if department_institution and department_institution != institution:
			frappe.throw(_("Department / School Section must belong to the selected Institution."), frappe.ValidationError)
	doc.department = department or None
	doc.set(INSTITUTION_FIELD, institution)
	doc.description = data.get("description") or ""
	grading_scale = str(data.get("default_grading_scale") or "").strip()
	if grading_scale and not frappe.db.exists("Grading Scale", grading_scale):
		frappe.throw(_("Select a valid Default Grading Scale."), frappe.ValidationError)
	doc.default_grading_scale = grading_scale or None
	doc.set("assessment_criteria", [])
	for row in _validate_assessment_rows(_list_payload(data.get("assessment_criteria"))):
		doc.append("assessment_criteria", row)
	doc.save()
	return _course_detail(doc.name, institution, branch, data.get("program_offering"), data.get("student_group"))


def _ensure_course_topic_link(course: str, topic: str) -> None:
	if frappe.db.exists("Course Topic", {"parent": course, "parenttype": "Course", "topic": topic}):
		return
	course_doc = frappe.get_doc("Course", course)
	if is_teacher_user():
		frappe.flags.in_eduedge_topic_link_update = True
	try:
		course_doc.append("topics", {"topic": topic})
		course_doc.save()
	finally:
		frappe.flags.in_eduedge_topic_link_update = False


@frappe.whitelist(methods=["POST"])
def save_topic(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_topic")
	data = _parse_payload(payload)
	branch, selected, _allowed = _resolve_branch(data.get("branch"))
	course = str(data.get("course") or "").strip()
	if not course:
		frappe.throw(_("Select a Subject / Course before managing Topics."), frappe.ValidationError)
	course_doc = frappe.get_doc("Course", course)
	course_doc.check_permission("read")
	institution = selected.get("institution")
	if course_doc.get(INSTITUTION_FIELD) != institution:
		frappe.throw(_("Subject / Course and Branch must belong to the same Institution."), frappe.ValidationError)
	offering = str(data.get("program_offering") or "").strip() or None
	group = str(data.get("student_group") or "").strip() or None
	scope = str(data.get("scope") or TOPIC_SCOPE_INSTITUTION).strip()
	if is_teacher_user():
		if not offering:
			frappe.throw(_("Select the assigned Class before managing Topics."), frappe.ValidationError)
		if group and has_course_assignment(course, branch=branch, program_offering=offering, student_group=group):
			scope = TOPIC_SCOPE_CLASS_ARM
		elif has_course_assignment(course, branch=branch, program_offering=offering):
			scope = TOPIC_SCOPE_CLASS
		else:
			frappe.throw(_("This Subject / Course is not assigned to you for the selected Class or Class Arm."), frappe.PermissionError)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Topic", name)
		doc.check_permission("write")
		owner_course = doc.get(TOPIC_COURSE_FIELD)
		if owner_course and owner_course != course:
			frappe.throw(_("This Topic is governed by another Subject / Course."), frappe.PermissionError)
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
	doc.set(TOPIC_SCOPE_FIELD, scope)
	doc.set(TOPIC_OFFERING_FIELD, offering if scope != TOPIC_SCOPE_INSTITUTION else None)
	doc.set(TOPIC_GROUP_FIELD, group if scope == TOPIC_SCOPE_CLASS_ARM else None)
	doc.save()
	_ensure_course_topic_link(course, doc.name)
	return _topic_detail(doc.name, course, branch, offering, group)
