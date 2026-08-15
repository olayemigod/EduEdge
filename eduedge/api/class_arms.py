from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.class_arm_identity import (
	CLASS_ARM_DOCTYPE,
	CLASS_ARM_FIELD,
	DISPLAY_NAME_FIELD,
	PREVIOUS_GROUP_FIELD,
	clean_class_arm_name,
	generate_operational_group_name,
	get_or_create_class_arm,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, resolve_program_offering_period_dates
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
		"name", "student_group_name", "group_based_on", "program", "course",
		"academic_year", "academic_term", "batch", "max_strength", "disabled", "modified",
	]
	for fieldname in (
		DISPLAY_NAME_FIELD, CLASS_ARM_FIELD, PREVIOUS_GROUP_FIELD,
		BRANCH_FIELD, INSTITUTION_FIELD, OFFERING_FIELD,
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
		row["legacy_term_bound"] = bool(row.get("academic_term"))


@frappe.whitelist()
def get_class_arms_page(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,  # accepted only for old bookmarked URLs
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
		order_by="disabled asc, academic_year desc, student_group_name asc, modified desc",
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
	allow_legacy_term: bool = False,
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
	if doc.academic_term and not allow_legacy_term:
		frappe.throw(
			_("Select a sessional Programme Offering. Term-bound Offerings are retained only as legacy academic history."),
			frappe.ValidationError,
		)
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
			"is_active": cint(doc.is_active),
			"enrollment_enabled": cint(doc.enrollment_enabled),
		}
	)


def _offering_options(branch: str, academic_year: str | None = None, program: str | None = None) -> list[dict]:
	if not frappe.has_permission("EduEdge Program Offering", "read"):
		return []
	filters: dict[str, Any] = {
		"school_branch": branch,
		"is_active": 1,
		"enrollment_enabled": 1,
		"academic_term": ["is", "not set"],
	}
	if academic_year:
		filters["academic_year"] = academic_year
	if program:
		filters["program"] = program
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name", "offering_title", "offering_code", "institution", "program", "department",
			"academic_year", "student_batch", "study_mode", "delivery_mode", "start_date", "end_date",
		],
		order_by="academic_year desc, program asc, offering_title asc",
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
				filters={"parent": class_arm, "parenttype": "Student Group"},
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
		"academic_years": _academic_year_options(),
		"context": dict(context),
		"class_arm_identities": [dict(row) for row in identities],
		"courses": _course_options(context.get("program")),
		"students": _eligible_students(branch, context, class_arm) if context else [],
		"instructors": [],
	}


def _academic_year_options() -> list[dict]:
	if not frappe.has_permission("Academic Year", "read"):
		return []
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Year",
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc, name desc",
			page_length=MAX_OPTION_ROWS,
		)
	]


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
	legacy = bool(doc.academic_term)
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
		"legacy_term_bound": legacy,
		"students": [
			{"student": row.student, "student_name": row.student_name, "group_roll_number": row.group_roll_number, "active": cint(row.active)}
			for row in doc.get("students") or []
		],
		"instructors": [],
		"can_write": bool(doc.has_permission("write") and not legacy),
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
	if context.academic_term:
		frappe.throw(_("Class Arms require a sessional Programme Offering."), frappe.ValidationError)
	values = {
		BRANCH_FIELD: context.school_branch,
		INSTITUTION_FIELD: context.institution,
		OFFERING_FIELD: context.name,
		CLASS_ARM_FIELD: identity.name,
		DISPLAY_NAME_FIELD: identity.class_arm_name,
		PREVIOUS_GROUP_FIELD: previous_student_group,
		"program": context.program,
		"academic_year": context.academic_year,
		"academic_term": None,
		"batch": context.student_batch or None,
	}
	for fieldname, value in values.items():
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, value)


def _merge_students(doc, student_rows: list[dict]) -> None:
	"""Update a session roster without deleting historical child rows."""
	selected = {}
	for row in student_rows:
		student = str(row.get("student") or row.get("name") or "").strip()
		if student:
			selected[student] = row

	existing = {row.student: row for row in doc.get("students") or [] if row.student}
	for student, child in existing.items():
		incoming = selected.pop(student, None)
		if incoming is None:
			child.active = 0
			continue
		child.active = 1
		roll = cint(incoming.get("group_roll_number"))
		child.group_roll_number = roll or None
	for student, incoming in selected.items():
		doc.append(
			"students",
			{
				"student": student,
				"group_roll_number": cint(incoming.get("group_roll_number")) or None,
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
		if doc.academic_term:
			frappe.throw(
				_("Legacy term-bound Class Arms are historical. Create or prepare the sessional Class Arm instead of editing this period record."),
				frappe.ValidationError,
			)
		if doc.get(BRANCH_FIELD):
			assert_branch_access(doc.get(BRANCH_FIELD))
		if doc.get(BRANCH_FIELD) != branch or doc.get(OFFERING_FIELD) != offering:
			frappe.throw(_("An existing Class Arm cannot be moved to another Branch, Offering, or Academic Session."), frappe.ValidationError)
		identity = frappe.get_doc(CLASS_ARM_DOCTYPE, doc.get(CLASS_ARM_FIELD))
		identity.check_permission("read")
		if clean_class_arm_name(identity.class_arm_name).casefold() != friendly_name.casefold():
			frappe.throw(_("Rename the reusable Class Arm identity separately; a session record cannot change identity."), frappe.ValidationError)
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
			{CLASS_ARM_FIELD: identity.name, OFFERING_FIELD: context.name, "academic_term": ["is", "not set"]},
		)
		if existing:
			frappe.throw(
				_("{0} already exists for this Academic Session and Programme Offering.").format(identity.class_arm_name),
				frappe.DuplicateEntryError,
			)
		doc = frappe.new_doc("Student Group")
		doc.student_group_name = generate_operational_group_name(
			friendly_name=identity.class_arm_name,
			branch=branch,
			program=context.program,
			offering=context.name,
			academic_year=context.academic_year,
		)

	_set_operational_context(doc, context, identity, previous_student_group=doc.get(PREVIOUS_GROUP_FIELD))
	doc.group_based_on = group_based_on
	doc.course = course or None
	doc.max_strength = capacity
	doc.disabled = cint(disabled)
	_merge_students(doc, student_rows)
	doc.save()
	return {
		"name": doc.name,
		"display_name": identity.class_arm_name,
		"class_arm_identity": identity.name,
		"branch": doc.get(BRANCH_FIELD),
		"offering": doc.get(OFFERING_FIELD),
		"academic_year": doc.academic_year,
		"student_count": sum(1 for row in doc.get("students") or [] if cint(row.active)),
		"full_form_route": f"/app/student-group/{doc.name}",
	}


def _source_group_sort_key(row: dict) -> tuple[date, date, str]:
	offering = row.get(OFFERING_FIELD)
	start = end = None
	if offering:
		start, end = resolve_program_offering_period_dates(offering)
	return (
		getdate(end) if end else date.min,
		getdate(start) if start else date.min,
		str(row.get("modified") or ""),
	)


def _select_source_groups(branch: str, academic_year: str) -> list[dict]:
	rows = [
		dict(row)
		for row in frappe.get_list(
			"Student Group",
			filters={BRANCH_FIELD: branch, "academic_year": academic_year, "disabled": 0, CLASS_ARM_FIELD: ["is", "set"]},
			fields=_student_group_fields(),
			order_by="modified desc",
			page_length=MAX_OPTION_ROWS,
		)
	]
	by_identity: dict[str, list[dict]] = {}
	for row in rows:
		by_identity.setdefault(row.get(CLASS_ARM_FIELD), []).append(row)
	selected = []
	for identity, candidates in by_identity.items():
		sessional = [row for row in candidates if not row.get("academic_term")]
		if len(sessional) == 1:
			chosen = sessional[0]
			chosen["legacy_source"] = False
			selected.append(chosen)
			continue
		if len(sessional) > 1:
			selected.append({"class_arm_identity": identity, "blocked_reason": "More than one sessional Student Group exists for this Class Arm and Academic Session."})
			continue
		chosen = max(candidates, key=_source_group_sort_key)
		chosen["legacy_source"] = True
		selected.append(chosen)
	return selected


def _offering_signature(row: dict | frappe._dict) -> tuple[str, str, str, str]:
	return (
		str(row.get("program") or ""),
		str(row.get("student_batch") or ""),
		str(row.get("study_mode") or ""),
		str(row.get("delivery_mode") or ""),
	)


def _destination_offerings(branch: str, academic_year: str) -> list[dict]:
	return _offering_options(branch, academic_year=academic_year)


def _match_destination_offering(source_offering: frappe._dict, destinations: list[dict]) -> tuple[dict | None, str | None]:
	exact = [row for row in destinations if _offering_signature(row) == _offering_signature(source_offering)]
	if len(exact) == 1:
		return exact[0], None
	if len(exact) > 1:
		return None, "More than one destination Programme Offering matches the source delivery context."
	program_only = [row for row in destinations if row.get("program") == source_offering.program]
	if len(program_only) == 1:
		return program_only[0], None
	if not program_only:
		return None, "No active sessional destination Programme Offering exists for this Class / Programme."
	return None, "More than one destination Programme Offering exists for this Class / Programme; align cohort and delivery mode first."


def _rollover_row(source: dict, destinations: list[dict]) -> dict:
	if source.get("blocked_reason"):
		return {
			"class_arm_identity": source.get("class_arm_identity"),
			"status": "blocked",
			"reason": source.get("blocked_reason"),
		}
	identity = frappe.db.get_value(
		CLASS_ARM_DOCTYPE,
		source.get(CLASS_ARM_FIELD),
		["name", "class_arm_name", "class_arm_code", "program", "enabled"],
		as_dict=True,
	)
	if not identity or not cint(identity.enabled):
		return {"source": source.get("name"), "status": "blocked", "reason": "Reusable Class Arm identity is missing or disabled."}
	source_offering_name = source.get(OFFERING_FIELD)
	if not source_offering_name:
		return {"source": source.get("name"), "display_name": identity.class_arm_name, "status": "blocked", "reason": "Source Class Arm has no Programme Offering."}
	source_offering = _get_offering(
		source_offering_name,
		source.get(BRANCH_FIELD),
		require_enrollment=False,
		allow_legacy_term=True,
		require_active=False,
	)
	destination, reason = _match_destination_offering(source_offering, destinations)
	if reason:
		return {
			"source": source.get("name"),
			"class_arm_identity": identity.name,
			"display_name": identity.class_arm_name,
			"program": identity.program,
			"status": "blocked",
			"legacy_source": bool(source.get("legacy_source")),
			"reason": reason,
		}
	existing = frappe.db.exists(
		"Student Group",
		{CLASS_ARM_FIELD: identity.name, OFFERING_FIELD: destination["name"], "academic_term": ["is", "not set"]},
	)
	source_students = frappe.get_all(
		"Student Group Student",
		filters={"parent": source.get("name"), "parenttype": "Student Group", "active": 1},
		pluck="student",
		limit_page_length=MAX_OPTION_ROWS,
	)
	destination_context = frappe._dict(destination)
	eligible_rows = _eligible_students(source.get(BRANCH_FIELD), destination_context)
	eligible_by_name = {row.get("name"): row for row in eligible_rows}
	carried = [eligible_by_name[name] for name in source_students if name in eligible_by_name]
	excluded_names = [name for name in source_students if name not in eligible_by_name]
	return {
		"source": source.get("name"),
		"class_arm_identity": identity.name,
		"display_name": identity.class_arm_name,
		"class_arm_code": identity.class_arm_code,
		"program": identity.program,
		"source_offering": source_offering.name,
		"destination_offering": destination["name"],
		"destination_academic_year": destination["academic_year"],
		"status": "existing" if existing else "ready",
		"existing_student_group": existing,
		"legacy_source": bool(source.get("legacy_source")),
		"eligible_students": carried,
		"excluded_students": excluded_names,
		"eligible_count": len(carried),
		"excluded_count": len(excluded_names),
	}


def _session_rollover_plan(branch: str, source_academic_year: str, destination_academic_year: str) -> dict:
	_require_read()
	branch, selected_branch, _branches = _resolve_branch(branch)
	if not source_academic_year or not destination_academic_year:
		frappe.throw(_("Source and destination Academic Sessions are required."), frappe.ValidationError)
	if source_academic_year == destination_academic_year:
		frappe.throw(_("Destination Academic Session must be different from the source Session."), frappe.ValidationError)
	_assert_year_read(source_academic_year)
	_assert_year_read(destination_academic_year)
	source_start = frappe.db.get_value("Academic Year", source_academic_year, "year_start_date")
	destination_start = frappe.db.get_value("Academic Year", destination_academic_year, "year_start_date")
	if source_start and destination_start and getdate(destination_start) <= getdate(source_start):
		frappe.throw(_("Select a later destination Academic Session."), frappe.ValidationError)
	destinations = _destination_offerings(branch, destination_academic_year)
	rows = [_rollover_row(source, destinations) for source in _select_source_groups(branch, source_academic_year)]
	return {
		"branch": selected_branch,
		"source_academic_year": source_academic_year,
		"destination_academic_year": destination_academic_year,
		"rows": rows,
		"summary": {
			"total": len(rows),
			"ready": sum(1 for row in rows if row.get("status") == "ready"),
			"existing": sum(1 for row in rows if row.get("status") == "existing"),
			"blocked": sum(1 for row in rows if row.get("status") == "blocked"),
			"students_to_carry": sum(cint(row.get("eligible_count")) for row in rows),
			"students_excluded": sum(cint(row.get("excluded_count")) for row in rows),
		},
	}


def _assert_year_read(name: str) -> None:
	if not frappe.db.exists("Academic Year", name):
		frappe.throw(_("Academic Session {0} does not exist.").format(name), frappe.DoesNotExistError)
	frappe.get_doc("Academic Year", name).check_permission("read")


@frappe.whitelist(methods=["POST"])
def preview_class_arm_session_rollover(branch: str, source_academic_year: str, destination_academic_year: str) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="preview_class_arm_session_rollover")
	return _session_rollover_plan(branch, source_academic_year, destination_academic_year)


@frappe.whitelist(methods=["POST"])
def execute_class_arm_session_rollover(branch: str, source_academic_year: str, destination_academic_year: str) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="execute_class_arm_session_rollover")
	if not frappe.has_permission("Student Group", "create"):
		frappe.throw(_("You are not permitted to create Class Arms for the next Academic Session."), frappe.PermissionError)
	plan = _session_rollover_plan(branch, source_academic_year, destination_academic_year)
	created = []
	existing = []
	blocked = []
	for row in plan["rows"]:
		if row.get("status") == "existing":
			existing.append(row)
			continue
		if row.get("status") != "ready":
			blocked.append(row)
			continue
		source_doc = frappe.get_doc("Student Group", row["source"])
		identity = frappe.get_doc(CLASS_ARM_DOCTYPE, row["class_arm_identity"])
		destination = _get_offering(row["destination_offering"], branch)
		doc = frappe.new_doc("Student Group")
		doc.student_group_name = generate_operational_group_name(
			friendly_name=identity.class_arm_name,
			branch=branch,
			program=destination.program,
			offering=destination.name,
			academic_year=destination.academic_year,
		)
		_set_operational_context(doc, destination, identity, previous_student_group=source_doc.name)
		doc.group_based_on = source_doc.group_based_on
		doc.course = source_doc.course
		doc.max_strength = source_doc.max_strength
		doc.disabled = 0
		_merge_students(doc, [{"student": student.get("name")} for student in row.get("eligible_students") or []])
		doc.save()
		created.append({
			"name": doc.name,
			"display_name": identity.class_arm_name,
			"source": source_doc.name,
			"destination_offering": destination.name,
			"eligible_count": row.get("eligible_count", 0),
			"excluded_count": row.get("excluded_count", 0),
		})
	return {
		"source_academic_year": source_academic_year,
		"destination_academic_year": destination_academic_year,
		"created": created,
		"existing": existing,
		"blocked": blocked,
		"created_count": len(created),
		"existing_count": len(existing),
		"blocked_count": len(blocked),
	}


@frappe.whitelist(methods=["POST"])
def preview_class_arm_rollover(source: str, destination_offering: str) -> dict:
	frappe.throw(
		_("Term-by-term Class Arm preparation has been retired. Use Bulk Prepare Next Academic Session."),
		frappe.ValidationError,
	)


@frappe.whitelist(methods=["POST"])
def execute_class_arm_rollover(source: str, destination_offering: str) -> dict:
	frappe.throw(
		_("Term-by-term Class Arm preparation has been retired. Use Bulk Prepare Next Academic Session."),
		frappe.ValidationError,
	)
