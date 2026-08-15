from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.class_arm_identity import (
	CLASS_ARM_DOCTYPE,
	CLASS_ARM_FIELD,
	DISPLAY_NAME_FIELD,
	PREVIOUS_GROUP_FIELD,
	clean_class_arm_name,
	destination_is_later,
	generate_operational_group_name,
	get_or_create_class_arm,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

DEFAULT_PAGE_LENGTH = 25
MAX_PAGE_LENGTH = 50
MAX_OPTION_ROWS = 500


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_read() -> None:
	_require_login()
	if not frappe.has_permission("Student Group", "read"):
		frappe.throw(_("You are not permitted to view Class Arms."), frappe.PermissionError)


def _allowed_branches() -> list[dict]:
	rows = get_allowed_school_branches() or []
	result: list[dict] = []
	for source in rows:
		row = dict(source)
		name = row.get("name")
		if not name:
			continue
		if not row.get("institution") or not row.get("branch_name"):
			details = frappe.db.get_value(
				"EduEdge School Branch",
				name,
				["branch_name", "institution", "enabled"],
				as_dict=True,
			) or {}
			row.update({key: value for key, value in details.items() if value is not None})
		if not cint(row.get("enabled", 1)):
			continue
		if row.get("institution") and not row.get("institution_name"):
			row["institution_name"] = frappe.db.get_value(
				"EduEdge Institution", row.get("institution"), "institution_name"
			)
		result.append(row)
	return result


def _resolve_branch(branch: str | None) -> tuple[str, dict, list[dict]]:
	allowed = _allowed_branches()
	allowed_by_name = {row.get("name"): row for row in allowed if row.get("name")}
	resolved = str(branch or "").strip()
	if not resolved:
		current = get_current_school_branch() or {}
		resolved = str(current.get("name") or "").strip()
	if not resolved and len(allowed) == 1:
		resolved = str(allowed[0].get("name") or "").strip()
	if not resolved:
		frappe.throw(_("Select a permitted School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(resolved)
	selected = allowed_by_name.get(resolved)
	if not selected:
		frappe.throw(_("The selected School Branch / Campus is not available to your user."), frappe.PermissionError)
	return resolved, selected, allowed


def _student_group_fields() -> list[str]:
	meta = frappe.get_meta("Student Group")
	fields = [
		"name",
		"student_group_name",
		"group_based_on",
		"program",
		"course",
		"academic_year",
		"academic_term",
		"batch",
		"max_strength",
		"disabled",
		"modified",
	]
	for fieldname in (
		DISPLAY_NAME_FIELD,
		CLASS_ARM_FIELD,
		PREVIOUS_GROUP_FIELD,
		BRANCH_FIELD,
		INSTITUTION_FIELD,
		OFFERING_FIELD,
	):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	return fields


def _friendly_group_name(row: dict | frappe._dict) -> str:
	return str(row.get(DISPLAY_NAME_FIELD) or row.get("student_group_name") or row.get("name") or "")


def _attach_group_summary(rows: list[dict]) -> None:
	names = [row.get("name") for row in rows if row.get("name")]
	if not names:
		return
	student_counts = frappe.get_all(
		"Student Group Student",
		filters={"parent": ["in", names], "parenttype": "Student Group", "active": 1},
		fields=["parent", {"COUNT": "name", "as": "record_count"}],
		group_by="parent",
		limit_page_length=max(len(names), 1),
	)
	counts = {row.parent: cint(row.record_count) for row in student_counts}
	identity_names = list(dict.fromkeys(row.get(CLASS_ARM_FIELD) for row in rows if row.get(CLASS_ARM_FIELD)))
	identities = {}
	if identity_names:
		identities = {
			row.name: row
			for row in frappe.get_all(
				CLASS_ARM_DOCTYPE,
				filters={"name": ["in", identity_names]},
				fields=["name", "class_arm_name", "class_arm_code", "default_capacity", "enabled"],
				limit_page_length=len(identity_names),
			)
		}
	for row in rows:
		identity = identities.get(row.get(CLASS_ARM_FIELD))
		row["display_name"] = identity.class_arm_name if identity else _friendly_group_name(row)
		row["class_arm_identity"] = dict(identity) if identity else None
		row["student_count"] = counts.get(row.get("name"), 0)
		row["instructor_names"] = []


@frappe.whitelist()
def get_class_arms_page(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	search: str | None = None,
	start: int | str = 0,
	page_length: int | str = DEFAULT_PAGE_LENGTH,
) -> dict:
	_require_read()
	branch, selected_branch, branches = _resolve_branch(branch)
	start = max(cint(start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
	filters: dict[str, Any] = {BRANCH_FIELD: branch}
	if str(academic_year or "").strip():
		filters["academic_year"] = str(academic_year).strip()
	if str(academic_term or "").strip():
		filters["academic_term"] = str(academic_term).strip()
	search = str(search or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {
			"name": ["like", like],
			"student_group_name": ["like", like],
			DISPLAY_NAME_FIELD: ["like", like],
			"program": ["like", like],
		}
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		or_filters=or_filters,
		fields=_student_group_fields(),
		order_by="disabled asc, academic_year desc, academic_term desc, student_group_name asc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = [dict(row) for row in rows[:page_length]]
	_attach_group_summary(rows)
	return {
		"selected_branch": selected_branch,
		"allowed_branches": branches,
		"class_arms": rows,
		"filters": {
			"branch": branch,
			"academic_year": str(academic_year or "").strip(),
			"academic_term": str(academic_term or "").strip(),
			"search": search,
		},
		"paging": {
			"start": start,
			"page_length": page_length,
			"has_more": has_more,
			"next_start": start + len(rows),
		},
		"permissions": {
			"can_create": bool(frappe.has_permission("Student Group", "create") and frappe.has_permission(CLASS_ARM_DOCTYPE, "create")),
			"can_write": bool(frappe.has_permission("Student Group", "write")),
		},
	}


def _get_offering(
	offering: str,
	branch: str,
	*,
	require_enrollment: bool = True,
	require_active: bool = True,
) -> frappe._dict:
	doc = frappe.get_doc("EduEdge Program Offering", offering)
	doc.check_permission("read")
	assert_branch_access(doc.school_branch)
	if doc.school_branch != branch:
		frappe.throw(_("Programme Offering must belong to the selected Branch / Campus."), frappe.ValidationError)
	if require_active and not cint(doc.is_active):
		frappe.throw(_("Select an active Programme Offering."), frappe.ValidationError)
	if require_enrollment and not cint(doc.enrollment_enabled):
		frappe.throw(_("Select a Programme Offering that is available for enrollment."), frappe.ValidationError)
	return frappe._dict(
		{
			"name": doc.name,
			"offering_title": doc.offering_title,
			"offering_code": doc.offering_code,
			"school_branch": doc.school_branch,
			"institution": doc.institution,
			"program": doc.program,
			"department": doc.department,
			"academic_year": doc.academic_year,
			"academic_term": doc.academic_term,
			"student_batch": doc.student_batch,
			"study_mode": doc.study_mode,
			"delivery_mode": doc.delivery_mode,
			"start_date": doc.start_date,
			"end_date": doc.end_date,
		}
	)


def _offering_options(branch: str, program: str | None = None) -> list[dict]:
	if not frappe.has_permission("EduEdge Program Offering", "read"):
		return []
	filters: dict[str, Any] = {"school_branch": branch, "is_active": 1, "enrollment_enabled": 1}
	if program:
		filters["program"] = program
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name", "offering_title", "offering_code", "institution", "program", "department",
			"academic_year", "academic_term", "student_batch", "study_mode", "delivery_mode",
			"start_date", "end_date",
		],
		order_by="start_date asc, academic_year asc, offering_title asc",
		page_length=MAX_OPTION_ROWS,
	)
	return [dict(row) for row in rows]


def _course_options(program: str | None) -> list[dict]:
	if not program or not frappe.has_permission("Course", "read"):
		return []
	course_names = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		pluck="course",
		limit_page_length=MAX_OPTION_ROWS,
	)
	course_names = list(dict.fromkeys(name for name in course_names if name))
	if not course_names:
		return []
	meta = frappe.get_meta("Course")
	fields = ["name", "course_name", "course_code"]
	if meta.has_field(DISPLAY_NAME_FIELD):
		fields.append(DISPLAY_NAME_FIELD)
	rows = frappe.get_list(
		"Course",
		filters={"name": ["in", course_names]},
		fields=fields,
		order_by="course_name asc",
		page_length=len(course_names),
	)
	return [
		{
			"name": row.name,
			"label": row.get(DISPLAY_NAME_FIELD) or row.course_name or row.name,
			"course_code": row.get("course_code"),
		}
		for row in rows
	]


def _eligible_students(branch: str, context: frappe._dict, class_arm: str | None = None) -> list[dict]:
	if not frappe.has_permission("Student", "read") or not frappe.has_permission("Program Enrollment", "read"):
		return []
	enrollment_filters: dict[str, Any] = {
		BRANCH_FIELD: branch,
		"docstatus": 1,
		"program": context.program,
		"academic_year": context.academic_year,
	}
	enrollment_meta = frappe.get_meta("Program Enrollment")
	if enrollment_meta.has_field(OFFERING_FIELD):
		enrollment_filters[OFFERING_FIELD] = context.name
	if context.academic_term:
		enrollment_filters["academic_term"] = context.academic_term
	if context.student_batch:
		enrollment_filters["student_batch_name"] = context.student_batch
	enrollments = frappe.get_list(
		"Program Enrollment",
		filters=enrollment_filters,
		fields=["student"],
		page_length=MAX_OPTION_ROWS,
	)
	student_names = [row.student for row in enrollments if row.student]
	if class_arm:
		student_names.extend(
			frappe.get_all(
				"Student Group Student",
				filters={"parent": class_arm, "parenttype": "Student Group", "active": 1},
				pluck="student",
				limit_page_length=MAX_OPTION_ROWS,
			)
		)
	student_names = list(dict.fromkeys(name for name in student_names if name))
	if not student_names:
		return []
	rows = frappe.get_list(
		"Student",
		filters={"name": ["in", student_names], "enabled": 1},
		fields=["name", "student_name", "student_email_id"],
		order_by="student_name asc",
		page_length=len(student_names),
	)
	return [dict(row) for row in rows]


@frappe.whitelist()
def get_class_arm_options(branch: str | None = None, offering: str | None = None, class_arm: str | None = None) -> dict:
	_require_read()
	branch, selected_branch, branches = _resolve_branch(branch)
	context = _get_offering(offering, branch) if offering else frappe._dict()
	identities = []
	if context and frappe.has_permission(CLASS_ARM_DOCTYPE, "read"):
		identities = frappe.get_list(
			CLASS_ARM_DOCTYPE,
			filters={"school_branch": branch, "program": context.program, "enabled": 1},
			fields=["name", "class_arm_name", "class_arm_code", "default_capacity"],
			order_by="class_arm_name asc",
			page_length=MAX_OPTION_ROWS,
		)
	return {
		"selected_branch": selected_branch,
		"allowed_branches": branches,
		"offerings": _offering_options(branch),
		"context": dict(context),
		"class_arm_identities": [dict(row) for row in identities],
		"courses": _course_options(context.get("program")),
		"students": _eligible_students(branch, context, class_arm) if context else [],
		"instructors": [],
	}


@frappe.whitelist()
def get_class_arm(name: str) -> dict:
	_require_read()
	doc = frappe.get_doc("Student Group", name)
	doc.check_permission("read")
	branch = doc.get(BRANCH_FIELD)
	if branch:
		assert_branch_access(branch)
	identity = None
	if doc.get(CLASS_ARM_FIELD):
		identity = frappe.db.get_value(
			CLASS_ARM_DOCTYPE,
			doc.get(CLASS_ARM_FIELD),
			["name", "class_arm_name", "class_arm_code", "default_capacity", "enabled"],
			as_dict=True,
		)
	return {
		"name": doc.name,
		"display_name": identity.class_arm_name if identity else (doc.get(DISPLAY_NAME_FIELD) or doc.student_group_name or doc.name),
		"student_group_name": doc.student_group_name,
		"class_arm_identity": dict(identity) if identity else None,
		"previous_student_group": doc.get(PREVIOUS_GROUP_FIELD),
		"branch": branch,
		"institution": doc.get(INSTITUTION_FIELD),
		"offering": doc.get(OFFERING_FIELD),
		"program": doc.program,
		"academic_year": doc.academic_year,
		"academic_term": doc.academic_term,
		"batch": doc.batch,
		"group_based_on": doc.group_based_on,
		"course": doc.course,
		"max_strength": cint(doc.max_strength),
		"disabled": cint(doc.disabled),
		"students": [
			{"student": row.student, "student_name": row.student_name, "group_roll_number": row.group_roll_number, "active": cint(row.active)}
			for row in doc.get("students") or []
		],
		"instructors": [
			{"instructor": row.instructor, "instructor_name": row.instructor_name}
			for row in doc.get("instructors") or []
		],
		"can_write": bool(doc.has_permission("write")),
	}


def _parse_rows(value: Any, label: str) -> list[dict]:
	if not value:
		return []
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, list):
		frappe.throw(_("{0} must be a list.").format(label), frappe.ValidationError)
	return [dict(row) if isinstance(row, dict) else {"name": row} for row in value]


def _assert_unique(rows: list[dict], fieldname: str, label: str) -> None:
	values = [str(row.get(fieldname) or row.get("name") or "").strip() for row in rows]
	values = [value for value in values if value]
	if len(values) != len(set(values)):
		frappe.throw(_("Duplicate {0} rows are not allowed.").format(label), frappe.DuplicateEntryError)


def _set_operational_context(doc, context: frappe._dict, identity, *, previous_student_group: str | None = None) -> None:
	values = {
		BRANCH_FIELD: context.school_branch,
		INSTITUTION_FIELD: context.institution,
		OFFERING_FIELD: context.name,
		CLASS_ARM_FIELD: identity.name,
		DISPLAY_NAME_FIELD: identity.class_arm_name,
		PREVIOUS_GROUP_FIELD: previous_student_group,
		"program": context.program,
		"academic_year": context.academic_year,
		"academic_term": context.academic_term or None,
		"batch": context.student_batch or None,
	}
	for fieldname, value in values.items():
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, value)


def _set_students(doc, student_rows: list[dict]) -> None:
	doc.set("students", [])
	for row in student_rows:
		student = str(row.get("student") or row.get("name") or "").strip()
		if not student:
			continue
		doc.append(
			"students",
			{
				"student": student,
				"group_roll_number": cint(row.get("group_roll_number")) or None,
				"active": 1,
			},
		)


@frappe.whitelist(methods=["POST"])
def save_class_arm(
	display_name: str,
	branch: str,
	offering: str,
	class_arm: str | None = None,
	group_based_on: str | None = "Batch",
	course: str | None = None,
	max_strength: int | str = 0,
	disabled: int | str = 0,
	students: Any = None,
	instructors: Any = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_class_arm")
	branch, _selected_branch, _branches = _resolve_branch(branch)
	context = _get_offering(offering, branch)
	student_rows = _parse_rows(students, _("Students"))
	instructor_rows = _parse_rows(instructors, _("Instructors"))
	_assert_unique(student_rows, "student", _("Student"))
	if instructor_rows:
		frappe.throw(
			_("Teaching responsibility is managed through Instructor Assignments. Do not attach Instructors directly to a Class Arm."),
			frappe.ValidationError,
		)
	friendly_name = clean_class_arm_name(display_name)
	if not friendly_name:
		frappe.throw(_("Class Arm name is required."), frappe.ValidationError)
	group_based_on = str(group_based_on or "Batch").strip()
	if group_based_on not in {"Batch", "Course", "Activity"}:
		frappe.throw(_("Select a valid grouping basis."), frappe.ValidationError)
	if group_based_on == "Course" and not course:
		frappe.throw(_("Course / Subject is required for a Course-based Class Arm."), frappe.ValidationError)
	if group_based_on != "Course":
		course = None
	capacity = max(cint(max_strength), 0)
	if capacity and len(student_rows) > capacity:
		frappe.throw(_("Selected Students exceed the Class Arm maximum strength."), frappe.ValidationError)

	if class_arm:
		doc = frappe.get_doc("Student Group", class_arm)
		doc.check_permission("write")
		if doc.get(BRANCH_FIELD):
			assert_branch_access(doc.get(BRANCH_FIELD))
		if doc.get(BRANCH_FIELD) and doc.get(BRANCH_FIELD) != branch:
			frappe.throw(_("An existing Class Arm period cannot be moved to another Branch / Campus."), frappe.ValidationError)
		if doc.get(OFFERING_FIELD) and doc.get(OFFERING_FIELD) != offering:
			frappe.throw(_("An existing Class Arm period cannot be moved to another Programme Offering. Prepare a new period instead."), frappe.ValidationError)
		identity_name = doc.get(CLASS_ARM_FIELD)
		if identity_name:
			identity = frappe.get_doc(CLASS_ARM_DOCTYPE, identity_name)
			identity.check_permission("read")
			if clean_class_arm_name(identity.class_arm_name).casefold() != friendly_name.casefold():
				frappe.throw(_("Rename the reusable Class Arm identity separately; an operational period cannot change identity."), frappe.ValidationError)
		else:
			identity = get_or_create_class_arm(
				branch=branch,
				program=context.program,
				friendly_name=friendly_name,
				institution=context.institution,
				default_capacity=capacity,
			)
	else:
		if not frappe.has_permission("Student Group", "create"):
			frappe.throw(_("You are not permitted to create Class Arms."), frappe.PermissionError)
		identity = get_or_create_class_arm(
			branch=branch,
			program=context.program,
			friendly_name=friendly_name,
			institution=context.institution,
			default_capacity=capacity,
		)
		existing = frappe.db.exists(
			"Student Group",
			{CLASS_ARM_FIELD: identity.name, OFFERING_FIELD: context.name},
		)
		if existing:
			frappe.throw(
				_("{0} already has an operational Class Arm for this Programme Offering.").format(identity.class_arm_name),
				frappe.DuplicateEntryError,
			)
		doc = frappe.new_doc("Student Group")
		doc.student_group_name = generate_operational_group_name(
			friendly_name=identity.class_arm_name,
			branch=branch,
			program=context.program,
			offering=context.name,
			academic_year=context.academic_year,
			academic_term=context.academic_term,
		)

	_set_operational_context(doc, context, identity, previous_student_group=doc.get(PREVIOUS_GROUP_FIELD))
	doc.group_based_on = group_based_on
	doc.course = course or None
	doc.max_strength = capacity
	doc.disabled = cint(disabled)
	_set_students(doc, student_rows)
	# Existing native instructor child rows are deliberately left untouched for historical compatibility.
	# New Class Arms never receive Instructor rows; EduEdge Instructor Assignment is authoritative.
	doc.save()
	return {
		"name": doc.name,
		"display_name": identity.class_arm_name,
		"class_arm_identity": identity.name,
		"branch": doc.get(BRANCH_FIELD),
		"offering": doc.get(OFFERING_FIELD),
		"student_count": len(doc.get("students") or []),
		"instructor_count": len(doc.get("instructors") or []),
		"full_form_route": f"/app/student-group/{doc.name}",
	}


def _rollover_plan(source: str, destination_offering: str) -> dict:
	_require_read()
	source_doc = frappe.get_doc("Student Group", source)
	source_doc.check_permission("read")
	branch = source_doc.get(BRANCH_FIELD)
	if not branch:
		frappe.throw(_("Source Class Arm has no Branch / Campus context."), frappe.ValidationError)
	assert_branch_access(branch)
	identity_name = source_doc.get(CLASS_ARM_FIELD)
	if not identity_name:
		frappe.throw(_("Source Class Arm has no reusable Class Arm identity. Run migration before rollover."), frappe.ValidationError)
	identity = frappe.get_doc(CLASS_ARM_DOCTYPE, identity_name)
	identity.check_permission("read")
	if not cint(identity.enabled):
		frappe.throw(_("The reusable Class Arm identity is disabled."), frappe.ValidationError)

	source_offering_name = source_doc.get(OFFERING_FIELD)
	if not source_offering_name:
		frappe.throw(_("Source Class Arm is not linked to a Programme Offering."), frappe.ValidationError)
	source_context = _get_offering(
		source_offering_name,
		branch,
		require_enrollment=False,
		require_active=False,
	)
	destination = _get_offering(destination_offering, branch)
	if destination.institution != source_context.institution or destination.institution != identity.institution:
		frappe.throw(_("Destination Offering must belong to the same Institution."), frappe.ValidationError)
	if destination.program != source_context.program or destination.program != identity.program:
		frappe.throw(_("Destination Offering must be for the same Class / Programme."), frappe.ValidationError)
	if destination.name == source_context.name or not destination_is_later(source_context, destination):
		frappe.throw(_("Select a later Programme Offering for this Class Arm."), frappe.ValidationError)

	existing = frappe.db.exists(
		"Student Group",
		{CLASS_ARM_FIELD: identity.name, OFFERING_FIELD: destination.name},
	)
	source_students = [row.student for row in source_doc.get("students") or [] if row.student and cint(row.active)]
	eligible_rows = _eligible_students(branch, destination)
	eligible_by_name = {row.get("name"): row for row in eligible_rows}
	carried = [eligible_by_name[name] for name in source_students if name in eligible_by_name]
	excluded_names = [name for name in source_students if name not in eligible_by_name]
	excluded = []
	if excluded_names:
		student_rows = frappe.get_list(
			"Student",
			filters={"name": ["in", excluded_names]},
			fields=["name", "student_name"],
			page_length=len(excluded_names),
		)
		excluded_by_name = {row.name: row for row in student_rows}
		excluded = [
			{
				"name": name,
				"student_name": excluded_by_name.get(name).student_name if excluded_by_name.get(name) else name,
				"reason": "No submitted enrollment for the destination Programme Offering",
			}
			for name in excluded_names
		]
	return {
		"source": {
			"name": source_doc.name,
			"display_name": identity.class_arm_name,
			"offering": source_context.name,
			"offering_title": source_context.offering_title,
			"academic_year": source_context.academic_year,
			"academic_term": source_context.academic_term,
		},
		"destination": dict(destination),
		"class_arm_identity": {
			"name": identity.name,
			"class_arm_name": identity.class_arm_name,
			"class_arm_code": identity.class_arm_code,
		},
		"existing_student_group": existing,
		"eligible_students": carried,
		"excluded_students": excluded,
		"eligible_count": len(carried),
		"excluded_count": len(excluded),
	}


@frappe.whitelist(methods=["POST"])
def preview_class_arm_rollover(source: str, destination_offering: str) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="preview_class_arm_rollover")
	return _rollover_plan(source, destination_offering)


@frappe.whitelist(methods=["POST"])
def execute_class_arm_rollover(source: str, destination_offering: str) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="execute_class_arm_rollover")
	if not frappe.has_permission("Student Group", "create"):
		frappe.throw(_("You are not permitted to create Class Arm periods."), frappe.PermissionError)
	plan = _rollover_plan(source, destination_offering)
	if plan.get("existing_student_group"):
		return {
			"status": "existing",
			"name": plan["existing_student_group"],
			"display_name": plan["class_arm_identity"]["class_arm_name"],
			"eligible_count": plan["eligible_count"],
			"excluded_count": plan["excluded_count"],
		}

	source_doc = frappe.get_doc("Student Group", source)
	identity = frappe.get_doc(CLASS_ARM_DOCTYPE, plan["class_arm_identity"]["name"])
	destination = frappe._dict(plan["destination"])
	doc = frappe.new_doc("Student Group")
	doc.student_group_name = generate_operational_group_name(
		friendly_name=identity.class_arm_name,
		branch=destination.school_branch,
		program=destination.program,
		offering=destination.name,
		academic_year=destination.academic_year,
		academic_term=destination.academic_term,
	)
	_set_operational_context(doc, destination, identity, previous_student_group=source_doc.name)
	doc.group_based_on = source_doc.group_based_on
	doc.course = source_doc.course
	doc.max_strength = source_doc.max_strength
	doc.disabled = source_doc.disabled
	_set_students(doc, [{"student": row.get("name")} for row in plan["eligible_students"]])
	doc.save()
	return {
		"status": "created",
		"name": doc.name,
		"display_name": identity.class_arm_name,
		"source": source_doc.name,
		"destination_offering": destination.name,
		"eligible_count": plan["eligible_count"],
		"excluded_count": plan["excluded_count"],
		"excluded_students": plan["excluded_students"],
		"full_form_route": f"/app/student-group/{doc.name}",
	}
