from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_SCOPE,
	COURSE_REQUIRED_TYPES,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

BRANCH_ONLY_SCOPE = "Branch Access Only"
BULK_SCOPES = (BRANCH_ONLY_SCOPE, CLASS_SCOPE, CLASS_ARM_SCOPE)
ASSIGNMENT_TYPES = (
	"Class Teacher",
	"Subject Teacher",
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
	"Form Teacher",
	"Head of Class / Level",
)


@dataclass(frozen=True)
class PlannedAssignment:
	branch: str
	program_offering: str
	student_group: str | None
	course: str | None
	assignment_scope: str
	label: str


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_read() -> None:
	_require_login()
	if not frappe.has_permission("EduEdge Instructor Assignment", "read"):
		frappe.throw(_("You are not permitted to view Teacher Assignments."), frappe.PermissionError)


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid Teacher Assignment payload is required."), frappe.ValidationError)
	return payload


def _list_values(value) -> list[str]:
	if isinstance(value, str):
		try:
			parsed = frappe.parse_json(value)
			value = parsed if isinstance(parsed, list) else [value]
		except Exception:
			value = [value]
	if not isinstance(value, (list, tuple, set)):
		return []
	return sorted({str(item or "").strip() for item in value if str(item or "").strip()})


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


def _validate_branches(branches: list[str], allowed: list[dict]) -> dict[str, dict]:
	by_name = {row["name"]: row for row in allowed}
	if not branches:
		current = str((get_current_school_branch() or {}).get("name") or "").strip()
		if current:
			branches = [current]
	if not branches:
		frappe.throw(_("Select at least one Branch / Campus."), frappe.ValidationError)
	for branch in branches:
		assert_branch_access(branch)
		if branch not in by_name:
			frappe.throw(_("Branch {0} is not available to your user.").format(branch), frappe.PermissionError)
	return {branch: by_name[branch] for branch in branches}


def _instructors(institutions: set[str] | None = None) -> list[dict]:
	filters: dict[str, Any] = {"status": "Active"}
	meta = frappe.get_meta("Instructor")
	if institutions and meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = ["in", sorted(institutions)]
	fields = ["name", "instructor_name", "department", "employee"]
	for fieldname in (INSTITUTION_FIELD, "eduedge_email", "eduedge_mobile"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return frappe.get_list(
		"Instructor",
		filters=filters,
		fields=fields,
		order_by="instructor_name asc",
		limit_page_length=1000,
	)


def _offerings(branches: list[str]) -> list[dict]:
	if not branches:
		return []
	return frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": ["in", branches], "is_active": 1},
		fields=[
			"name",
			"offering_title",
			"offering_code",
			"institution",
			"school_branch",
			"program",
			"academic_year",
			"academic_term",
			"student_batch",
		],
		order_by="school_branch asc, academic_year desc, offering_title asc",
		limit_page_length=1000,
	)


def _groups(branches: list[str], offerings: list[str] | None = None) -> list[dict]:
	if not branches:
		return []
	filters: dict[str, Any] = {BRANCH_FIELD: ["in", branches], "disabled": 0}
	meta = frappe.get_meta("Student Group")
	if offerings and meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = ["in", offerings]
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD]
	for fieldname in ("eduedge_display_name", OFFERING_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return frappe.get_list(
		"Student Group",
		filters=filters,
		fields=fields,
		order_by=f"{BRANCH_FIELD} asc, student_group_name asc",
		limit_page_length=1000,
	)


def _course_map(offerings: list[dict]) -> tuple[list[dict], dict[str, set[str]]]:
	programs = sorted({row.program for row in offerings if row.get("program")})
	if not programs:
		return [], {}
	program_rows = frappe.get_all(
		"Program Course",
		filters={"parent": ["in", programs], "parenttype": "Program"},
		fields=["parent", "course", "course_name", "required"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	by_program: dict[str, set[str]] = {}
	course_names: set[str] = set()
	for row in program_rows:
		if not row.course:
			continue
		by_program.setdefault(row.parent, set()).add(row.course)
		course_names.add(row.course)
	course_details = {
		row.name: row
		for row in frappe.get_list(
			"Course",
			filters={"name": ["in", sorted(course_names)]},
			fields=["name", "course_name", "department", INSTITUTION_FIELD],
			order_by="course_name asc",
			limit_page_length=max(len(course_names), 1),
		)
	} if course_names else {}
	courses = [dict(course_details[name]) for name in sorted(course_details, key=lambda value: (course_details[value].course_name or value).lower())]
	return courses, by_program


def _assignment_rows(instructor: str | None, branches: list[str]) -> list[dict]:
	if not instructor or not branches:
		return []
	return frappe.get_list(
		"EduEdge Instructor Assignment",
		filters={"instructor": instructor, "school_branch": ["in", branches]},
		fields=[
			"name",
			"assignment_title",
			"assignment_type",
			"assignment_scope",
			"school_branch",
			"program_offering",
			"student_group",
			"course",
			"academic_year",
			"academic_term",
			"valid_from",
			"valid_to",
			"enabled",
		],
		order_by="modified desc",
		limit_page_length=1000,
	)


def _branch_assignment_rows(instructor: str | None, branches: list[str]) -> list[dict]:
	if not instructor or not branches:
		return []
	return frappe.get_list(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor, "school_branch": ["in", branches]},
		fields=["name", "school_branch", "is_primary", "enabled", "valid_from", "valid_to"],
		order_by="is_primary desc, school_branch asc",
		limit_page_length=1000,
	)


@frappe.whitelist()
def get_teacher_assignments_page(
	instructor: str | None = None,
	branches: str | list | None = None,
	offerings: str | list | None = None,
) -> dict:
	_require_read()
	allowed = _allowed_branches()
	selected_branches = _list_values(branches)
	if not selected_branches:
		current = str((get_current_school_branch() or {}).get("name") or "").strip()
		selected_branches = [current] if current else ([allowed[0]["name"]] if len(allowed) == 1 else [])
	branch_map = _validate_branches(selected_branches, allowed) if selected_branches else {}
	institutions = {row.get("institution") for row in branch_map.values() if row.get("institution")}
	instructor_rows = _instructors(institutions or {row.get("institution") for row in allowed if row.get("institution")})
	selected_instructor = next((row for row in instructor_rows if row.name == instructor), None)
	if instructor and not selected_instructor:
		frappe.throw(_("The selected Instructor is not available in the selected Institution context."), frappe.PermissionError)
	if selected_instructor and selected_instructor.get(INSTITUTION_FIELD):
		selected_branches = [
			name for name in selected_branches if branch_map.get(name, {}).get("institution") == selected_instructor.get(INSTITUTION_FIELD)
		]
		branch_map = {name: branch_map[name] for name in selected_branches}
	offering_rows = _offerings(selected_branches)
	selected_offerings = _list_values(offerings)
	if selected_offerings:
		allowed_names = {row.name for row in offering_rows}
		if any(name not in allowed_names for name in selected_offerings):
			frappe.throw(_("One or more selected Classes are not available in the selected Branches."), frappe.PermissionError)
	group_rows = _groups(selected_branches, selected_offerings or None)
	courses, course_map = _course_map(offering_rows)
	return {
		"allowed_branches": allowed,
		"selected_branches": selected_branches,
		"instructors": instructor_rows,
		"selected_instructor": selected_instructor,
		"offerings": offering_rows,
		"groups": group_rows,
		"courses": courses,
		"course_map": {key: sorted(values) for key, values in course_map.items()},
		"assignments": _assignment_rows(instructor, selected_branches),
		"branch_assignments": _branch_assignment_rows(instructor, selected_branches),
		"assignment_types": list(ASSIGNMENT_TYPES),
		"assignment_scopes": list(BULK_SCOPES),
		"permissions": {
			"can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
			"can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
			"can_manage_branch_access": bool(
				frappe.has_permission("EduEdge Instructor Branch Assignment", "create")
				or frappe.has_permission("EduEdge Instructor Branch Assignment", "write")
			),
		},
	}


def _offering_map(names: list[str], branch_map: dict[str, dict]) -> dict[str, frappe._dict]:
	if not names:
		return {}
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters={"name": ["in", names], "is_active": 1},
		fields=["name", "offering_title", "institution", "school_branch", "program", "academic_year", "academic_term"],
		limit_page_length=0,
	)
	mapping = {row.name: row for row in rows}
	for name in names:
		row = mapping.get(name)
		if not row:
			frappe.throw(_("Class / Programme Offering {0} is missing or inactive.").format(name), frappe.ValidationError)
		if row.school_branch not in branch_map:
			frappe.throw(_("Class / Programme Offering {0} is outside the selected Branches.").format(name), frappe.ValidationError)
		if branch_map[row.school_branch].get("institution") != row.institution:
			frappe.throw(_("Class / Programme Offering Institution context is invalid."), frappe.ValidationError)
	return mapping


def _group_map(names: list[str], offering_map: dict[str, frappe._dict]) -> dict[str, frappe._dict]:
	if not names:
		return {}
	meta = frappe.get_meta("Student Group")
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD, "disabled"]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	rows = frappe.get_all("Student Group", filters={"name": ["in", names]}, fields=fields, limit_page_length=0)
	mapping = {row.name: row for row in rows}
	for name in names:
		row = mapping.get(name)
		if not row or row.disabled:
			frappe.throw(_("Class Arm {0} is missing or disabled.").format(name), frappe.ValidationError)
		matching = [
			offering
			for offering in offering_map.values()
			if offering.school_branch == row.get(BRANCH_FIELD)
			and offering.program == row.program
			and offering.academic_year == row.academic_year
			and (not row.academic_term or row.academic_term == offering.academic_term)
		]
		if meta.has_field(OFFERING_FIELD) and row.get(OFFERING_FIELD):
			matching = [offering for offering in matching if offering.name == row.get(OFFERING_FIELD)]
		if len(matching) != 1:
			frappe.throw(_("Class Arm {0} does not resolve to exactly one selected Class / Programme Offering.").format(name), frappe.ValidationError)
		row.program_offering = matching[0].name
	return mapping


def _course_membership(programs: set[str]) -> dict[str, set[str]]:
	rows = frappe.get_all(
		"Program Course",
		filters={"parent": ["in", sorted(programs)], "parenttype": "Program"},
		fields=["parent", "course"],
		limit_page_length=0,
	) if programs else []
	result: dict[str, set[str]] = {}
	for row in rows:
		if row.course:
			result.setdefault(row.parent, set()).add(row.course)
	return result


def _plan(payload: dict) -> tuple[list[PlannedAssignment], list[dict], dict]:
	allowed = _allowed_branches()
	branches = _list_values(payload.get("branches"))
	branch_map = _validate_branches(branches, allowed)
	instructor = str(payload.get("instructor") or "").strip()
	if not instructor:
		frappe.throw(_("Select a Teacher / Instructor."), frappe.ValidationError)
	instructor_row = frappe.db.get_value(
		"Instructor",
		instructor,
		["name", "instructor_name", "status", INSTITUTION_FIELD],
		as_dict=True,
	)
	if not instructor_row or instructor_row.status != "Active":
		frappe.throw(_("Select an active Teacher / Instructor."), frappe.ValidationError)
	for branch in branch_map.values():
		if instructor_row.get(INSTITUTION_FIELD) and branch.get("institution") != instructor_row.get(INSTITUTION_FIELD):
			frappe.throw(_("A Teacher can be assigned only within their Institution."), frappe.ValidationError)
	scope = str(payload.get("assignment_scope") or BRANCH_ONLY_SCOPE).strip()
	if scope not in BULK_SCOPES:
		frappe.throw(_("Select a valid Assignment Scope."), frappe.ValidationError)
	assignment_type = str(payload.get("assignment_type") or "Subject Teacher").strip()
	if assignment_type not in ASSIGNMENT_TYPES:
		frappe.throw(_("Select a valid Assignment Type."), frappe.ValidationError)
	valid_from = payload.get("valid_from") or nowdate()
	valid_to = payload.get("valid_to") or None
	if valid_to and getdate(valid_to) < getdate(valid_from):
		frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)
	meta = {
		"instructor": instructor,
		"instructor_name": instructor_row.instructor_name,
		"assignment_scope": scope,
		"assignment_type": assignment_type,
		"valid_from": valid_from,
		"valid_to": valid_to,
		"enabled": cint(payload.get("enabled", 1)),
		"notes": payload.get("notes") or "",
		"branches": sorted(branch_map),
	}
	if scope == BRANCH_ONLY_SCOPE:
		return [], [], meta
	offering_names = _list_values(payload.get("program_offerings"))
	if not offering_names:
		frappe.throw(_("Select at least one Class / Programme Offering."), frappe.ValidationError)
	offering_map = _offering_map(offering_names, branch_map)
	group_names = _list_values(payload.get("student_groups"))
	if scope == CLASS_ARM_SCOPE and not group_names:
		frappe.throw(_("Select at least one Class Arm."), frappe.ValidationError)
	group_map = _group_map(group_names, offering_map) if scope == CLASS_ARM_SCOPE else {}
	courses = _list_values(payload.get("courses"))
	if assignment_type in COURSE_REQUIRED_TYPES and not courses:
		frappe.throw(_("Select at least one Subject / Course for this Assignment Type."), frappe.ValidationError)
	program_courses = _course_membership({row.program for row in offering_map.values() if row.program})
	planned: list[PlannedAssignment] = []
	skipped: list[dict] = []
	targets: list[tuple[frappe._dict, frappe._dict | None]] = []
	if scope == CLASS_SCOPE:
		targets = [(offering, None) for offering in offering_map.values()]
	else:
		targets = [(offering_map[group.program_offering], group) for group in group_map.values()]
	for offering, group in targets:
		candidate_courses = courses or [None]
		for course in candidate_courses:
			if course and course not in program_courses.get(offering.program, set()):
				skipped.append({
					"reason": "Subject is not configured for this Class",
					"program_offering": offering.name,
					"student_group": group.name if group else None,
					"course": course,
				})
				continue
			label_parts = [offering.offering_title or offering.name]
			if group:
				label_parts.append(group.get("student_group_name") or group.name)
			if course:
				label_parts.append(frappe.db.get_value("Course", course, "course_name") or course)
			planned.append(
				PlannedAssignment(
					branch=offering.school_branch,
					program_offering=offering.name,
					student_group=group.name if group else None,
					course=course,
					assignment_scope=scope,
					label=" · ".join(label_parts),
				)
			)
	if not planned:
		frappe.throw(_("No valid Teacher Assignment combination remains after Class and Subject validation."), frappe.ValidationError)
	return planned, skipped, meta


def _same_date(value_a, value_b) -> bool:
	return (str(value_a or "") == str(value_b or ""))


def _overlap(start_a, end_a, start_b, end_b) -> bool:
	minimum = getdate("1900-01-01")
	maximum = getdate("2999-12-31")
	a_start = getdate(start_a) if start_a else minimum
	a_end = getdate(end_a) if end_a else maximum
	b_start = getdate(start_b) if start_b else minimum
	b_end = getdate(end_b) if end_b else maximum
	return a_start <= b_end and b_start <= a_end


def _classify_existing(plan: list[PlannedAssignment], meta: dict) -> tuple[list[PlannedAssignment], list[dict], list[dict]]:
	create: list[PlannedAssignment] = []
	existing: list[dict] = []
	conflicts: list[dict] = []
	for row in plan:
		rows = frappe.get_all(
			"EduEdge Instructor Assignment",
			filters={
				"instructor": meta["instructor"],
				"school_branch": row.branch,
				"program_offering": row.program_offering,
				"assignment_scope": row.assignment_scope,
				"assignment_type": meta["assignment_type"],
			},
			fields=["name", "student_group", "course", "valid_from", "valid_to", "enabled"],
			limit_page_length=0,
		)
		matching = [
			existing_row
			for existing_row in rows
			if (existing_row.student_group or None) == row.student_group
			and (existing_row.course or None) == row.course
		]
		exact = next(
			(
				existing_row
				for existing_row in matching
				if _same_date(existing_row.valid_from, meta["valid_from"])
				and _same_date(existing_row.valid_to, meta["valid_to"])
			),
			None,
		)
		if exact:
			existing.append({"name": exact.name, "label": row.label, "enabled": cint(exact.enabled)})
			continue
		overlap = next(
			(
				existing_row
				for existing_row in matching
				if cint(existing_row.enabled)
				and _overlap(meta["valid_from"], meta["valid_to"], existing_row.valid_from, existing_row.valid_to)
			),
			None,
		)
		if overlap:
			conflicts.append({"name": overlap.name, "label": row.label, "reason": "Overlapping active assignment"})
			continue
		create.append(row)
	return create, existing, conflicts


@frappe.whitelist(methods=["POST"])
def preview_teacher_assignment_batch(payload: str | dict) -> dict:
	_require_read()
	plan, skipped, meta = _plan(_parse_payload(payload))
	create, existing, conflicts = _classify_existing(plan, meta)
	return {
		"scope": meta["assignment_scope"],
		"branch_count": len(meta["branches"]),
		"valid_combinations": len(plan),
		"create_count": len(create),
		"existing_count": len(existing),
		"skipped_count": len(skipped),
		"conflict_count": len(conflicts),
		"create": [asdict(row) for row in create],
		"existing": existing,
		"skipped": skipped,
		"conflicts": conflicts,
	}


def _ensure_branch_assignment(instructor: str, branch: str, valid_from, valid_to, make_primary: bool) -> tuple[str, str]:
	name = frappe.db.exists(
		"EduEdge Instructor Branch Assignment",
		{"instructor": instructor, "school_branch": branch},
	)
	if name:
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", name)
		doc.check_permission("write")
		old_start = getdate(doc.valid_from) if doc.valid_from else None
		new_start = getdate(valid_from) if valid_from else None
		if new_start and (not old_start or new_start < old_start):
			doc.valid_from = valid_from
		if not doc.valid_to or not valid_to:
			doc.valid_to = None
		elif getdate(valid_to) > getdate(doc.valid_to):
			doc.valid_to = valid_to
		doc.enabled = 1
		doc.save()
		return doc.name, "updated"
	if not frappe.has_permission("EduEdge Instructor Branch Assignment", "create"):
		frappe.throw(_("You are not permitted to create Branch access for Teachers."), frappe.PermissionError)
	doc = frappe.new_doc("EduEdge Instructor Branch Assignment")
	doc.instructor = instructor
	doc.school_branch = branch
	doc.enabled = 1
	doc.is_primary = 1 if make_primary else 0
	doc.valid_from = valid_from
	doc.valid_to = valid_to
	doc.save()
	return doc.name, "created"


@frappe.whitelist(methods=["POST"])
def save_teacher_assignment_batch(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_teacher_assignment_batch")
	data = _parse_payload(payload)
	plan, skipped, meta = _plan(data)
	if meta["assignment_scope"] != BRANCH_ONLY_SCOPE and not frappe.has_permission("EduEdge Instructor Assignment", "create"):
		frappe.throw(_("You are not permitted to create Teacher Assignments."), frappe.PermissionError)
	create, existing, conflicts = _classify_existing(plan, meta)
	if conflicts:
		frappe.throw(
			_("Teacher Assignment batch has {0} overlapping conflict(s). Resolve the existing assignments before saving.").format(len(conflicts)),
			frappe.ValidationError,
		)
	primary_exists = frappe.db.exists(
		"EduEdge Instructor Branch Assignment",
		{"instructor": meta["instructor"], "is_primary": 1, "enabled": 1},
	)
	branch_results: list[dict] = []
	for index, branch in enumerate(meta["branches"]):
		name, action = _ensure_branch_assignment(
			meta["instructor"],
			branch,
			meta["valid_from"],
			meta["valid_to"],
			make_primary=bool(not primary_exists and index == 0),
		)
		if action == "created" and not primary_exists and index == 0:
			primary_exists = name
		branch_results.append({"name": name, "branch": branch, "action": action})
	created: list[dict] = []
	for row in create:
		doc = frappe.new_doc("EduEdge Instructor Assignment")
		doc.instructor = meta["instructor"]
		doc.assignment_type = meta["assignment_type"]
		doc.assignment_scope = row.assignment_scope
		doc.enabled = meta["enabled"]
		doc.school_branch = row.branch
		doc.program_offering = row.program_offering
		doc.student_group = row.student_group
		doc.course = row.course
		doc.valid_from = meta["valid_from"]
		doc.valid_to = meta["valid_to"]
		doc.notes = meta["notes"]
		doc.save()
		created.append({"name": doc.name, "label": row.label})
	for row in existing:
		if not row.get("enabled"):
			doc = frappe.get_doc("EduEdge Instructor Assignment", row["name"])
			doc.check_permission("write")
			doc.enabled = 1
			doc.notes = meta["notes"] or doc.notes
			doc.save()
	return {
		"branch_access": branch_results,
		"created": created,
		"existing": existing,
		"skipped": skipped,
		"summary": {
			"branches_created_or_updated": len(branch_results),
			"assignments_created": len(created),
			"assignments_existing": len(existing),
			"invalid_combinations_skipped": len(skipped),
		},
	}
