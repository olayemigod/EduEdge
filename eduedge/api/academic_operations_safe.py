from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api import academic_operations as base
from eduedge.education.academic_operations import ASSIGNMENT_DOCTYPE
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_scope import (
	get_user_instructor_names,
	is_limited_instructor_user,
)
from eduedge.platform.access import guard_eduedge_action
from eduedge.services.academic_calendar import resolve_academic_defaults
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch


def _require_doctype_permission(doctype: str, permission_type: str, message: str) -> None:
	if not frappe.has_permission(doctype, permission_type):
		frappe.throw(_(message), frappe.PermissionError)


def _attendance_permissions() -> dict:
	return {
		"can_read_attendance": bool(frappe.has_permission("Student Attendance", "read")),
		"can_create_attendance": bool(frappe.has_permission("Student Attendance", "create")),
		"can_write_attendance": bool(frappe.has_permission("Student Attendance", "write")),
		"can_submit_attendance": bool(frappe.has_permission("Student Attendance", "submit")),
	}


def _operations_permissions() -> dict:
	permissions = _attendance_permissions()
	permissions.update(
		{
			"can_create_student_group": bool(frappe.has_permission("Student Group", "create")),
			"can_create_course_schedule": bool(frappe.has_permission("Course Schedule", "create")),
			"can_read_rooms": bool(frappe.has_permission("Room", "read")),
			"can_create_rooms": bool(frappe.has_permission("Room", "create")),
			"can_read_instructor_assignments": bool(
				frappe.has_permission(ASSIGNMENT_DOCTYPE, "read")
			),
			"can_write_instructor_assignments": bool(
				frappe.has_permission(ASSIGNMENT_DOCTYPE, "write")
				or frappe.has_permission(ASSIGNMENT_DOCTYPE, "create")
			),
		}
	)
	return permissions


def _require_operations_read() -> None:
	base._require_academic_operator()
	_require_doctype_permission(
		"Student Group",
		"read",
		"You are not permitted to view Classes / Student Groups.",
	)
	_require_doctype_permission(
		"Course Schedule",
		"read",
		"You are not permitted to view Course Schedules.",
	)
	_require_doctype_permission(
		"Student Attendance",
		"read",
		"You are not permitted to view Student Attendance.",
	)


def _selected_branch_context(branch: str) -> dict:
	row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["name", "branch_name", "company", "institution"],
		as_dict=True,
	) or {}
	institution = row.get("institution")
	row["institution_name"] = (
		frappe.db.get_value("EduEdge Institution", institution, "institution_name")
		if institution
		else None
	)
	return row


def _attendance_coverage(
	branch: str,
	date: str,
	schedules: list[dict],
	group_strength: dict[str, int],
	group_labels: dict[str, str],
) -> list[dict]:
	"""Return submitted-attendance coverage for each scheduled session."""
	scheduled_rows = [
		dict(row)
		for row in schedules
		if row.get("name") and row.get("student_group")
	]
	if not scheduled_rows:
		return []

	schedule_names = [row["name"] for row in scheduled_rows]
	rows = frappe.get_list(
		"Student Attendance",
		filters={
			BRANCH_FIELD: branch,
			"date": date,
			"docstatus": 1,
			"course_schedule": ["in", schedule_names],
		},
		fields=[
			"course_schedule",
			"status",
			{"COUNT": "name", "as": "record_count"},
		],
		group_by="course_schedule, status",
		page_length=max(len(schedule_names) * len(base.ATTENDANCE_STATUSES), 1),
	)
	counts: dict[str, Counter] = {name: Counter() for name in schedule_names}
	for row in rows:
		counts.setdefault(row.course_schedule, Counter())[row.status] = int(row.record_count or 0)

	coverage = []
	for schedule in scheduled_rows:
		group = schedule["student_group"]
		expected = int(group_strength.get(group, 0))
		schedule_counts = counts.get(schedule["name"], Counter())
		submitted = sum(schedule_counts.values())
		coverage.append(
			{
				"course_schedule": schedule["name"],
				"course": schedule.get("course"),
				"student_group": group,
				"student_group_name": group_labels.get(group) or group,
				"from_time": schedule.get("from_time"),
				"to_time": schedule.get("to_time"),
				"room": schedule.get("room"),
				"expected": expected,
				"submitted": submitted,
				"present": schedule_counts["Present"],
				"absent": schedule_counts["Absent"],
				"leave": schedule_counts["Leave"],
				"missing": max(expected - submitted, 0),
				"has_attendance": submitted > 0,
				"complete": expected > 0 and submitted >= expected,
			}
		)
	return coverage


def _attendance_summary(branch: str, date: str) -> dict:
	rows = frappe.get_list(
		"Student Attendance",
		filters={BRANCH_FIELD: branch, "date": date, "docstatus": 1},
		fields=["status", {"COUNT": "name", "as": "record_count"}],
		group_by="status",
		page_length=len(base.ATTENDANCE_STATUSES),
	)
	counts = Counter({row.status: int(row.record_count or 0) for row in rows})
	return {
		"Present": counts["Present"],
		"Absent": counts["Absent"],
		"Leave": counts["Leave"],
		"total": sum(counts.values()),
	}


def _room_usage(schedules: list[dict]) -> list[dict]:
	usage: dict[str, dict] = {}
	for schedule in schedules:
		room = schedule.get("room") or "Unassigned"
		item = usage.setdefault(
			room,
			{
				"room": room,
				"is_unassigned": not bool(schedule.get("room")),
				"sessions": 0,
				"first_start": schedule.get("from_time"),
				"last_end": schedule.get("to_time"),
			},
		)
		item["sessions"] += 1
		if schedule.get("from_time") and (
			not item.get("first_start") or schedule.get("from_time") < item.get("first_start")
		):
			item["first_start"] = schedule.get("from_time")
		if schedule.get("to_time") and (
			not item.get("last_end") or schedule.get("to_time") > item.get("last_end")
		):
			item["last_end"] = schedule.get("to_time")
	return sorted(usage.values(), key=lambda row: (row["is_unassigned"], row["room"]))


def _calendar_display(calendar_context: dict, target_date: str) -> dict:
	context = dict(calendar_context or {})
	context["reference_date"] = target_date
	context["calendar_gap"] = bool(
		context.get("source") == "institution_calendar"
		and context.get("calendar")
		and not context.get("academic_term")
	)
	context["period_label"] = context.get("academic_term") or "No configured period"
	return context


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	_require_operations_read()
	resolved_branch = base._resolve_branch(branch)
	target_date = str(getdate(date or nowdate()))
	calendar_context = _calendar_display(resolve_academic_defaults(resolved_branch, target_date), target_date)
	academic_year = calendar_context.get("academic_year")
	academic_term = calendar_context.get("academic_term")
	limited_instructor = is_limited_instructor_user()
	instructor_names = get_user_instructor_names(required=limited_instructor)

	group_filters: dict = {BRANCH_FIELD: resolved_branch, "disabled": 0}
	if academic_year:
		group_filters["academic_year"] = academic_year
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=[
			"name",
			"student_group_name",
			"group_based_on",
			"program",
			"course",
			"academic_year",
			"academic_term",
			"max_strength",
		],
		order_by="student_group_name asc",
		page_length=100,
	)
	if academic_term:
		groups = [row for row in groups if not row.academic_term or row.academic_term == academic_term]

	schedule_filters: dict = {
		BRANCH_FIELD: resolved_branch,
		"schedule_date": target_date,
	}
	if student_group:
		schedule_filters["student_group"] = student_group
	if limited_instructor:
		schedule_filters["instructor"] = ["in", instructor_names]
	schedules = frappe.get_list(
		"Course Schedule",
		filters=schedule_filters,
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
		order_by="from_time asc",
		page_length=200,
	)
	if limited_instructor:
		assigned_groups = {row.student_group for row in schedules if row.student_group}
		groups = [row for row in groups if row.name in assigned_groups]

	group_names = [row.name for row in groups]
	group_strength = base._get_group_strength(group_names)
	group_labels = {}
	for row in groups:
		row["student_count"] = group_strength.get(row.name, 0)
		group_labels[row.name] = row.student_group_name

	attendance_summary = _attendance_summary(resolved_branch, target_date)
	attendance_coverage = _attendance_coverage(
		resolved_branch,
		target_date,
		schedules,
		group_strength,
		group_labels,
	)
	room_usage = _room_usage(schedules)
	allowed_branches = get_allowed_school_branches()
	current_branch = get_current_school_branch()
	selected_branch = _selected_branch_context(resolved_branch)
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	missing_registers = sum(1 for row in attendance_coverage if not row["has_attendance"])
	incomplete_registers = sum(1 for row in attendance_coverage if row["has_attendance"] and not row["complete"])
	complete_registers = sum(1 for row in attendance_coverage if row["complete"])
	permissions = _operations_permissions()
	assigned_instructors = (
		len(instructor_names)
		if limited_instructor
		else (
			frappe.db.count(
				ASSIGNMENT_DOCTYPE,
				{"school_branch": resolved_branch, "enabled": 1},
			)
			if permissions["can_read_instructor_assignments"]
			else 0
		)
	)

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": selected_branch.get("company"),
		"current_branch": current_branch,
		"selected_branch": selected_branch,
		"allowed_branches": allowed_branches,
		"academic_calendar": calendar_context,
		"limited_instructor_scope": limited_instructor,
		"filters": {
			"branch": resolved_branch,
			"date": target_date,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"student_group": student_group,
		},
		"counts": {
			"student_groups": len(groups),
			"assigned_instructors": assigned_instructors,
			"schedules": len(schedules),
			"rooms_used": sum(1 for row in room_usage if not row["is_unassigned"]),
			"unassigned_room_sessions": sum(row["sessions"] for row in room_usage if row["is_unassigned"]),
			"attendance_submitted": attendance_summary["total"],
			"present": attendance_summary["Present"],
			"absent": attendance_summary["Absent"],
			"leave": attendance_summary["Leave"],
			"attendance_complete_registers": complete_registers,
			"attendance_incomplete_registers": incomplete_registers,
			"attendance_missing_registers": missing_registers,
			"attendance_complete_groups": complete_registers,
			"attendance_incomplete_groups": incomplete_registers,
			"attendance_missing_groups": missing_registers,
		},
		"permissions": permissions,
		"student_groups": groups,
		"schedules": schedules,
		"attendance_coverage": attendance_coverage,
		"room_usage": room_usage,
	}


def _get_schedule_row(course_schedule: str) -> frappe._dict:
	doc = frappe.get_doc("Course Schedule", course_schedule)
	doc.check_permission("read")
	return frappe._dict(
		{
			"name": doc.name,
			"student_group": doc.student_group,
			"schedule_date": doc.schedule_date,
			"instructor": doc.instructor,
			"instructor_name": doc.instructor_name,
			"course": doc.course,
			"room": doc.room,
			"from_time": doc.from_time,
			"to_time": doc.to_time,
			BRANCH_FIELD: doc.get(BRANCH_FIELD),
		}
	)


def _resolve_register_schedule(
	student_group: str,
	branch: str,
	target_date: str,
	course_schedule: str | None,
) -> frappe._dict | None:
	limited_instructor = is_limited_instructor_user()
	if course_schedule:
		schedule = _get_schedule_row(course_schedule)
		if schedule.student_group != student_group:
			frappe.throw(
				_("Course Schedule does not belong to the selected Student Group."),
				frappe.ValidationError,
			)
		if schedule.get(BRANCH_FIELD) != branch:
			frappe.throw(_("Course Schedule belongs to another Branch."), frappe.ValidationError)
		return schedule

	filters = {
		"student_group": student_group,
		"schedule_date": target_date,
		BRANCH_FIELD: branch,
	}
	if limited_instructor:
		filters["instructor"] = ["in", get_user_instructor_names(required=True)]
	matching = frappe.get_list(
		"Course Schedule",
		filters=filters,
		fields=[
			"name",
			"student_group",
			"schedule_date",
			"instructor",
			"instructor_name",
			"course",
			"room",
			"from_time",
			"to_time",
			BRANCH_FIELD,
		],
		order_by="from_time asc",
		page_length=3,
	)
	if len(matching) > 1:
		frappe.throw(
			_("More than one Course Schedule exists for this Class and date. Select the exact scheduled session before loading attendance."),
			frappe.ValidationError,
		)
	if limited_instructor and not matching:
		frappe.throw(
			_("Attendance can only be recorded against a Course Schedule assigned to your Instructor profile."),
			frappe.PermissionError,
		)
	return matching[0] if matching else None


@frappe.whitelist()
def get_attendance_register(
	student_group: str,
	date: str | None = None,
	course_schedule: str | None = None,
) -> dict:
	_require_operations_read()
	group_doc = frappe.get_doc("Student Group", student_group)
	group_doc.check_permission("read")
	branch = group_doc.get(BRANCH_FIELD)
	base.assert_branch_access(branch)
	if group_doc.disabled:
		frappe.throw(_("The selected Student Group is disabled."), frappe.ValidationError)

	target_date = str(getdate(date or nowdate()))
	schedule = _resolve_register_schedule(student_group, branch, target_date, course_schedule)
	if schedule:
		target_date = str(getdate(schedule.schedule_date))

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "parenttype": "Student Group", "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
	)
	existing_filters: dict = {
		"student_group": student_group,
		BRANCH_FIELD: branch,
		"date": target_date,
		"docstatus": ["!=", 2],
	}
	if schedule:
		existing_filters["course_schedule"] = schedule.name
	else:
		existing_filters["course_schedule"] = ["is", "not set"]

	existing = frappe.get_list(
		"Student Attendance",
		filters=existing_filters,
		fields=["name", "student", "status", "docstatus", "leave_application"],
		page_length=max(len(students), 1),
	)
	records = {row.student: row for row in existing}
	register = []
	for row in students:
		record = records.get(row.student)
		register.append(
			{
				"student": row.student,
				"student_name": row.student_name,
				"group_roll_number": row.group_roll_number,
				"status": record.status if record else "Present",
				"attendance_name": record.name if record else None,
				"docstatus": int(record.docstatus) if record else 0,
				"locked": bool(record and int(record.docstatus) == 1),
				"leave_application": record.leave_application if record else None,
			}
		)

	return {
		"branch": branch,
		"student_group": group_doc.name,
		"student_group_name": group_doc.student_group_name,
		"date": target_date,
		"course_schedule": schedule,
		"students": register,
		"submitted_count": sum(1 for row in register if row["locked"]),
		"pending_count": sum(1 for row in register if not row["locked"]),
		"permissions": _attendance_permissions(),
	}


@frappe.whitelist()
@guard_eduedge_action("attendance", action="save_attendance_register")
def save_attendance_register(
	student_group: str,
	date: str,
	entries,
	course_schedule: str | None = None,
	submit: int | str | bool = 0,
) -> dict:
	base._require_academic_operator()
	register = get_attendance_register(student_group, date, course_schedule)
	rows = frappe.parse_json(entries) if isinstance(entries, str) else entries
	if not isinstance(rows, list) or not rows:
		frappe.throw(_("Attendance entries are required."), frappe.ValidationError)

	allowed_students = {row["student"] for row in register["students"]}
	seen: set[str] = set()
	normalized: list[dict] = []
	for row in rows:
		student = row.get("student")
		status = row.get("status")
		if student not in allowed_students:
			frappe.throw(
				_("Student {0} is not an active member of this Student Group.").format(student),
				frappe.ValidationError,
			)
		if student in seen:
			frappe.throw(
				_("Student {0} appears more than once in the register.").format(student),
				frappe.ValidationError,
			)
		if status not in base.ATTENDANCE_STATUSES:
			frappe.throw(_("Invalid attendance status for {0}.").format(student), frappe.ValidationError)
		seen.add(student)
		normalized.append({"student": student, "status": status})

	existing = {
		row["student"]: row
		for row in register["students"]
		if row.get("attendance_name")
	}
	conflicts = [
		row["attendance_name"]
		for row in normalized
		if row["student"] in existing
		and existing[row["student"]]["locked"]
		and existing[row["student"]]["status"] != row["status"]
	]
	if conflicts:
		frappe.throw(
			_("Submitted attendance cannot be changed. Cancel or amend these records first: {0}").format(
				", ".join(conflicts)
			),
			frappe.ValidationError,
		)

	should_submit = str(submit).lower() in {"1", "true", "yes", "on"}
	permissions = _attendance_permissions()
	if should_submit and not permissions["can_submit_attendance"]:
		frappe.throw(_("You are not permitted to submit Student Attendance."), frappe.PermissionError)

	schedule_name = (register.get("course_schedule") or {}).get("name")
	created = 0
	updated = 0
	submitted = 0
	unchanged = 0

	for row in normalized:
		current = existing.get(row["student"])
		if current and current["locked"]:
			unchanged += 1
			continue

		if current:
			if not permissions["can_write_attendance"]:
				frappe.throw(_("You are not permitted to edit draft Student Attendance."), frappe.PermissionError)
			doc = frappe.get_doc("Student Attendance", current["attendance_name"])
			doc.check_permission("write")
			doc.status = row["status"]
			updated += 1
		else:
			if not permissions["can_create_attendance"]:
				frappe.throw(_("You are not permitted to create Student Attendance."), frappe.PermissionError)
			doc = frappe.new_doc("Student Attendance")
			doc.student = row["student"]
			doc.student_group = student_group
			doc.course_schedule = schedule_name
			doc.date = register["date"]
			doc.set(BRANCH_FIELD, register["branch"])
			created += 1

		doc.save()
		if should_submit and doc.docstatus == 0:
			doc.check_permission("submit")
			doc.submit()
			submitted += 1

	return {
		"created": created,
		"updated": updated,
		"submitted": submitted,
		"unchanged": unchanged,
		"student_group": student_group,
		"course_schedule": schedule_name,
		"date": register["date"],
	}
