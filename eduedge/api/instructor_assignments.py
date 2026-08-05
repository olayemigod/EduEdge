from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.api import teacher_assignments as core
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import (
	CLASS_ARM_SCOPE,
	CLASS_RESPONSIBILITY_TYPES,
	CLASS_SCOPE,
	LEGACY_SUBJECT_TEACHER,
	SUBJECT_INSTRUCTOR,
	UNIQUE_PRIMARY_ASSIGNMENT_TYPES,
	current_user_instructors,
)
from eduedge.platform.access import require_eduedge_access

BRANCH_ONLY_SCOPE = core.BRANCH_ONLY_SCOPE
BULK_SCOPES = (BRANCH_ONLY_SCOPE, CLASS_SCOPE, CLASS_ARM_SCOPE)
ASSIGNMENT_TYPES = (
	"Class Teacher",
	SUBJECT_INSTRUCTOR,
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
	"Form Teacher",
	"Head of Class / Level",
)
SUBJECT_REQUIRED_TYPES = {
	SUBJECT_INSTRUCTOR,
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
}


@dataclass(frozen=True)
class PlannedAssignment:
	row_id: str
	branch: str
	institution: str
	program_offering: str
	student_group: str | None
	course: str | None
	assignment_scope: str
	assignment_type: str
	valid_from: str | None
	valid_to: str | None
	enabled: int
	notes: str
	label: str


@dataclass(frozen=True)
class PlannedBranchAccess:
	row_id: str
	branch: str
	institution: str
	valid_from: str | None
	valid_to: str | None
	enabled: int
	notes: str
	label: str


def _normalise_type(value: str | None) -> str:
	resolved = str(value or "").strip()
	return SUBJECT_INSTRUCTOR if resolved == LEGACY_SUBJECT_TEACHER else resolved


def _rows(payload: dict) -> list[dict]:
	values = payload.get("rows")
	if isinstance(values, str):
		values = frappe.parse_json(values)
	if isinstance(values, list):
		return [dict(row or {}) for row in values if isinstance(row, dict)]
	if str(payload.get("assignment_scope") or "") == BRANCH_ONLY_SCOPE:
		return [
			{
				"row_id": f"legacy-branch-{index}",
				"branch": branch,
				"assignment_scope": BRANCH_ONLY_SCOPE,
				"valid_from": payload.get("valid_from"),
				"valid_to": payload.get("valid_to"),
				"enabled": payload.get("enabled", 1),
				"notes": payload.get("notes") or "",
			}
			for index, branch in enumerate(core._list_values(payload.get("branches")), 1)
		]
	frappe.throw(
		_(
			"The previous global Class × Class Arm × Subject assignment format has been retired because it could create unintended responsibilities. Refresh the page and use explicit Assignment Rows."
		),
		frappe.ValidationError,
	)


def _can_manage_assignments() -> bool:
	return bool(
		frappe.has_permission("EduEdge Instructor Assignment", "create")
		or frappe.has_permission("EduEdge Instructor Assignment", "write")
	)


def _require_assignment_manager() -> None:
	core._require_read()
	if not _can_manage_assignments():
		frappe.throw(
			_("Only authorised academic managers can create or change Instructor Assignments."),
			frappe.PermissionError,
		)


def _instructors() -> list[dict]:
	meta = frappe.get_meta("Instructor")
	filters: dict[str, Any] = {"status": "Active"}
	if not _can_manage_assignments():
		own = current_user_instructors()
		filters["name"] = ["in", own] if own else ["in", ["__none__"]]
	fields = ["name", "instructor_name", "department", "employee", "status"]
	for fieldname in (INSTITUTION_FIELD, "eduedge_email", "eduedge_mobile"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Instructor",
		filters=filters,
		fields=fields,
		order_by="instructor_name asc",
		limit_page_length=1000,
	)
	institutions = {
		row.name: row.institution_name
		for row in frappe.get_list(
			"EduEdge Institution",
			fields=["name", "institution_name"],
			limit_page_length=0,
		)
	}
	for row in rows:
		row["home_institution_name"] = institutions.get(row.get(INSTITUTION_FIELD)) or row.get(INSTITUTION_FIELD)
	return rows


def _period_dates(academic_year: str | None, academic_term: str | None) -> tuple[str | None, str | None]:
	if academic_term:
		row = frappe.db.get_value(
			"Academic Term",
			academic_term,
			["term_start_date", "term_end_date"],
			as_dict=True,
		) or {}
		if row.get("term_start_date") or row.get("term_end_date"):
			return row.get("term_start_date"), row.get("term_end_date")
	if academic_year:
		row = frappe.db.get_value(
			"Academic Year",
			academic_year,
			["year_start_date", "year_end_date"],
			as_dict=True,
		) or {}
		return row.get("year_start_date"), row.get("year_end_date")
	return None, None


def _course_options(
	allowed: list[dict],
	offerings: list[dict],
) -> tuple[list[dict], dict[str, set[str]], dict[str, set[str]]]:
	"""Expose Institution subjects while retaining exact Program curriculum membership."""
	configured_courses, configured_map = core._course_map(offerings)
	course_meta = frappe.get_meta("Course")
	institution_names = sorted(
		{
			str(row.get("institution") or "").strip()
			for row in allowed
			if str(row.get("institution") or "").strip()
		}
	)
	fields = ["name", "course_name", "department"]
	if course_meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	filters: dict[str, Any] = {}
	if institution_names and course_meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = ["in", institution_names]
	institution_courses = frappe.get_list(
		"Course",
		filters=filters,
		fields=fields,
		order_by="course_name asc",
		limit_page_length=0,
	) if frappe.has_permission("Course", "read") else []
	course_rows = {row.name: dict(row) for row in configured_courses}
	for row in institution_courses:
		course_rows[row.name] = dict(row)

	visible_map: dict[str, set[str]] = {}
	for offering in offerings:
		program = str(offering.get("program") or "").strip()
		institution = str(offering.get("institution") or "").strip()
		if not program:
			continue
		visible = set(configured_map.get(program, set()))
		for course in course_rows.values():
			course_institution = str(course.get(INSTITUTION_FIELD) or "").strip()
			if not course_institution or course_institution == institution:
				visible.add(course["name"])
		visible_map[program] = visible
	return (
		sorted(course_rows.values(), key=lambda row: str(row.get("course_name") or row.get("name") or "").lower()),
		visible_map,
		configured_map,
	)


def _all_options(allowed: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict[str, set[str]], dict[str, set[str]]]:
	branches = [row["name"] for row in allowed]
	offerings = core._offerings(branches)
	for row in offerings:
		row["period_start_date"], row["period_end_date"] = _period_dates(row.academic_year, row.academic_term)
	groups = core._groups(branches)
	courses, visible_map, configured_map = _course_options(allowed, offerings)
	return offerings, groups, courses, visible_map, configured_map


@frappe.whitelist()
def get_instructor_assignments_page(
	instructor: str | None = None,
	branches: str | list | None = None,
	offerings: str | list | None = None,
) -> dict:
	core._require_read()
	allowed = core._allowed_branches()
	allowed_names = [row["name"] for row in allowed]
	selected = core._list_values(branches)
	if selected and any(name not in allowed_names for name in selected):
		frappe.throw(_("One or more selected Branches are not available to your user."), frappe.PermissionError)
	if not selected:
		current = str((core.get_current_school_branch() or {}).get("name") or "").strip()
		selected = [current] if current else (allowed_names[:] if len(allowed_names) == 1 else [])
	instructors = _instructors()
	if not instructor and not _can_manage_assignments() and len(instructors) == 1:
		instructor = instructors[0].name
	selected_instructor = next((row for row in instructors if row.name == instructor), None)
	if instructor and not selected_instructor:
		frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	offering_rows, groups, courses, course_map, configured_course_map = _all_options(allowed)
	requested_offerings = core._list_values(offerings)
	if requested_offerings and any(name not in {row.name for row in offering_rows} for name in requested_offerings):
		frappe.throw(_("One or more selected Classes are not available to your user."), frappe.PermissionError)
	register_branches = selected or allowed_names
	return {
		"allowed_branches": allowed,
		"selected_branches": selected,
		"instructors": instructors,
		"selected_instructor": selected_instructor,
		"offerings": offering_rows,
		"groups": groups,
		"courses": courses,
		"course_map": {key: sorted(values) for key, values in course_map.items()},
		"configured_course_map": {key: sorted(values) for key, values in configured_course_map.items()},
		"assignments": core._assignment_rows(instructor, register_branches),
		"branch_assignments": core._branch_assignment_rows(instructor, register_branches) if _can_manage_assignments() else [],
		"assignment_types": list(ASSIGNMENT_TYPES),
		"assignment_scopes": list(BULK_SCOPES),
		"subject_required_types": sorted(SUBJECT_REQUIRED_TYPES),
		"class_responsibility_types": sorted(CLASS_RESPONSIBILITY_TYPES),
		"permissions": {
			"can_manage": _can_manage_assignments(),
			"can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
			"can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
			"can_manage_branch_access": bool(
				frappe.has_permission("EduEdge Instructor Branch Assignment", "create")
				or frappe.has_permission("EduEdge Instructor Branch Assignment", "write")
			),
		},
	}


def _maps(rows: list[dict], allowed: list[dict]) -> tuple[dict, dict, dict, dict]:
	branch_map = {row["name"]: row for row in allowed}
	offering_names = {str(row.get("program_offering") or "").strip() for row in rows if row.get("program_offering")}
	offerings = {
		row.name: row
		for row in frappe.get_all(
			"EduEdge Program Offering",
			filters={"name": ["in", sorted(offering_names)], "is_active": 1},
			fields=["name", "offering_title", "institution", "school_branch", "program", "academic_year", "academic_term"],
			limit_page_length=0,
		)
	} if offering_names else {}
	group_names = {name for row in rows for name in core._list_values(row.get("student_groups"))}
	meta = frappe.get_meta("Student Group")
	group_fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD, "disabled"]
	if meta.has_field(OFFERING_FIELD):
		group_fields.append(OFFERING_FIELD)
	groups = {
		row.name: row
		for row in frappe.get_all(
			"Student Group",
			filters={"name": ["in", sorted(group_names)]},
			fields=group_fields,
			limit_page_length=0,
		)
	} if group_names else {}
	program_courses = core._course_membership({row.program for row in offerings.values() if row.program})
	return branch_map, offerings, groups, program_courses


def _date_range(row: dict, label: str) -> tuple[str | None, str | None]:
	start = str(row.get("valid_from") or "").strip() or None
	end = str(row.get("valid_to") or "").strip() or None
	if start and end and getdate(end) < getdate(start):
		frappe.throw(_("{0}: Valid To cannot be earlier than Valid From.").format(label), frappe.ValidationError)
	return start, end


def _validate_type_scope(assignment_type: str, scope: str, courses: list[str], label: str) -> None:
	if assignment_type not in ASSIGNMENT_TYPES or scope not in BULK_SCOPES:
		frappe.throw(_("{0}: select a valid Assignment Type and Scope.").format(label), frappe.ValidationError)
	if assignment_type in {"Class Teacher", "Form Teacher"} and scope != CLASS_ARM_SCOPE:
		frappe.throw(_("{0}: {1} must be assigned to a specific Class Arm.").format(label, assignment_type), frappe.ValidationError)
	if assignment_type == "Head of Class / Level" and scope != CLASS_SCOPE:
		frappe.throw(_("{0}: Head of Class / Level must use Class / Programme Offering scope.").format(label), frappe.ValidationError)
	if assignment_type in SUBJECT_REQUIRED_TYPES and not courses:
		frappe.throw(_("{0}: select at least one Subject / Course for {1}.").format(label, assignment_type), frappe.ValidationError)
	if assignment_type in CLASS_RESPONSIBILITY_TYPES and courses:
		frappe.throw(_("{0}: {1} is a class responsibility and cannot carry Subjects. Add a separate Subject Instructor row.").format(label, assignment_type), frappe.ValidationError)


def _validate_group(group, offering, label: str) -> None:
	if not group or cint(group.disabled):
		frappe.throw(_("{0}: select an active Class Arm.").format(label), frappe.ValidationError)
	if group.get(BRANCH_FIELD) != offering.school_branch or group.program != offering.program:
		frappe.throw(_("{0}: Class Arm does not belong to the selected Class and Branch.").format(label), frappe.ValidationError)
	if group.academic_year and group.academic_year != offering.academic_year:
		frappe.throw(_("{0}: Class Arm Academic Session does not match the selected Class.").format(label), frappe.ValidationError)
	if group.academic_term and group.academic_term != offering.academic_term:
		frappe.throw(_("{0}: Class Arm Term does not match the selected Class.").format(label), frappe.ValidationError)
	if group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != offering.name:
		frappe.throw(_("{0}: Class Arm does not belong to the selected Programme Offering.").format(label), frappe.ValidationError)


def _plan(payload: dict) -> tuple[list[PlannedAssignment], list[PlannedBranchAccess], dict]:
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
	rows = _rows(payload)
	if not rows:
		frappe.throw(_("Add at least one Assignment Row."), frappe.ValidationError)
	allowed = core._allowed_branches()
	branch_map, offering_map, group_map, program_courses = _maps(rows, allowed)
	planned: list[PlannedAssignment] = []
	branch_access: list[PlannedBranchAccess] = []
	institutions: set[str] = set()
	summaries: list[dict] = []
	curriculum_additions: dict[tuple[str, str], dict] = {}
	course_meta = frappe.get_meta("Course")
	for index, row in enumerate(rows, 1):
		row_id = str(row.get("row_id") or f"row-{index}")
		label = str(row.get("row_label") or f"Assignment Row {index}")
		branch_name = str(row.get("branch") or "").strip()
		branch = branch_map.get(branch_name)
		if not branch:
			frappe.throw(_("{0}: select a permitted Branch / Campus.").format(label), frappe.PermissionError)
		core.assert_branch_access(branch_name)
		institution = branch.get("institution") or ""
		if institution:
			institutions.add(institution)
		start, end = _date_range(row, label)
		enabled = cint(row.get("enabled", 1))
		notes = str(row.get("notes") or "").strip()
		scope = str(row.get("assignment_scope") or CLASS_ARM_SCOPE)
		if scope == BRANCH_ONLY_SCOPE:
			branch_access.append(
				PlannedBranchAccess(
					row_id,
					branch_name,
					institution,
					start,
					end,
					enabled,
					notes,
					f"{branch.get('institution_name') or institution} · {branch.get('branch_name') or branch_name}",
				)
			)
			summaries.append({"row_id": row_id, "scope": scope, "record_count": 1})
			continue
		offering = offering_map.get(str(row.get("program_offering") or ""))
		if not offering or offering.school_branch != branch_name or offering.institution != institution:
			frappe.throw(_("{0}: selected Class belongs to another Branch or Institution.").format(label), frappe.ValidationError)
		period_start, period_end = _period_dates(offering.academic_year, offering.academic_term)
		start = start or period_start
		end = end or period_end
		if period_start and start and getdate(start) < getdate(period_start):
			frappe.throw(_("{0}: Valid From cannot be earlier than the selected Class academic period.").format(label), frappe.ValidationError)
		if period_end and end and getdate(end) > getdate(period_end):
			frappe.throw(_("{0}: Valid To cannot be later than the selected Class academic period.").format(label), frappe.ValidationError)
		assignment_type = _normalise_type(row.get("assignment_type") or SUBJECT_INSTRUCTOR)
		courses = core._list_values(row.get("courses"))
		_validate_type_scope(assignment_type, scope, courses, label)
		missing_for_row: set[str] = set()
		for course in courses:
			course_doc = frappe.get_doc("Course", course)
			course_doc.check_permission("read")
			course_institution = course_doc.get(INSTITUTION_FIELD) if course_meta.has_field(INSTITUTION_FIELD) else None
			if course_institution and course_institution != institution:
				frappe.throw(_("{0}: Subject / Course belongs to another Institution.").format(label), frappe.ValidationError)
			if course not in program_courses.get(offering.program, set()):
				program_doc = frappe.get_doc("Program", offering.program)
				program_doc.check_permission("write")
				missing_for_row.add(course)
				curriculum_additions[(offering.program, course)] = {
					"program": offering.program,
					"program_offering": offering.name,
					"course": course,
					"course_name": course_doc.course_name or course,
					"row_id": row_id,
					"reason": _("Institution Subject will be added to the selected Class curriculum"),
				}
		targets: list[Any] = [None]
		if scope == CLASS_ARM_SCOPE:
			names = core._list_values(row.get("student_groups"))
			if not names:
				frappe.throw(_("{0}: select at least one Class Arm.").format(label), frappe.ValidationError)
			targets = []
			for name in names:
				group = group_map.get(name)
				_validate_group(group, offering, label)
				targets.append(group)
		count = 0
		for group in targets:
			for course in courses or [None]:
				parts = [
					offering.offering_title or offering.name,
					(group.get("student_group_name") or group.name) if group else _("All Class Arms"),
					(frappe.db.get_value("Course", course, "course_name") or course) if course else assignment_type,
				]
				if course in missing_for_row:
					parts.append(_("add to Class curriculum"))
				planned.append(
					PlannedAssignment(
						row_id,
						branch_name,
						institution,
						offering.name,
						group.name if group else None,
						course,
						scope,
						assignment_type,
						start,
						end,
						enabled,
						notes,
						" · ".join(str(value) for value in parts if value),
					)
				)
				count += 1
		summaries.append({"row_id": row_id, "scope": scope, "record_count": count})
	_validate_batch_duplicates(planned)
	_validate_branch_access_duplicates(branch_access)
	return planned, branch_access, {
		"instructor": instructor,
		"assignment_institutions": sorted(institutions),
		"row_summaries": summaries,
		"curriculum_additions": list(curriculum_additions.values()),
	}


def _identity(row: PlannedAssignment) -> tuple:
	return (
		row.branch,
		row.program_offering,
		row.student_group or "",
		row.course or "",
		row.assignment_scope,
		row.assignment_type,
	)


def _validate_batch_duplicates(plan: list[PlannedAssignment]) -> None:
	grouped: dict[tuple, list[PlannedAssignment]] = {}
	for row in plan:
		grouped.setdefault(_identity(row), []).append(row)
	for rows in grouped.values():
		for index, row in enumerate(rows):
			for other in rows[index + 1 :]:
				if core._overlap(row.valid_from, row.valid_to, other.valid_from, other.valid_to):
					frappe.throw(
						_("Assignment Rows {0} and {1} produce the same overlapping academic responsibility. Merge or remove one row.").format(row.row_id, other.row_id),
						frappe.DuplicateEntryError,
					)


def _validate_branch_access_duplicates(rows: list[PlannedBranchAccess]) -> None:
	grouped: dict[str, list[PlannedBranchAccess]] = {}
	for row in rows:
		grouped.setdefault(row.branch, []).append(row)
	for branch_rows in grouped.values():
		for index, row in enumerate(branch_rows):
			for other in branch_rows[index + 1 :]:
				if row.enabled and other.enabled and core._overlap(row.valid_from, row.valid_to, other.valid_from, other.valid_to):
					frappe.throw(
						_("Assignment Rows {0} and {1} create overlapping explicit Branch access for {2}.").format(row.row_id, other.row_id, row.branch),
						frappe.DuplicateEntryError,
					)


def _type_variants(value: str) -> list[str]:
	return [SUBJECT_INSTRUCTOR, LEGACY_SUBJECT_TEACHER] if value == SUBJECT_INSTRUCTOR else [value]


def _classify(plan: list[PlannedAssignment], instructor: str) -> tuple[list, list, list]:
	create, existing, conflicts = [], [], []
	for row in plan:
		records = frappe.get_all(
			"EduEdge Instructor Assignment",
			filters={
				"instructor": instructor,
				"school_branch": row.branch,
				"program_offering": row.program_offering,
				"assignment_scope": row.assignment_scope,
				"assignment_type": ["in", _type_variants(row.assignment_type)],
			},
			fields=["name", "student_group", "course", "valid_from", "valid_to", "enabled"],
			limit_page_length=0,
		)
		matching = [
			value
			for value in records
			if (value.student_group or None) == row.student_group and (value.course or None) == row.course
		]
		exact = next(
			(
				value
				for value in matching
				if core._same_date(value.valid_from, row.valid_from)
				and core._same_date(value.valid_to, row.valid_to)
			),
			None,
		)
		if exact:
			existing.append(
				{
					"name": exact.name,
					"row_id": row.row_id,
					"label": row.label,
					"enabled": cint(exact.enabled),
					"requested_enabled": row.enabled,
					"notes": row.notes,
				}
			)
			continue
		overlap = next(
			(
				value
				for value in matching
				if cint(value.enabled)
				and row.enabled
				and core._overlap(row.valid_from, row.valid_to, value.valid_from, value.valid_to)
			),
			None,
		)
		if overlap:
			conflicts.append(
				{
					"name": overlap.name,
					"row_id": row.row_id,
					"label": row.label,
					"reason": _("Overlapping active assignment for this Instructor"),
				}
			)
		else:
			create.append(row)
	conflicts.extend(_primary_conflicts(plan, instructor))
	return create, existing, conflicts


def _primary_conflicts(plan: list[PlannedAssignment], instructor: str) -> list[dict]:
	conflicts = []
	for row in plan:
		if not row.enabled or row.assignment_type not in UNIQUE_PRIMARY_ASSIGNMENT_TYPES:
			continue
		filters: dict[str, Any] = {
			"instructor": ["!=", instructor],
			"school_branch": row.branch,
			"program_offering": row.program_offering,
			"assignment_scope": row.assignment_scope,
			"assignment_type": row.assignment_type,
			"enabled": 1,
		}
		if row.assignment_scope == CLASS_ARM_SCOPE:
			filters["student_group"] = row.student_group
		records = frappe.get_all(
			"EduEdge Instructor Assignment",
			filters=filters,
			fields=["name", "instructor", "valid_from", "valid_to"],
			limit_page_length=0,
		)
		overlap = next(
			(
				value
				for value in records
				if core._overlap(row.valid_from, row.valid_to, value.valid_from, value.valid_to)
			),
			None,
		)
		if overlap:
			conflicts.append(
				{
					"name": overlap.name,
					"row_id": row.row_id,
					"label": row.label,
					"reason": _("{0} already has another active primary Instructor.").format(row.assignment_type),
					"other_instructor": overlap.instructor,
				}
			)
	return conflicts


def _branch_periods(instructor: str, branch: str) -> list[dict]:
	return frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor, "school_branch": branch},
		fields=["name", "enabled", "is_primary", "valid_from", "valid_to"],
		order_by="valid_from asc, modified asc",
		limit_page_length=0,
	)


def _min_date(left, right):
	if not left or not right:
		return None
	return left if getdate(left) <= getdate(right) else right


def _max_date(left, right):
	if not left or not right:
		return None
	return left if getdate(left) >= getdate(right) else right


def _save_branch_period(
	instructor: str,
	branch: str,
	start,
	end,
	*,
	enabled: int,
	make_primary: bool,
) -> dict:
	periods = _branch_periods(instructor, branch)
	exact = next(
		(
			row
			for row in periods
			if core._same_date(row.valid_from, start) and core._same_date(row.valid_to, end)
		),
		None,
	)
	if exact:
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", exact.name)
		doc.check_permission("write")
		doc.enabled = cint(enabled)
		if not doc.enabled:
			doc.is_primary = 0
		doc.save()
		return {"name": doc.name, "branch": branch, "action": "updated", "enabled": doc.enabled}
	if not enabled:
		return {"name": None, "branch": branch, "action": "not-found-disabled", "enabled": 0}
	overlapping = next(
		(
			row
			for row in periods
			if cint(row.enabled) and core._overlap(start, end, row.valid_from, row.valid_to)
		),
		None,
	)
	if overlapping:
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", overlapping.name)
		doc.check_permission("write")
		doc.valid_from = _min_date(doc.valid_from, start)
		doc.valid_to = _max_date(doc.valid_to, end)
		doc.enabled = 1
		doc.save()
		return {"name": doc.name, "branch": branch, "action": "extended", "enabled": 1}
	if not frappe.has_permission("EduEdge Instructor Branch Assignment", "create"):
		frappe.throw(_("You are not permitted to create Branch access for Instructors."), frappe.PermissionError)
	doc = frappe.new_doc("EduEdge Instructor Branch Assignment")
	doc.instructor, doc.school_branch = instructor, branch
	doc.enabled, doc.is_primary = 1, 1 if make_primary else 0
	doc.valid_from, doc.valid_to = start, end
	doc.save()
	return {"name": doc.name, "branch": branch, "action": "created", "enabled": 1}


# _ensure_branch_assignment was replaced by exact-period academic eligibility.
def _ensure_academic_branch_access(instructor: str, row: PlannedAssignment) -> dict | None:
	if not row.enabled:
		return None
	return _save_branch_period(
		instructor,
		row.branch,
		row.valid_from,
		row.valid_to,
		enabled=1,
		make_primary=False,
	)


def _apply_curriculum_additions(additions: list[dict]) -> list[dict]:
	"""Attach selected Institution Subjects to their exact native Program curriculum."""
	grouped: dict[str, list[dict]] = {}
	for row in additions:
		grouped.setdefault(row["program"], []).append(row)
	results: list[dict] = []
	for program, rows in grouped.items():
		doc = frappe.get_doc("Program", program)
		doc.check_permission("write")
		existing = {row.course for row in doc.get("courses") or [] if row.course}
		created = []
		for row in rows:
			course = row["course"]
			if course in existing:
				continue
			doc.append("courses", {"course": course, "required": 1})
			existing.add(course)
			created.append(course)
		if created:
			doc.save()
		for course in created:
			results.append(
				{
					"program": program,
					"course": course,
					"course_name": frappe.db.get_value("Course", course, "course_name") or course,
					"action": "added-to-class-curriculum",
				}
			)
	return results


@frappe.whitelist(methods=["POST"])
def preview_instructor_assignment_batch(payload: str | dict) -> dict:
	_require_assignment_manager()
	plan, branch_access, meta = _plan(core._parse_payload(payload))
	create, existing, conflicts = _classify(plan, meta["instructor"])
	return {
		"row_count": len(meta["row_summaries"]),
		"row_summaries": meta["row_summaries"],
		"institution_count": len(meta["assignment_institutions"]),
		"academic_record_count": len(plan),
		"branch_access_record_count": len(branch_access),
		"curriculum_change_count": len(meta["curriculum_additions"]),
		"curriculum_changes": meta["curriculum_additions"],
		"create_count": len(create),
		"existing_count": len(existing),
		"branch_change_count": len(branch_access),
		"conflict_count": len(conflicts),
		"create": [asdict(row) for row in create],
		"existing": existing,
		"branch_changes": [asdict(row) for row in branch_access],
		"conflicts": conflicts,
	}


def _save_assignment(instructor: str, row: PlannedAssignment) -> dict:
	doc = frappe.new_doc("EduEdge Instructor Assignment")
	doc.instructor, doc.assignment_type, doc.assignment_scope = instructor, row.assignment_type, row.assignment_scope
	doc.enabled, doc.school_branch, doc.program_offering = row.enabled, row.branch, row.program_offering
	doc.student_group, doc.course = row.student_group, row.course
	doc.valid_from, doc.valid_to, doc.notes = row.valid_from, row.valid_to, row.notes
	frappe.flags.in_eduedge_assignment_matrix_save = True
	try:
		doc.save()
	finally:
		frappe.flags.in_eduedge_assignment_matrix_save = False
	return {"name": doc.name, "row_id": row.row_id, "label": row.label, "enabled": row.enabled}


@frappe.whitelist(methods=["POST"])
def save_instructor_assignment_batch(payload: str | dict) -> dict:
	_require_assignment_manager()
	require_eduedge_access(feature_key="academics", action="save_instructor_assignment_batch")
	plan, branch_access, meta = _plan(core._parse_payload(payload))
	if plan and not frappe.has_permission("EduEdge Instructor Assignment", "create"):
		frappe.throw(_("You are not permitted to create Instructor Assignments."), frappe.PermissionError)
	create, existing, conflicts = _classify(plan, meta["instructor"])
	if conflicts:
		frappe.throw(
			_("Instructor Assignment plan has {0} conflict(s). Resolve them before saving.").format(len(conflicts)),
			frappe.ValidationError,
		)
	curriculum_results = _apply_curriculum_additions(meta["curriculum_additions"])
	primary_exists = frappe.db.exists(
		"EduEdge Instructor Branch Assignment",
		{"instructor": meta["instructor"], "is_primary": 1, "enabled": 1},
	)
	explicit_results = []
	for row in branch_access:
		result = _save_branch_period(
			meta["instructor"],
			row.branch,
			row.valid_from,
			row.valid_to,
			enabled=row.enabled,
			make_primary=bool(not primary_exists and row.enabled),
		)
		if result.get("name") and result.get("enabled") and not primary_exists:
			primary_exists = result["name"]
		explicit_results.append(result)
	academic_results, seen = [], set()
	for row in plan:
		key = (row.branch, row.valid_from or "", row.valid_to or "")
		if not row.enabled or key in seen:
			continue
		seen.add(key)
		result = _ensure_academic_branch_access(meta["instructor"], row)
		if result:
			academic_results.append(result)
	created = [_save_assignment(meta["instructor"], row) for row in create]
	updated = []
	for row in existing:
		if cint(row["enabled"]) == cint(row["requested_enabled"]) and not row.get("notes"):
			continue
		doc = frappe.get_doc("EduEdge Instructor Assignment", row["name"])
		doc.check_permission("write")
		doc.enabled = cint(row["requested_enabled"])
		if row.get("notes"):
			doc.notes = row["notes"]
		frappe.flags.in_eduedge_assignment_matrix_save = True
		try:
			doc.save()
		finally:
			frappe.flags.in_eduedge_assignment_matrix_save = False
		updated.append({"name": doc.name, "row_id": row["row_id"], "enabled": doc.enabled})
	return {
		"branch_access": explicit_results,
		"academic_branch_eligibility": academic_results,
		"curriculum_changes": curriculum_results,
		"created": created,
		"existing": existing,
		"updated_existing": updated,
		"summary": {
			"institutions_covered": len(meta["assignment_institutions"]),
			"rows_processed": len(meta["row_summaries"]),
			"class_curriculum_subjects_added": len(curriculum_results),
			"branch_access_changed": len(explicit_results),
			"academic_branch_periods_ensured": len(academic_results),
			"assignments_created": len(created),
			"assignments_existing": len(existing),
			"assignments_updated": len(updated),
		},
	}
