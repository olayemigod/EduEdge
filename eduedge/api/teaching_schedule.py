from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.api import academic_operations_safe as operations
from eduedge.api.fuzzy_search import get_bounded_candidates, rank_link_rows
from eduedge.api.instructor_assignment_link_search import (
	_validated_offering,
	search_assignment_class_arms,
)
from eduedge.api.teaching_assignment_options import course_schedule_instructor_query
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignments import _group_offering
from eduedge.education.instructor_scope import get_user_instructor_names, is_limited_instructor_user
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

VALID_VIEWS = {"day", "week", "upcoming", "rooms"}
MAX_LINK_RESULTS = 50


def _date_window(reference_date, view: str):
	day = getdate(reference_date or nowdate())
	if view == "week":
		start = day - timedelta(days=day.weekday())
		return start, start + timedelta(days=6)
	if view == "upcoming":
		return day, day + timedelta(days=30)
	return day, day


def _selected_branch_context(branch: str) -> dict:
	return operations._selected_branch_context(branch)


def _group_labels(names: list[str]) -> dict[str, str]:
	if not names:
		return {}
	rows = frappe.get_list(
		"Student Group",
		filters={"name": ["in", names]},
		fields=["name", "student_group_name"],
		page_length=max(len(names), 1),
	)
	return {row.name: row.student_group_name or row.name for row in rows}


def _course_labels(names: list[str]) -> dict[str, str]:
	if not names:
		return {}
	rows = frappe.get_list(
		"Course",
		filters={"name": ["in", names]},
		fields=["name", "course_name"],
		page_length=max(len(names), 1),
	)
	return {row.name: row.course_name or row.name for row in rows}


def _room_labels(names: list[str]) -> dict[str, str]:
	if not names:
		return {}
	rows = frappe.get_list(
		"Room",
		filters={"name": ["in", names]},
		fields=["name", "room_name"],
		page_length=max(len(names), 1),
	)
	return {row.name: row.room_name or row.name for row in rows}


def _require_schedule_read() -> None:
	operations.base._require_academic_operator()
	if not frappe.has_permission("Course Schedule", "read"):
		frappe.throw(_("You are not permitted to view Teaching Schedules."), frappe.PermissionError)


def _require_schedule_create() -> None:
	operations.base._require_academic_operator()
	if not frappe.has_permission("Course Schedule", "create"):
		frappe.throw(_("You are not permitted to create Teaching Schedules."), frappe.PermissionError)


def _limit(value: int | str | None) -> int:
	return min(max(cint(value) or 20, 1), MAX_LINK_RESULTS)


def _resolved_branch(branch: str) -> str:
	return operations.base._resolve_branch(branch)


def _calendar_for_date(branch: str, reference_date: str) -> dict:
	return resolve_academic_defaults(branch, str(getdate(reference_date or nowdate())))


def _validate_offering_date(branch: str, program_offering: str, reference_date: str):
	offering = _validated_offering(branch, program_offering)
	calendar = _calendar_for_date(branch, reference_date)
	if not calendar.get("academic_year"):
		frappe.throw(
			_("No Academic Session covers the selected Schedule Date for this Branch."),
			frappe.ValidationError,
		)
	if offering.academic_year != calendar.get("academic_year"):
		frappe.throw(
			_("Select a Class / Programme Offering from the Academic Session covering the Schedule Date."),
			frappe.ValidationError,
		)
	if offering.academic_term and calendar.get("academic_term") and offering.academic_term != calendar.get("academic_term"):
		frappe.throw(
			_("Select a Class / Programme Offering from the Term / Semester covering the Schedule Date."),
			frappe.ValidationError,
		)
	return offering


def _schedule_group(branch: str, program_offering: str, student_group: str) -> dict:
	meta = frappe.get_meta("Student Group")
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", "disabled", BRANCH_FIELD]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	row = frappe.db.get_value("Student Group", student_group, fields, as_dict=True)
	if not row or cint(row.disabled):
		frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
	if row.get(BRANCH_FIELD) != branch:
		frappe.throw(_("The selected Class Arm belongs to another Branch / Campus."), frappe.ValidationError)
	resolved_offering = row.get(OFFERING_FIELD) or _group_offering(student_group)
	if resolved_offering != program_offering:
		frappe.throw(_("The selected Class Arm does not belong to the selected Class Intake."), frappe.ValidationError)
	return dict(row)


@frappe.whitelist()
def search_teaching_schedule_offerings(
	branch: str,
	reference_date: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Return active destination Classes for the Branch and Session covering the date."""
	_require_schedule_read()
	resolved_branch = _resolved_branch(branch)
	calendar = _calendar_for_date(resolved_branch, reference_date)
	academic_year = calendar.get("academic_year")
	if not academic_year:
		return []
	rows = get_bounded_candidates(
		"EduEdge Program Offering",
		filters={"school_branch": resolved_branch, "academic_year": academic_year, "is_active": 1},
		fields=["name", "offering_title", "offering_code", "program", "academic_year", "academic_term"],
		query=query,
		search_fields=("offering_title", "offering_code", "program", "academic_year", "academic_term"),
		order_by="offering_title asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		if row.get("academic_term") and calendar.get("academic_term") and row.get("academic_term") != calendar.get("academic_term"):
			continue
		row["value"] = row.get("name")
		row["label"] = row.get("offering_title") or row.get("program") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (row.get("program"), row.get("academic_year"), row.get("academic_term"))
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value", "offering_code"),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_teaching_schedule_class_arms(
	branch: str,
	program_offering: str,
	reference_date: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	_require_schedule_read()
	resolved_branch = _resolved_branch(branch)
	_validate_offering_date(resolved_branch, program_offering, reference_date)
	return search_assignment_class_arms(
		branch=resolved_branch,
		program_offering=program_offering,
		query=query,
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_teaching_schedule_courses(
	branch: str,
	program_offering: str,
	reference_date: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Return only Subjects that are actually configured on the selected Class."""
	_require_schedule_read()
	resolved_branch = _resolved_branch(branch)
	offering = _validate_offering_date(resolved_branch, program_offering, reference_date)
	course_names = frappe.get_all(
		"Program Course",
		filters={"parent": offering.program, "parenttype": "Program"},
		pluck="course",
		limit_page_length=0,
	)
	course_names = sorted({name for name in course_names if name})
	if not course_names:
		return []
	meta = frappe.get_meta("Course")
	fields = ["name", "course_name"]
	search_fields = ["course_name"]
	filters: dict = {"name": ["in", course_names]}
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
		search_fields.append(INSTITUTION_FIELD)
		if offering.institution:
			filters[INSTITUTION_FIELD] = ["in", [offering.institution, ""]]
	rows = get_bounded_candidates(
		"Course",
		filters=filters,
		fields=fields,
		query=query,
		search_fields=tuple(search_fields),
		order_by="course_name asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("course_name") or row.get("name")
		row["description"] = row.get(INSTITUTION_FIELD) or _("Class curriculum")
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value",),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_teaching_schedule_instructors(
	branch: str,
	program_offering: str,
	student_group: str,
	course: str,
	reference_date: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Return only Instructors with a valid teaching responsibility for this exact context."""
	_require_schedule_read()
	resolved_branch = _resolved_branch(branch)
	_validate_offering_date(resolved_branch, program_offering, reference_date)
	_schedule_group(resolved_branch, program_offering, student_group)
	rows = course_schedule_instructor_query(
		"Instructor",
		query or "",
		"instructor_name",
		0,
		_limit(page_length),
		{
			BRANCH_FIELD: resolved_branch,
			"student_group": student_group,
			"course": course,
			"reference_date": reference_date,
		},
	)
	return [
		{"value": row[0], "label": row[1] or row[0], "description": row[2] if len(row) > 2 else ""}
		for row in rows
		if row and row[0]
	]


@frappe.whitelist()
def search_teaching_schedule_rooms(
	branch: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	_require_schedule_read()
	resolved_branch = _resolved_branch(branch)
	rows = get_bounded_candidates(
		"Room",
		filters={BRANCH_FIELD: resolved_branch},
		fields=["name", "room_name", BRANCH_FIELD],
		query=query,
		search_fields=("room_name",),
		order_by="room_name asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("room_name") or row.get("name")
		row["description"] = _("This Branch / Campus")
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value",),
		search_fields=("label",),
		page_length=_limit(page_length),
	)


@frappe.whitelist(methods=["POST"])
def create_teaching_schedule(
	branch: str,
	reference_date: str,
	program_offering: str,
	student_group: str,
	course: str,
	instructor: str,
	room: str,
	from_time: str,
	to_time: str,
) -> dict:
	"""Create one native Course Schedule through EduEdge's governed teaching context."""
	_require_schedule_create()
	resolved_branch = _resolved_branch(branch)
	offering = _validate_offering_date(resolved_branch, program_offering, reference_date)
	group = _schedule_group(resolved_branch, program_offering, student_group)
	if group.get("program") and group.get("program") != offering.program:
		frappe.throw(_("The selected Class Arm does not belong to the selected Class."), frappe.ValidationError)
	if not frappe.db.exists(
		"Program Course",
		{"parent": offering.program, "parenttype": "Program", "course": course},
	):
		frappe.throw(_("The selected Subject is not configured on this Class curriculum."), frappe.ValidationError)

	eligible = search_teaching_schedule_instructors(
		branch=resolved_branch,
		program_offering=program_offering,
		student_group=student_group,
		course=course,
		reference_date=reference_date,
		query=instructor,
		page_length=MAX_LINK_RESULTS,
	)
	if instructor not in {row.get("value") for row in eligible}:
		frappe.throw(
			_("The selected Instructor is not assigned to teach this Subject for the selected Class Arm and date."),
			frappe.ValidationError,
		)

	room_branch = frappe.db.get_value("Room", room, BRANCH_FIELD)
	if not room_branch or room_branch != resolved_branch:
		frappe.throw(_("Select a Room belonging to this Branch / Campus."), frappe.ValidationError)

	doc = frappe.get_doc(
		{
			"doctype": "Course Schedule",
			"student_group": student_group,
			"instructor": instructor,
			"course": course,
			"room": room,
			"schedule_date": str(getdate(reference_date)),
			"from_time": from_time,
			"to_time": to_time,
			BRANCH_FIELD: resolved_branch,
		}
	)
	# Do not bypass Frappe Education validation. Native Course Schedule validation
	# remains authoritative for date, time and Student Group/Instructor/Room clashes.
	doc.insert()

	return {
		"name": doc.name,
		"student_group": doc.student_group,
		"student_group_name": frappe.db.get_value("Student Group", doc.student_group, "student_group_name") or doc.student_group,
		"course": doc.course,
		"course_name": frappe.db.get_value("Course", doc.course, "course_name") or doc.course,
		"instructor": doc.instructor,
		"instructor_name": doc.instructor_name or doc.instructor,
		"room": doc.room,
		"room_name": frappe.db.get_value("Room", doc.room, "room_name") or doc.room,
		"schedule_date": str(doc.schedule_date),
		"from_time": str(doc.from_time or ""),
		"to_time": str(doc.to_time or ""),
		BRANCH_FIELD: doc.get(BRANCH_FIELD),
	}


@frappe.whitelist()
def get_teaching_schedule_context(
	branch: str | None = None,
	reference_date: str | None = None,
	view: str = "day",
) -> dict:
	"""Return a focused, permission-aware view over native Course Schedule records."""
	_require_schedule_read()
	view = str(view or "day").strip().lower()
	if view not in VALID_VIEWS:
		frappe.throw(_("Select a valid Teaching Schedule view."), frappe.ValidationError)

	resolved_branch = operations.base._resolve_branch(branch)
	start_date, end_date = _date_window(reference_date, view)
	limited_instructor = is_limited_instructor_user()
	instructor_names = get_user_instructor_names(required=limited_instructor)

	filters: dict = {
		BRANCH_FIELD: resolved_branch,
		"schedule_date": ["between", [str(start_date), str(end_date)]],
	}
	if limited_instructor:
		filters["instructor"] = ["in", instructor_names]

	schedules = frappe.get_list(
		"Course Schedule",
		filters=filters,
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
			"title",
		],
		order_by="schedule_date asc, from_time asc, student_group asc",
		page_length=500,
	)
	group_labels = _group_labels(sorted({row.student_group for row in schedules if row.student_group}))
	course_labels = _course_labels(sorted({row.course for row in schedules if row.course}))
	room_labels = _room_labels(sorted({row.room for row in schedules if row.room}))
	for row in schedules:
		row["student_group_name"] = group_labels.get(row.student_group) or row.student_group
		row["course_name"] = course_labels.get(row.course) or row.course
		row["room_name"] = room_labels.get(row.room) or row.room

	room_usage = operations._room_usage([dict(row) for row in schedules if str(row.schedule_date) == str(start_date)])
	calendar = resolve_academic_defaults(resolved_branch, str(getdate(reference_date or nowdate())))
	selected_branch = _selected_branch_context(resolved_branch)
	permissions = operations._operations_permissions()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": selected_branch.get("company"),
		"current_branch": get_current_school_branch(),
		"selected_branch": selected_branch,
		"allowed_branches": get_allowed_school_branches(),
		"permissions": permissions,
		"view": view,
		"reference_date": str(getdate(reference_date or nowdate())),
		"start_date": str(start_date),
		"end_date": str(end_date),
		"academic_calendar": {
			**calendar,
			"ready": bool(calendar.get("academic_year") and calendar.get("academic_term")),
		},
		"schedules": [dict(row) for row in schedules],
		"room_usage": room_usage,
		"counts": {
			"schedules": len(schedules),
			"instructors": len({row.instructor for row in schedules if row.instructor}),
			"student_groups": len({row.student_group for row in schedules if row.student_group}),
			"rooms": len({row.room for row in schedules if row.room}),
			"unassigned_rooms": sum(1 for row in schedules if not row.room),
		},
	}
