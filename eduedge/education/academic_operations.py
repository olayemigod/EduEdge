from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_hierarchy import _validate_department
from eduedge.education.academic_validation import resolve_exact_offering
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, get_context_branch, validate_program_offering
from eduedge.services.academic_calendar import assert_institution_calendar_context

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Branch Assignment"


def before_validate_student_group(doc, method=None) -> None:
	_assign_branch(doc)
	offering = resolve_exact_offering(doc, purpose="enrollment")
	_validate_branch(doc)
	_validate_term_year(doc.academic_year, doc.academic_term)
	if not doc.program:
		frappe.throw(_("Select a Programme / Class for this Student Group / Class Arm."), frappe.ValidationError)
	_validate_group_program_context(doc, offering)
	_validate_group_course_context(doc)
	if doc.academic_year:
		assert_institution_calendar_context(
			branch=doc.get(BRANCH_FIELD),
			academic_year=doc.academic_year,
			academic_term=doc.academic_term or None,
		)
	validate_program_offering(
		branch=doc.get(BRANCH_FIELD),
		program=doc.program,
		academic_year=doc.academic_year,
		academic_term=doc.academic_term,
		purpose="enrollment",
	)
	for row in doc.get("students") or []:
		if row.student and getattr(row, "active", 1):
			_validate_student_group_enrollment(doc, row.student)
	for row in doc.get("instructors") or []:
		if row.instructor:
			assert_instructor_assignment(row.instructor, doc.get(BRANCH_FIELD), reference_date=nowdate())


def _validate_group_program_context(doc, offering) -> None:
	branch = doc.get(BRANCH_FIELD)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	program_meta = frappe.get_meta("Program")
	fields = ["department"]
	if program_meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	program = frappe.db.get_value("Program", doc.program, fields, as_dict=True)
	if not program:
		frappe.throw(_("Select a valid Programme / Class."), frappe.ValidationError)
	program_institution = program.get(INSTITUTION_FIELD)
	if program_meta.has_field(INSTITUTION_FIELD) and program_institution != institution:
		frappe.throw(_("Programme / Class must belong to the Student Group's Institution."), frappe.ValidationError)
	if not program.department:
		frappe.throw(_("Programme / Class must belong to a Department, Faculty, School, or School Section."), frappe.ValidationError)
	_validate_department(program.department, institution)
	if offering:
		if offering.program != doc.program:
			frappe.throw(_("Student Group Programme / Class must match its Programme Offering."), frappe.ValidationError)
		if offering.department and offering.department != program.department:
			frappe.throw(_("Programme Offering Department must match the Programme / Class."), frappe.ValidationError)
		if offering.school_branch != branch:
			frappe.throw(_("Student Group Branch must match its Programme Offering."), frappe.ValidationError)
		if offering.academic_year != doc.academic_year:
			frappe.throw(_("Student Group Academic Session must match its Programme Offering."), frappe.ValidationError)
		if offering.academic_term and offering.academic_term != doc.academic_term:
			frappe.throw(_("Student Group Term / Semester must match its Programme Offering."), frappe.ValidationError)


def _validate_group_course_context(doc) -> None:
	if not doc.course:
		return
	if not frappe.db.exists("Course", doc.course):
		frappe.throw(_("Select a valid Course / Subject."), frappe.ValidationError)
	if doc.program and not frappe.db.exists(
		"Program Course",
		{"parent": doc.program, "parenttype": "Program", "course": doc.course},
	):
		frappe.throw(
			_("Course / Subject {0} is not configured on Programme / Class {1}.").format(doc.course, doc.program),
			frappe.ValidationError,
		)
	course_meta = frappe.get_meta("Course")
	if course_meta.has_field(INSTITUTION_FIELD):
		course_institution = frappe.db.get_value("Course", doc.course, INSTITUTION_FIELD)
		branch_institution = frappe.db.get_value("EduEdge School Branch", doc.get(BRANCH_FIELD), "institution")
		if course_institution and course_institution != branch_institution:
			frappe.throw(_("Course / Subject must belong to the Student Group's Institution."), frappe.ValidationError)


def _validate_student_group_enrollment(doc, student: str) -> None:
	filters = {"student": student, "docstatus": 1, BRANCH_FIELD: doc.get(BRANCH_FIELD)}
	offering = doc.get(OFFERING_FIELD) if doc.meta.has_field(OFFERING_FIELD) else None
	if offering and frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD):
		if frappe.db.exists("Program Enrollment", {**filters, OFFERING_FIELD: offering}):
			return
	if doc.program:
		filters["program"] = doc.program
	if doc.academic_year:
		filters["academic_year"] = doc.academic_year
	if doc.academic_term:
		filters["academic_term"] = doc.academic_term
	if doc.batch:
		filters["student_batch_name"] = doc.batch
	if not frappe.db.exists("Program Enrollment", filters):
		frappe.throw(
			_("Student {0} has no submitted enrollment matching this Programme Offering and Branch.").format(student),
			frappe.ValidationError,
		)


def before_validate_room(doc, method=None) -> None:
	_assign_branch(doc)
	_validate_branch(doc)


def before_validate_course_schedule(doc, method=None) -> None:
	group_context = (
		frappe.db.get_value(
			"Student Group",
			doc.student_group,
			[BRANCH_FIELD, "academic_year", "academic_term", "disabled", "program", "course"],
			as_dict=True,
		)
		if doc.student_group
		else None
	)
	group_branch = (group_context or {}).get(BRANCH_FIELD)
	_assign_branch(doc, preferred_branch=group_branch)
	_validate_branch(doc)
	if group_branch and doc.get(BRANCH_FIELD) != group_branch:
		frappe.throw(_("Course Schedule Branch must match the selected Student Group Branch."), frappe.ValidationError)
	if not group_context:
		frappe.throw(_("Select a valid Student Group / Class Arm / Level."), frappe.ValidationError)
	if group_context.disabled:
		frappe.throw(_("The selected Student Group is disabled."), frappe.ValidationError)
	if not group_context.academic_year:
		frappe.throw(_("The selected Student Group has no Academic Session. Correct the group before scheduling a lesson."), frappe.ValidationError)
	if not doc.schedule_date:
		frappe.throw(_("Schedule Date is required."), frappe.ValidationError)
	assert_institution_calendar_context(
		branch=doc.get(BRANCH_FIELD),
		academic_year=group_context.academic_year,
		academic_term=group_context.academic_term or None,
		reference_date=doc.schedule_date,
	)
	_validate_schedule_course(doc, group_context)
	room_branch = _linked_branch("Room", doc.room)
	if room_branch and room_branch != doc.get(BRANCH_FIELD):
		frappe.throw(_("Room {0} belongs to another School Branch / Campus.").format(doc.room), frappe.ValidationError)
	assert_instructor_assignment(doc.instructor, doc.get(BRANCH_FIELD), reference_date=doc.schedule_date or nowdate())


def _validate_schedule_course(doc, group_context) -> None:
	if not doc.course:
		frappe.throw(_("Course / Subject is required for a Course Schedule."), frappe.ValidationError)
	if group_context.course and doc.course != group_context.course:
		frappe.throw(_("Course Schedule Course must match the selected Course-based Student Group."), frappe.ValidationError)
	if group_context.program and not frappe.db.exists(
		"Program Course",
		{"parent": group_context.program, "parenttype": "Program", "course": doc.course},
	):
		frappe.throw(
			_("Course / Subject {0} is not configured on Programme / Class {1}.").format(doc.course, group_context.program),
			frappe.ValidationError,
		)


def before_validate_student_attendance(doc, method=None) -> None:
	_resolve_exact_attendance_schedule(doc)
	schedule = (
		frappe.db.get_value("Course Schedule", doc.course_schedule, ["name", "student_group", "schedule_date", BRANCH_FIELD], as_dict=True)
		if doc.course_schedule else None
	)
	if doc.course_schedule and not schedule:
		frappe.throw(_("Course Schedule does not exist."), frappe.DoesNotExistError)
	if schedule:
		if doc.student_group and doc.student_group != schedule.student_group:
			frappe.throw(_("Student Attendance Student Group must match the selected Course Schedule."), frappe.ValidationError)
		doc.student_group = schedule.student_group
		if doc.date and getdate(doc.date) != getdate(schedule.schedule_date):
			frappe.throw(_("Student Attendance Date must match the selected Course Schedule date."), frappe.ValidationError)
		doc.date = schedule.schedule_date
	group_name = doc.student_group
	group_branch = _linked_branch("Student Group", group_name)
	student_home_branch = _linked_branch("Student", doc.student)
	resolved_branch = (schedule or {}).get(BRANCH_FIELD) or group_branch or student_home_branch
	_assign_branch(doc, preferred_branch=resolved_branch)
	_validate_branch(doc)
	branches = {value for value in ((schedule or {}).get(BRANCH_FIELD), group_branch) if value}
	if len(branches) > 1 or (branches and doc.get(BRANCH_FIELD) not in branches):
		frappe.throw(_("Student Attendance Branch must match the Student Group and Course Schedule."), frappe.ValidationError)
	if group_name and doc.student:
		is_member = frappe.db.exists(
			"Student Group Student",
			{"parent": group_name, "parenttype": "Student Group", "student": doc.student, "active": 1},
		)
		if not is_member:
			frappe.throw(_("Student {0} is not an active member of Student Group {1}.").format(doc.student, group_name), frappe.ValidationError)
	_validate_attendance_duplicate(doc)


def _resolve_exact_attendance_schedule(doc) -> None:
	"""Bind direct attendance to one exact scheduled session, or fail closed.

	If the caller already supplied a Course Schedule, the normal validation path
	below remains authoritative. Without one, unscheduled attendance is allowed only
	when no matching schedule exists for the same Student Group and date.
	"""
	if doc.course_schedule or not doc.student_group or not doc.date:
		return
	filters = {"student_group": doc.student_group, "schedule_date": doc.date}
	group_branch = _linked_branch("Student Group", doc.student_group)
	if group_branch and frappe.get_meta("Course Schedule").has_field(BRANCH_FIELD):
		filters[BRANCH_FIELD] = group_branch
	matches = frappe.get_all(
		"Course Schedule",
		filters=filters,
		fields=["name"],
		order_by="from_time asc, name asc",
		limit_page_length=2,
	)
	if len(matches) == 1:
		doc.course_schedule = matches[0].name
		return
	if len(matches) > 1:
		frappe.throw(
			_("More than one Course Schedule exists for this Class and date. Select the exact scheduled session before saving attendance."),
			frappe.ValidationError,
		)


def _validate_attendance_duplicate(doc) -> None:
	if not doc.student or not doc.student_group or not doc.date:
		return
	lock_doctype = "Course Schedule" if doc.course_schedule else "Student Group"
	lock_name = doc.course_schedule or doc.student_group
	frappe.db.sql(f"select name from `tab{lock_doctype}` where name = %s for update", (lock_name,))
	filters = {
		"student": doc.student,
		"student_group": doc.student_group,
		"date": doc.date,
		"docstatus": ["!=", 2],
		"name": ["!=", doc.name or ""],
	}
	filters["course_schedule"] = doc.course_schedule if doc.course_schedule else ["is", "not set"]
	if frappe.db.exists("Student Attendance", filters):
		frappe.throw(_("Student Attendance already exists for this Student, Class and scheduled session."), frappe.DuplicateEntryError)


def assert_instructor_assignment(instructor: str, branch: str, *, reference_date: str | None = None) -> dict:
	if not instructor or not branch:
		frappe.throw(_("Instructor and School Branch / Campus are required."), frappe.ValidationError)
	target_date = getdate(reference_date or nowdate())
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={"instructor": instructor, "school_branch": branch, "enabled": 1},
		fields=["name", "valid_from", "valid_to", "is_primary"],
		order_by="is_primary desc, modified desc",
	)
	for row in rows:
		if row.valid_from and getdate(row.valid_from) > target_date:
			continue
		if row.valid_to and getdate(row.valid_to) < target_date:
			continue
		return row
	frappe.throw(
		_("Instructor {0} is not assigned to School Branch / Campus {1} on {2}.").format(instructor, branch, target_date),
		frappe.ValidationError,
	)


def _assign_branch(doc, preferred_branch: str | None = None) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD) or doc.get(BRANCH_FIELD):
		return
	branch = preferred_branch or get_context_branch()
	if branch:
		doc.set(BRANCH_FIELD, branch)


def _validate_branch(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if not branch:
		if frappe.db.count("EduEdge School Branch", {"enabled": 1}):
			frappe.throw(_("Select a School Branch / Campus before saving this record."), frappe.ValidationError)
		return
	assert_branch_access(branch)


def _validate_term_year(academic_year: str | None, academic_term: str | None) -> None:
	if not academic_term:
		return
	actual_year = frappe.db.get_value("Academic Term", academic_term, "academic_year")
	if actual_year != academic_year:
		frappe.throw(_("Academic Term {0} does not belong to Academic Year {1}.").format(academic_term, academic_year), frappe.ValidationError)


def _linked_branch(doctype: str, name: str | None) -> str | None:
	return frappe.db.get_value(doctype, name, BRANCH_FIELD) if name else None
