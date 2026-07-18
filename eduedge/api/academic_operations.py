from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_operations import ASSIGNMENT_DOCTYPE
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.platform.access import guard_eduedge_action
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)

ACADEMIC_OPERATOR_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
	"Instructor",
	"Teacher",
}
ATTENDANCE_STATUSES = {"Present", "Absent", "Leave"}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_academic_operator() -> None:
	_require_login()
	if not ACADEMIC_OPERATOR_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(
			_("You are not permitted to manage academic operations."),
			frappe.PermissionError,
		)


def _resolve_branch(branch: str | None = None) -> str:
	resolved = branch or (get_current_school_branch() or {}).get("name") or get_context_branch()
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus first."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved


def _current_academic_defaults() -> tuple[str | None, str | None]:
	return (
		frappe.db.get_single_value("Education Settings", "current_academic_year"),
		frappe.db.get_single_value("Education Settings", "current_academic_term"),
	)


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	_require_academic_operator()
	resolved_branch = _resolve_branch(branch)
	target_date = str(getdate(date or nowdate()))
	academic_year, academic_term = _current_academic_defaults()

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
	group_names = [row.name for row in groups]
	group_strength = _get_group_strength(group_names)
	for row in groups:
		row["student_count"] = group_strength.get(row.name, 0)

	schedule_filters: dict = {
		BRANCH_FIELD: resolved_branch,
		"schedule_date": target_date,
	}
	if student_group:
		schedule_filters["student_group"] = student_group
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
	attendance_summary = _get_attendance_summary(resolved_branch, target_date)
	allowed_branches = get_allowed_school_branches()
	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
		"allowed_branches": allowed_branches,
		"filters": {
			"branch": resolved_branch,
			"date": target_date,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"student_group": student_group,
		},
		"counts": {
			"student_groups": len(groups),
			"assigned_instructors": frappe.db.count(
				ASSIGNMENT_DOCTYPE,
				{"school_branch": resolved_branch, "enabled": 1},
			),
			"schedules": len(schedules),
			"attendance_submitted": attendance_summary["total"],
			"present": attendance_summary["Present"],
			"absent": attendance_summary["Absent"],
			"leave": attendance_summary["Leave"],
		},
		"student_groups": groups,
		"schedules": schedules,
	}


def _get_group_strength(group_names: list[str]) -> dict[str, int]:
	if not group_names:
		return {}
	rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": ["in", group_names], "active": 1},
		fields=["parent", "count(name) as student_count"],
		group_by="parent",
	)
	return {row.parent: int(row.student_count or 0) for row in rows}


def _get_attendance_summary(branch: str, date: str) -> dict:
	rows = frappe.get_all(
		"Student Attendance",
		filters={BRANCH_FIELD: branch, "date": date, "docstatus": 1},
		fields=["status", "count(name) as record_count"],
		group_by="status",
	)
	counts = Counter({row.status: int(row.record_count or 0) for row in rows})
	return {
		"Present": counts["Present"],
		"Absent": counts["Absent"],
		"Leave": counts["Leave"],
		"total": sum(counts.values()),
	}


@frappe.whitelist()
def get_attendance_register(
	student_group: str,
	date: str | None = None,
	course_schedule: str | None = None,
) -> dict:
	_require_academic_operator()
	group = frappe.db.get_value(
		"Student Group",
		student_group,
		["name", "student_group_name", BRANCH_FIELD, "disabled"],
		as_dict=True,
	)
	if not group:
		frappe.throw(_("Student Group does not exist."), frappe.DoesNotExistError)
	assert_branch_access(group.get(BRANCH_FIELD))
	if group.disabled:
		frappe.throw(_("The selected Student Group is disabled."), frappe.ValidationError)

	target_date = str(getdate(date or nowdate()))
	schedule = None
	if course_schedule:
		schedule = frappe.db.get_value(
			"Course Schedule",
			course_schedule,
			[
				"name",
				"student_group",
				"schedule_date",
				"instructor",
				"instructor_name",
				"course",
				BRANCH_FIELD,
			],
			as_dict=True,
		)
		if not schedule:
			frappe.throw(_("Course Schedule does not exist."), frappe.DoesNotExistError)
		if schedule.student_group != student_group:
			frappe.throw(
				_("Course Schedule does not belong to the selected Student Group."),
				frappe.ValidationError,
			)
		if schedule.get(BRANCH_FIELD) != group.get(BRANCH_FIELD):
			frappe.throw(_("Course Schedule belongs to another branch."), frappe.ValidationError)
		target_date = str(getdate(schedule.schedule_date))

	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "parenttype": "Student Group", "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
	)
	existing_filters: dict = {
		"student_group": student_group,
		"docstatus": ["!=", 2],
	}
	if course_schedule:
		existing_filters["course_schedule"] = course_schedule
	else:
		existing_filters.update({"date": target_date, "course_schedule": ["is", "not set"]})

	existing = frappe.get_all(
		"Student Attendance",
		filters=existing_filters,
		fields=["name", "student", "status", "docstatus", "leave_application"],
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
		"branch": group.get(BRANCH_FIELD),
		"student_group": group.name,
		"student_group_name": group.student_group_name,
		"date": target_date,
		"course_schedule": schedule,
		"students": register,
		"submitted_count": sum(1 for row in register if row["locked"]),
		"pending_count": sum(1 for row in register if not row["locked"]),
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
	_require_academic_operator()
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
		if status not in ATTENDANCE_STATUSES:
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
			_(
				"Submitted attendance cannot be changed. Cancel or amend these records first: {0}"
			).format(", ".join(conflicts)),
			frappe.ValidationError,
		)

	should_submit = str(submit).lower() in {"1", "true", "yes", "on"}
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
			doc = frappe.get_doc("Student Attendance", current["attendance_name"])
			doc.status = row["status"]
			updated += 1
		else:
			doc = frappe.new_doc("Student Attendance")
			doc.student = row["student"]
			doc.student_group = student_group
			doc.course_schedule = course_schedule
			doc.date = register["date"]
			doc.set(BRANCH_FIELD, register["branch"])
			created += 1

		doc.flags.ignore_permissions = True
		doc.save()
		if should_submit and doc.docstatus == 0:
			doc.submit()
			submitted += 1

	return {
		"created": created,
		"updated": updated,
		"submitted": submitted,
		"unchanged": unchanged,
		"student_group": student_group,
		"course_schedule": course_schedule,
		"date": register["date"],
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_query(doctype, txt, searchfield, start, page_len, filters):
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = _resolve_branch(filters.get(BRANCH_FIELD))
	group_filters = {BRANCH_FIELD: branch, "disabled": 0}
	if filters.get("academic_year"):
		group_filters["academic_year"] = filters["academic_year"]
	return frappe.get_list(
		"Student Group",
		filters=group_filters,
		or_filters={
			"name": ["like", f"%{txt}%"],
			"student_group_name": ["like", f"%{txt}%"],
			"program": ["like", f"%{txt}%"],
			"course": ["like", f"%{txt}%"],
		},
		fields=["name", "student_group_name", "program", "course"],
		start=int(start),
		page_length=int(page_len),
		order_by="student_group_name asc",
		as_list=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def room_query(doctype, txt, searchfield, start, page_len, filters):
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = _resolve_branch(filters.get(BRANCH_FIELD))
	return frappe.get_list(
		"Room",
		filters={BRANCH_FIELD: branch},
		or_filters={
			"name": ["like", f"%{txt}%"],
			"room_name": ["like", f"%{txt}%"],
			"room_number": ["like", f"%{txt}%"],
		},
		fields=["name", "room_name", "room_number", "seating_capacity"],
		start=int(start),
		page_length=int(page_len),
		order_by="room_name asc",
		as_list=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_student_query(doctype, txt, searchfield, start, page_len, filters):
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = _resolve_branch(filters.get(BRANCH_FIELD))
	group_based_on = filters.get("group_based_on")
	params = {
		"branch": branch,
		"academic_year": filters.get("academic_year"),
		"academic_term": filters.get("academic_term"),
		"program": filters.get("program"),
		"batch": filters.get("batch"),
		"student_category": filters.get("student_category"),
		"course": filters.get("course"),
		"txt": f"%{txt or ''}%",
		"start": int(start),
		"page_len": int(page_len),
	}

	if group_based_on == "Activity":
		return frappe.db.sql(
			f"""
			select student.name, student.student_name
			from `tabStudent` student
			where student.enabled = 1
				and student.`{BRANCH_FIELD}` = %(branch)s
				and (
					student.name like %(txt)s
					or student.student_name like %(txt)s
					or coalesce(student.student_email_id, '') like %(txt)s
				)
			order by student.student_name asc
			limit %(start)s, %(page_len)s
			""",
			params,
		)

	conditions = ["enrollment.docstatus = 1", f"enrollment.`{BRANCH_FIELD}` = %(branch)s"]
	for fieldname in ("academic_year", "academic_term", "program"):
		if filters.get(fieldname):
			conditions.append(f"enrollment.`{fieldname}` = %({fieldname})s")
	if filters.get("batch"):
		conditions.append("enrollment.student_batch_name = %(batch)s")
	if filters.get("student_category"):
		conditions.append("enrollment.student_category = %(student_category)s")

	course_join = ""
	if filters.get("course"):
		course_join = """
		inner join `tabProgram Enrollment Course` enrollment_course
			on enrollment_course.parent = enrollment.name
			and enrollment_course.parenttype = 'Program Enrollment'
			and enrollment_course.course = %(course)s
		"""

	return frappe.db.sql(
		f"""
		select distinct student.name, student.student_name
		from `tabProgram Enrollment` enrollment
		inner join `tabStudent` student on student.name = enrollment.student
		{course_join}
		where {' and '.join(conditions)}
			and student.enabled = 1
			and (
				student.name like %(txt)s
				or student.student_name like %(txt)s
				or coalesce(student.student_email_id, '') like %(txt)s
			)
		order by student.student_name asc
		limit %(start)s, %(page_len)s
		""",
		params,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_member_query(doctype, txt, searchfield, start, page_len, filters):
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	student_group = filters.get("student_group")
	if not student_group:
		return []
	branch = frappe.db.get_value("Student Group", student_group, BRANCH_FIELD)
	assert_branch_access(branch)
	return frappe.db.sql(
		f"""
		select student.name, student.student_name
		from `tabStudent Group Student` group_student
		inner join `tabStudent` student on student.name = group_student.student
		where group_student.parent = %(student_group)s
			and group_student.parenttype = 'Student Group'
			and group_student.active = 1
			and student.`{BRANCH_FIELD}` = %(branch)s
			and (
				student.name like %(txt)s
				or student.student_name like %(txt)s
			)
		order by group_student.group_roll_number asc, student.student_name asc
		limit %(start)s, %(page_len)s
		""",
		{
			"student_group": student_group,
			"branch": branch,
			"txt": f"%{txt or ''}%",
			"start": int(start),
			"page_len": int(page_len),
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_query(doctype, txt, searchfield, start, page_len, filters):
	_require_academic_operator()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	branch = _resolve_branch(filters.get(BRANCH_FIELD))
	reference_date = getdate(filters.get("reference_date") or nowdate())
	return frappe.db.sql(
		"""
		select distinct instructor.name, instructor.instructor_name, instructor.department
		from `tabInstructor` instructor
		inner join `tabEduEdge Instructor Branch Assignment` assignment
			on assignment.instructor = instructor.name
		where assignment.school_branch = %(branch)s
			and assignment.enabled = 1
			and instructor.status = 'Active'
			and (assignment.valid_from is null or assignment.valid_from <= %(reference_date)s)
			and (assignment.valid_to is null or assignment.valid_to >= %(reference_date)s)
			and (
				instructor.name like %(txt)s
				or instructor.instructor_name like %(txt)s
				or coalesce(instructor.department, '') like %(txt)s
			)
		order by instructor.instructor_name asc
		limit %(start)s, %(page_len)s
		""",
		{
			"branch": branch,
			"reference_date": reference_date,
			"txt": f"%{txt or ''}%",
			"start": int(start),
			"page_len": int(page_len),
		},
	)
