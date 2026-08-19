from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.api import academic_readiness as readiness
from eduedge.api.instructor_assignment_link_search import (
	search_assignment_courses,
	search_instructors,
)
from eduedge.api.instructor_assignments import save_instructor_assignment_batch
from eduedge.api.programme_curriculum_governance import add_programme_courses
from eduedge.api.session_launch import _allowed_branches, _get_launch_by_name, _require_manager
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE

MAX_TEACHING_CONTEXTS = 3000
MAX_SCHEDULE_ROWS = 5000
CLASS_RESPONSIBILITY_TYPES = ("Class Teacher", "Form Teacher")
CLASS_RESPONSIBILITY_INSTITUTION_TYPES = {"PRIMARY", "SECONDARY"}


def _normalise(value: Any) -> str:
	return " ".join(str(value or "").split())


def _launch(launch: str, action: str):
	_require_manager(action)
	doc = _get_launch_by_name(_normalise(launch))
	if doc.status == "Closed":
		frappe.throw(_("This Session Launch is closed and cannot be changed."), frappe.ValidationError)
	return doc


def _institution_type(institution: str) -> str:
	return _normalise(frappe.db.get_value("EduEdge Institution", institution, "institution_type")).upper()


def _subject_assignment_type(institution_type: str) -> str:
	if institution_type in {"TERTIARY", "UNIVERSITY", "COLLEGE", "POLYTECHNIC"}:
		return "Lecturer"
	if institution_type in {"TRAINING", "VOCATIONAL", "PROFESSIONAL"}:
		return "Tutor"
	return "Subject Instructor"


def _session_dates(academic_year: str) -> tuple[str, str]:
	row = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	) or {}
	if not row.get("year_start_date") or not row.get("year_end_date"):
		frappe.throw(_("The target Academic Session must have start and end dates."), frappe.ValidationError)
	return str(getdate(row.year_start_date)), str(getdate(row.year_end_date))


def _branch_assignment_rows(branch: str, offering_names: set[str]) -> list[dict]:
	if not offering_names or not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
		return []
	rows = frappe.get_list(
		"EduEdge Instructor Assignment",
		filters={
			"school_branch": branch,
			"program_offering": ["in", sorted(offering_names)],
			"enabled": 1,
		},
		fields=[
			"name",
			"assignment_title",
			"instructor",
			"instructor_name",
			"assignment_type",
			"assignment_scope",
			"program_offering",
			"student_group",
			"course",
			"valid_from",
			"valid_to",
		],
		page_length=MAX_TEACHING_CONTEXTS,
	)
	return [dict(row) for row in rows]


def _schedule_rows(branch: str, groups: list[dict], academic_year: str) -> tuple[list[dict], bool]:
	group_names = sorted({row.get("name") for row in groups if row.get("name")})
	if not group_names or not frappe.has_permission("Course Schedule", "read"):
		return [], False
	start_date, end_date = _session_dates(academic_year)
	rows = frappe.get_list(
		"Course Schedule",
		filters={
			BRANCH_FIELD: branch,
			"student_group": ["in", group_names],
			"schedule_date": ["between", [start_date, end_date]],
		},
		fields=[
			"name",
			"student_group",
			"course",
			"instructor",
			"instructor_name",
			"room",
			"schedule_date",
			"from_time",
			"to_time",
		],
		order_by="schedule_date asc, from_time asc",
		page_length=MAX_SCHEDULE_ROWS,
	)
	return [dict(row) for row in rows], len(rows) >= MAX_SCHEDULE_ROWS


def _curriculum_rows(offerings: list[dict], program_courses: dict[str, list[str]], labels: dict[str, str]) -> list[dict]:
	result = []
	for offering in offerings:
		courses = list(program_courses.get(offering.get("program"), []))
		result.append(
			{
				"branch": offering.get("school_branch") or "",
				"program_offering": offering["name"],
				"offering_label": offering.get("offering_title") or offering["name"],
				"program": offering.get("program") or "",
				"courses": [
					{"name": course, "label": labels.get(course, course)}
					for course in courses
				],
				"course_count": len(courses),
				"ready": bool(courses),
			}
		)
	return result


def _teaching_context_rows(
	contexts: list[dict],
	assignments: list[dict],
	schemes: list[dict],
	schedule_rows: list[dict],
) -> list[dict]:
	assignment_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
	for row in assignments:
		if row.get("course"):
			assignment_index[(row.get("program_offering"), row.get("course"))].append(row)

	schedule_index: dict[tuple[str, str], list[dict]] = defaultdict(list)
	for row in schedule_rows:
		if row.get("student_group") and row.get("course"):
			schedule_index[(row.get("student_group"), row.get("course"))].append(row)

	result = []
	for context in contexts:
		matched = [
			row
			for row in assignment_index.get((context["program_offering"], context["course"]), [])
			if readiness._assignment_matches_context(row, context)
		]
		scheme = readiness._select_scheme_for_context(schemes, context)
		if not scheme:
			scheme_status = "Missing"
		else:
			scheme_status = scheme.get("status") or "Missing"
		scheduled = schedule_index.get((context.get("student_group"), context["course"]), []) if context.get("student_group") else []
		result.append(
			{
				**context,
				"context_key": "::".join(
					[
						context["program_offering"],
						context.get("student_group") or "__class__",
						context["course"],
					]
				),
				"assigned": bool(matched),
				"assignments": [
					{
						"name": row.get("name"),
						"instructor": row.get("instructor"),
						"instructor_name": row.get("instructor_name") or row.get("instructor"),
						"assignment_type": row.get("assignment_type"),
					}
					for row in matched
				],
				"schedule_ready": bool(scheduled),
				"schedule_count": len(scheduled),
				"scheme_status": scheme_status,
				"scheme": (scheme or {}).get("name") or "",
			}
		)
	return result


def _responsibility_rows(groups: list[dict], assignments: list[dict], offerings: dict[str, dict]) -> list[dict]:
	by_group: dict[str, list[dict]] = defaultdict(list)
	for row in assignments:
		if row.get("assignment_type") in CLASS_RESPONSIBILITY_TYPES and row.get("student_group"):
			by_group[row["student_group"]].append(row)
	result = []
	for group in groups:
		offering = offerings.get(group.get("resolved_offering")) or {}
		period_start = offering.get("period_start_date")
		period_end = offering.get("period_end_date")
		matched = [
			row
			for row in by_group.get(group["name"], [])
			if readiness._date_overlap(row.get("valid_from"), row.get("valid_to"), period_start, period_end)
		]
		result.append(
			{
				"branch": group.get(BRANCH_FIELD) or offering.get("school_branch") or "",
				"program_offering": group.get("resolved_offering") or "",
				"offering_label": offering.get("offering_title") or group.get("program") or "",
				"student_group": group["name"],
				"student_group_label": group.get("label") or group.get("student_group_name") or group["name"],
				"assigned": bool(matched),
				"assignments": [
					{
						"name": row.get("name"),
						"instructor": row.get("instructor"),
						"instructor_name": row.get("instructor_name") or row.get("instructor"),
						"assignment_type": row.get("assignment_type"),
					}
					for row in matched
				],
			}
		)
	return result


def _branch_context(branch_row: dict, doc, institution_type: str) -> dict:
	branch = branch_row["name"]
	offerings = readiness._offering_rows(branch, academic_year=doc.academic_year, include_historical=False)
	groups = readiness._group_rows(branch, offerings, include_historical=False)
	contexts = readiness._expected_contexts(offerings, groups)
	if len(contexts) > MAX_TEACHING_CONTEXTS:
		frappe.throw(
			_("Academic Delivery has more than {0} teaching contexts in {1}. Refine the Session structure before continuing.").format(
				MAX_TEACHING_CONTEXTS, branch_row.get("branch_name") or branch
			),
			frappe.ValidationError,
		)
	offering_names = {row["name"] for row in offerings}
	assignments = _branch_assignment_rows(branch, offering_names)
	schemes = readiness._scheme_rows(branch, offering_names)
	schedules, schedule_truncated = _schedule_rows(branch, groups, doc.academic_year)
	program_courses = readiness._program_courses({row.get("program") for row in offerings if row.get("program")})
	course_names = {course for values in program_courses.values() for course in values}
	course_labels = readiness._course_labels(course_names)
	curriculum = _curriculum_rows(offerings, program_courses, course_labels)
	teaching = _teaching_context_rows(contexts, assignments, schemes, schedules)
	offering_map = {row["name"]: row for row in offerings}
	responsibilities = _responsibility_rows(groups, assignments, offering_map)
	responsibility_required = institution_type in CLASS_RESPONSIBILITY_INSTITUTION_TYPES
	return {
		"branch": branch,
		"branch_name": branch_row.get("branch_name") or branch,
		"curriculum": curriculum,
		"teaching_contexts": teaching,
		"class_responsibilities": responsibilities,
		"schedule_rows": schedules,
		"schedule_truncated": schedule_truncated,
		"summary": {
			"class_intakes": len(offerings),
			"class_arms": len(groups),
			"classes_with_subjects": sum(1 for row in curriculum if row["ready"]),
			"classes_without_subjects": sum(1 for row in curriculum if not row["ready"]),
			"expected_teaching_contexts": len(teaching),
			"assigned_teaching_contexts": sum(1 for row in teaching if row["assigned"]),
			"unassigned_teaching_contexts": sum(1 for row in teaching if not row["assigned"]),
			"scheduled_teaching_contexts": sum(1 for row in teaching if row["schedule_ready"]),
			"unscheduled_teaching_contexts": sum(1 for row in teaching if row.get("student_group") and not row["schedule_ready"]),
			"approved_scheme_contexts": sum(1 for row in teaching if row["scheme_status"] == "Approved"),
			"scheme_attention_contexts": sum(1 for row in teaching if row["scheme_status"] != "Approved"),
			"class_responsibility_required": responsibility_required,
			"class_responsibility_total": len(responsibilities),
			"class_responsibility_assigned": sum(1 for row in responsibilities if row["assigned"]),
			"class_responsibility_missing": sum(1 for row in responsibilities if not row["assigned"]),
		},
	}


def _aggregate(branches: list[dict], institution_type: str) -> dict:
	summary = {
		"class_intakes": 0,
		"class_arms": 0,
		"classes_with_subjects": 0,
		"classes_without_subjects": 0,
		"expected_teaching_contexts": 0,
		"assigned_teaching_contexts": 0,
		"unassigned_teaching_contexts": 0,
		"scheduled_teaching_contexts": 0,
		"unscheduled_teaching_contexts": 0,
		"approved_scheme_contexts": 0,
		"scheme_attention_contexts": 0,
		"class_responsibility_total": 0,
		"class_responsibility_assigned": 0,
		"class_responsibility_missing": 0,
	}
	for branch in branches:
		for key in summary:
			summary[key] += cint((branch.get("summary") or {}).get(key))
	responsibility_required = institution_type in CLASS_RESPONSIBILITY_INSTITUTION_TYPES
	subjects_ready = bool(summary["class_intakes"] and not summary["classes_without_subjects"])
	assignments_ready = bool(
		summary["expected_teaching_contexts"]
		and not summary["unassigned_teaching_contexts"]
	)
	responsibility_ready = not responsibility_required or bool(
		summary["class_responsibility_total"]
		and not summary["class_responsibility_missing"]
	)
	schedule_ready = bool(
		summary["expected_teaching_contexts"]
		and not summary["unscheduled_teaching_contexts"]
	)
	scheme_ready = bool(
		summary["expected_teaching_contexts"]
		and not summary["scheme_attention_contexts"]
	)
	return {
		**summary,
		"class_responsibility_required": responsibility_required,
		"subjects_ready": subjects_ready,
		"assignments_ready": assignments_ready,
		"class_responsibility_ready": responsibility_ready,
		"schedule_ready": schedule_ready,
		"scheme_ready": scheme_ready,
		"academic_delivery_ready": all(
			(subjects_ready, assignments_ready, responsibility_ready, schedule_ready, scheme_ready)
		),
	}


def _context(doc) -> dict:
	branches, total = _allowed_branches(doc.institution)
	institution_type = _institution_type(doc.institution)
	branch_rows = [_branch_context(row, doc, institution_type) for row in branches]
	return {
		"launch": doc.name,
		"institution": doc.institution,
		"institution_type": institution_type,
		"academic_year": doc.academic_year,
		"branches": branch_rows,
		"summary": _aggregate(branch_rows, institution_type),
		"permissions": {
			"can_manage_assignments": bool(
				frappe.has_permission("EduEdge Instructor Assignment", "create")
				or frappe.has_permission("EduEdge Instructor Assignment", "write")
			),
			"can_edit_curriculum": bool(frappe.has_permission("Program", "write")),
			"can_view_schedule": bool(frappe.has_permission("Course Schedule", "read")),
		},
		"branch_scope": {"accessible": len(branches), "institution_total": total, "complete": len(branches) == total},
		"defaults": {
			"subject_assignment_type": _subject_assignment_type(institution_type),
			"class_responsibility_type": "Class Teacher",
		},
	}


@frappe.whitelist()
def get_session_delivery_context(launch: str) -> dict:
	doc = _launch(launch, "get_session_delivery_context")
	return _context(doc)


def _validate_offering(doc, program_offering: str) -> dict:
	name = _normalise(program_offering)
	row = frappe.db.get_value(
		"EduEdge Program Offering",
		name,
		["name", "institution", "school_branch", "program", "academic_year", "academic_term", "is_active"],
		as_dict=True,
	)
	if not row or not cint(row.is_active):
		frappe.throw(_("Select an active destination Class Intake."), frappe.ValidationError)
	if row.institution != doc.institution or row.academic_year != doc.academic_year:
		frappe.throw(_("The selected Class Intake does not belong to this Session Launch."), frappe.ValidationError)
	allowed, _ = _allowed_branches(doc.institution)
	if row.school_branch not in {item["name"] for item in allowed}:
		frappe.throw(_("The selected Class Intake belongs to a Branch outside your access."), frappe.PermissionError)
	return dict(row)


@frappe.whitelist(methods=["POST"])
def add_guided_class_subject(launch: str, program_offering: str, course: str) -> dict:
	doc = _launch(launch, "add_guided_class_subject")
	offering = _validate_offering(doc, program_offering)
	result = add_programme_courses(programme=offering["program"], courses=[_normalise(course)], required=1)
	return {"result": result, "context": _context(doc)}


def _selected_teaching_contexts(doc, rows) -> list[dict]:
	selected = frappe.parse_json(rows) if isinstance(rows, str) else rows
	if not isinstance(selected, list) or not selected:
		frappe.throw(_("Select at least one teaching responsibility."), frappe.ValidationError)
	context = _context(doc)
	available = {
		row["context_key"]: row
		for branch in context["branches"]
		for row in branch["teaching_contexts"]
	}
	result = []
	seen = set()
	for item in selected:
		key = _normalise(item.get("context_key") if isinstance(item, dict) else item)
		if not key or key in seen:
			continue
		row = available.get(key)
		if not row:
			frappe.throw(_("One or more selected teaching responsibilities are no longer valid for this Session."), frappe.ValidationError)
		seen.add(key)
		result.append(row)
	return result


@frappe.whitelist(methods=["POST"])
def assign_guided_subject_instructor(
	launch: str,
	instructor: str,
	contexts,
	assignment_type: str | None = None,
) -> dict:
	doc = _launch(launch, "assign_guided_subject_instructor")
	selected = _selected_teaching_contexts(doc, contexts)
	resolved_type = _normalise(assignment_type) or _subject_assignment_type(_institution_type(doc.institution))
	rows = []
	for index, context in enumerate(selected, 1):
		rows.append(
			{
				"row_id": f"session-launch-subject-{index}",
				"row_label": f"{context['offering_label']} · {context['student_group_label']} · {context['course_label']}",
				"branch": context["school_branch"],
				"program_offering": context["program_offering"],
				"student_groups": [context["student_group"]] if context.get("student_group") else [],
				"courses": [context["course"]],
				"assignment_scope": CLASS_ARM_SCOPE if context.get("student_group") else CLASS_SCOPE,
				"assignment_type": resolved_type,
				"valid_from": str(context.get("period_start_date") or ""),
				"valid_to": str(context.get("period_end_date") or ""),
				"enabled": 1,
				"notes": _("Prepared from Academic Session Launch {0}").format(doc.name),
			}
		)
	result = save_instructor_assignment_batch({"instructor": _normalise(instructor), "rows": rows})
	return {"result": result, "context": _context(doc)}


@frappe.whitelist(methods=["POST"])
def assign_guided_class_teacher(launch: str, instructor: str, student_groups, assignment_type: str = "Class Teacher") -> dict:
	doc = _launch(launch, "assign_guided_class_teacher")
	selected = frappe.parse_json(student_groups) if isinstance(student_groups, str) else student_groups
	if not isinstance(selected, list) or not selected:
		frappe.throw(_("Select at least one Class Arm."), frappe.ValidationError)
	resolved_type = _normalise(assignment_type) or "Class Teacher"
	if resolved_type not in CLASS_RESPONSIBILITY_TYPES:
		frappe.throw(_("Select Class Teacher or Form Teacher for guided Class responsibility."), frappe.ValidationError)
	context = _context(doc)
	available = {
		row["student_group"]: row
		for branch in context["branches"]
		for row in branch["class_responsibilities"]
	}
	rows = []
	seen = set()
	for index, raw_name in enumerate(selected, 1):
		name = _normalise(raw_name)
		if not name or name in seen:
			continue
		row = available.get(name)
		if not row:
			frappe.throw(_("One or more selected Class Arms are no longer valid for this Session."), frappe.ValidationError)
		seen.add(name)
		offering = _validate_offering(doc, row["program_offering"])
		period_start, period_end = readiness.resolve_program_offering_period_dates(offering)
		rows.append(
			{
				"row_id": f"session-launch-class-{index}",
				"row_label": f"{row['offering_label']} · {row['student_group_label']} · {resolved_type}",
				"branch": row["branch"],
				"program_offering": row["program_offering"],
				"student_groups": [name],
				"courses": [],
				"assignment_scope": CLASS_ARM_SCOPE,
				"assignment_type": resolved_type,
				"valid_from": str(period_start or ""),
				"valid_to": str(period_end or ""),
				"enabled": 1,
				"notes": _("Prepared from Academic Session Launch {0}").format(doc.name),
			}
		)
	result = save_instructor_assignment_batch({"instructor": _normalise(instructor), "rows": rows})
	return {"result": result, "context": _context(doc)}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def guided_instructor_query(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	_launch(filters.get("launch"), "guided_instructor_query")
	rows = search_instructors(query=txt or "", page_length=page_len)
	return [
		[row.get("value"), row.get("label"), row.get("description") or ""]
		for row in rows
		if row.get("value")
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def guided_course_query(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	doc = _launch(filters.get("launch"), "guided_course_query")
	offering = _validate_offering(doc, filters.get("program_offering"))
	rows = search_assignment_courses(
		branch=offering["school_branch"],
		program_offering=offering["name"],
		query=txt or "",
		page_length=page_len,
	)
	return [
		[row.get("value"), row.get("label"), row.get("description") or ""]
		for row in rows
		if row.get("value") and not row.get("in_program")
	]
