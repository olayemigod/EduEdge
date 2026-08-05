from __future__ import annotations

from dataclasses import asdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.api import teacher_assignments as core
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access

BRANCH_ONLY_SCOPE = core.BRANCH_ONLY_SCOPE
BULK_SCOPES = core.BULK_SCOPES
ASSIGNMENT_TYPES = core.ASSIGNMENT_TYPES
PlannedAssignment = core.PlannedAssignment


def _instructors() -> list[dict]:
	meta = frappe.get_meta("Instructor")
	fields = ["name", "instructor_name", "department", "employee"]
	for fieldname in (INSTITUTION_FIELD, "eduedge_email", "eduedge_mobile"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Instructor",
		filters={"status": "Active"},
		fields=fields,
		order_by="instructor_name asc",
		limit_page_length=1000,
	)
	institution_names = {
		row.name: row.institution_name
		for row in frappe.get_list(
			"EduEdge Institution",
			fields=["name", "institution_name"],
			limit_page_length=0,
		)
	}
	for row in rows:
		row["home_institution_name"] = institution_names.get(row.get(INSTITUTION_FIELD)) or row.get(INSTITUTION_FIELD)
	return rows


@frappe.whitelist()
def get_instructor_assignments_page(
	instructor: str | None = None,
	branches: str | list | None = None,
	offerings: str | list | None = None,
) -> dict:
	core._require_read()
	allowed = core._allowed_branches()
	selected_branches = core._list_values(branches)
	if not selected_branches:
		current = str((core.get_current_school_branch() or {}).get("name") or "").strip()
		selected_branches = [current] if current else ([allowed[0]["name"]] if len(allowed) == 1 else [])
	branch_map = core._validate_branches(selected_branches, allowed) if selected_branches else {}
	instructor_rows = _instructors()
	selected_instructor = next((row for row in instructor_rows if row.name == instructor), None)
	if instructor and not selected_instructor:
		frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	offering_rows = core._offerings(selected_branches)
	selected_offerings = core._list_values(offerings)
	if selected_offerings:
		allowed_names = {row.name for row in offering_rows}
		if any(name not in allowed_names for name in selected_offerings):
			frappe.throw(_("One or more selected Classes are not available in the selected Branches."), frappe.PermissionError)
	group_rows = core._groups(selected_branches, selected_offerings or None)
	courses, course_map = core._course_map(offering_rows)
	return {
		"allowed_branches": allowed,
		"selected_branches": selected_branches,
		"instructors": instructor_rows,
		"selected_instructor": selected_instructor,
		"offerings": offering_rows,
		"groups": group_rows,
		"courses": courses,
		"course_map": {key: sorted(values) for key, values in course_map.items()},
		"assignments": core._assignment_rows(instructor, selected_branches),
		"branch_assignments": core._branch_assignment_rows(instructor, selected_branches),
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


def _plan(payload: dict) -> tuple[list[PlannedAssignment], list[dict], dict]:
	allowed = core._allowed_branches()
	branches = core._list_values(payload.get("branches"))
	branch_map = core._validate_branches(branches, allowed)
	instructor = str(payload.get("instructor") or "").strip()
	if not instructor:
		frappe.throw(_("Select an Instructor."), frappe.ValidationError)
	instructor_row = frappe.db.get_value(
		"Instructor",
		instructor,
		["name", "instructor_name", "status", INSTITUTION_FIELD],
		as_dict=True,
	)
	if not instructor_row or instructor_row.status != "Active":
		frappe.throw(_("Select an active Instructor."), frappe.ValidationError)
	frappe.get_doc("Instructor", instructor).check_permission("read")

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
		"home_institution": instructor_row.get(INSTITUTION_FIELD),
		"assignment_scope": scope,
		"assignment_type": assignment_type,
		"valid_from": valid_from,
		"valid_to": valid_to,
		"enabled": cint(payload.get("enabled", 1)),
		"notes": payload.get("notes") or "",
		"branches": sorted(branch_map),
		"assignment_institutions": sorted(
			{row.get("institution") for row in branch_map.values() if row.get("institution")}
		),
	}
	if scope == BRANCH_ONLY_SCOPE:
		return [], [], meta

	offering_names = core._list_values(payload.get("program_offerings"))
	if not offering_names:
		frappe.throw(_("Select at least one Class / Programme Offering."), frappe.ValidationError)
	offering_map = core._offering_map(offering_names, branch_map)
	group_names = core._list_values(payload.get("student_groups"))
	if scope == CLASS_ARM_SCOPE and not group_names:
		frappe.throw(_("Select at least one Class Arm."), frappe.ValidationError)
	group_map = core._group_map(group_names, offering_map) if scope == CLASS_ARM_SCOPE else {}
	courses = core._list_values(payload.get("courses"))
	if assignment_type in COURSE_REQUIRED_TYPES and not courses:
		frappe.throw(_("Select at least one Subject / Course for this Assignment Type."), frappe.ValidationError)
	program_courses = core._course_membership({row.program for row in offering_map.values() if row.program})
	planned: list[PlannedAssignment] = []
	skipped: list[dict] = []
	if scope == CLASS_SCOPE:
		targets = [(offering, None) for offering in offering_map.values()]
	else:
		targets = [(offering_map[group.program_offering], group) for group in group_map.values()]
	for offering, group in targets:
		for course in courses or [None]:
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
		frappe.throw(_("No valid Instructor Assignment combination remains after Class and Subject validation."), frappe.ValidationError)
	return planned, skipped, meta


@frappe.whitelist(methods=["POST"])
def preview_instructor_assignment_batch(payload: str | dict) -> dict:
	core._require_read()
	plan, skipped, meta = _plan(core._parse_payload(payload))
	create, existing, conflicts = core._classify_existing(plan, meta)
	return {
		"scope": meta["assignment_scope"],
		"branch_count": len(meta["branches"]),
		"institution_count": len(meta["assignment_institutions"]),
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
		frappe.throw(_("You are not permitted to create Branch access for Instructors."), frappe.PermissionError)
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
def save_instructor_assignment_batch(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_instructor_assignment_batch")
	data = core._parse_payload(payload)
	plan, skipped, meta = _plan(data)
	if meta["assignment_scope"] != BRANCH_ONLY_SCOPE and not frappe.has_permission("EduEdge Instructor Assignment", "create"):
		frappe.throw(_("You are not permitted to create Instructor Assignments."), frappe.PermissionError)
	create, existing, conflicts = core._classify_existing(plan, meta)
	if conflicts:
		frappe.throw(
			_("Instructor Assignment batch has {0} overlapping conflict(s). Resolve the existing assignments before saving.").format(len(conflicts)),
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
			"institutions_covered": len(meta["assignment_institutions"]),
			"branches_created_or_updated": len(branch_results),
			"assignments_created": len(created),
			"assignments_existing": len(existing),
			"invalid_combinations_skipped": len(skipped),
		},
	}
