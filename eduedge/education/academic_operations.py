from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.academic_validation import resolve_exact_offering
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import (
	assert_branch_access,
	get_context_branch,
	validate_program_offering,
)

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Branch Assignment"


def before_validate_student_group(doc, method=None) -> None:
	_assign_branch(doc)
	resolve_exact_offering(doc, purpose="enrollment")
	_validate_branch(doc)
	_validate_term_year(doc.academic_year, doc.academic_term)

	if doc.program:
		validate_program_offering(
			branch=doc.get(BRANCH_FIELD),
			program=doc.program,
			academic_year=doc.academic_year,
			academic_term=doc.academic_term,
			purpose="enrollment",
		)

	for row in doc.get("students") or []:
		if not row.student or not getattr(row, "active", 1):
			continue
		_validate_student_group_enrollment(doc, row.student)

	for row in doc.get("instructors") or []:
		if row.instructor:
			assert_instructor_assignment(
				row.instructor,
				doc.get(BRANCH_FIELD),
				reference_date=nowdate(),
			)


def _validate_student_group_enrollment(doc, student: str) -> None:
	filters = {
		"student": student,
		"docstatus": 1,
		BRANCH_FIELD: doc.get(BRANCH_FIELD),
	}
	offering = doc.get(OFFERING_FIELD) if doc.meta.has_field(OFFERING_FIELD) else None
	if offering and frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD):
		exact = frappe.db.exists("Program Enrollment", {**filters, OFFERING_FIELD: offering})
		if exact:
			return

	# Compatibility fallback for historical enrollments created before exact Offering linkage.
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
	group_branch = _linked_branch("Student Group", doc.student_group)
	_assign_branch(doc, preferred_branch=group_branch)
	_validate_branch(doc)

	if group_branch and doc.get(BRANCH_FIELD) != group_branch:
		frappe.throw(
			_("Course Schedule Branch must match the selected Student Group Branch."),
			frappe.ValidationError,
		)

	if frappe.db.get_value("Student Group", doc.student_group, "disabled"):
		frappe.throw(_("The selected Student Group is disabled."), frappe.ValidationError)

	room_branch = _linked_branch("Room", doc.room)
	if room_branch and room_branch != doc.get(BRANCH_FIELD):
		frappe.throw(
			_("Room {0} belongs to another School Branch / Campus.").format(doc.room),
			frappe.ValidationError,
		)

	assert_instructor_assignment(
		doc.instructor,
		doc.get(BRANCH_FIELD),
		reference_date=doc.schedule_date or nowdate(),
	)


def before_validate_student_attendance(doc, method=None) -> None:
	schedule_branch = _linked_branch("Course Schedule", doc.course_schedule)
	group_name = doc.student_group
	if doc.course_schedule:
		group_name = frappe.db.get_value("Course Schedule", doc.course_schedule, "student_group")
	group_branch = _linked_branch("Student Group", group_name)
	student_home_branch = _linked_branch("Student", doc.student)

	resolved_branch = schedule_branch or group_branch or student_home_branch
	_assign_branch(doc, preferred_branch=resolved_branch)
	_validate_branch(doc)

	branches = {value for value in (schedule_branch, group_branch) if value}
	if len(branches) > 1 or (branches and doc.get(BRANCH_FIELD) not in branches):
		frappe.throw(
			_("Student Attendance Branch must match the Student Group and Course Schedule."),
			frappe.ValidationError,
		)
	if group_name and doc.student:
		is_member = frappe.db.exists(
			"Student Group Student",
			{
				"parent": group_name,
				"parenttype": "Student Group",
				"student": doc.student,
				"active": 1,
			},
		)
		if not is_member:
			frappe.throw(
				_("Student {0} is not an active member of Student Group {1}.").format(doc.student, group_name),
				frappe.ValidationError,
			)


def assert_instructor_assignment(
	instructor: str,
	branch: str,
	*,
	reference_date: str | None = None,
) -> dict:
	if not instructor or not branch:
		frappe.throw(
			_("Instructor and School Branch / Campus are required."),
			frappe.ValidationError,
		)

	target_date = getdate(reference_date or nowdate())
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			"instructor": instructor,
			"school_branch": branch,
			"enabled": 1,
		},
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
		_("Instructor {0} is not assigned to School Branch / Campus {1} on {2}.").format(
			instructor, branch, target_date
		),
		frappe.ValidationError,
	)


def _assign_branch(doc, preferred_branch: str | None = None) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return
	if doc.get(BRANCH_FIELD):
		return
	branch = preferred_branch or get_context_branch()
	if branch:
		doc.set(BRANCH_FIELD, branch)


def _validate_branch(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if not branch:
		if frappe.db.count("EduEdge School Branch", {"enabled": 1}):
			frappe.throw(
				_("Select a School Branch / Campus before saving this record."),
				frappe.ValidationError,
			)
		return
	assert_branch_access(branch)


def _validate_term_year(academic_year: str | None, academic_term: str | None) -> None:
	if not academic_term:
		return
	actual_year = frappe.db.get_value("Academic Term", academic_term, "academic_year")
	if actual_year != academic_year:
		frappe.throw(
			_("Academic Term {0} does not belong to Academic Year {1}.").format(
				academic_term, academic_year
			),
			frappe.ValidationError,
		)


def _linked_branch(doctype: str, name: str | None) -> str | None:
	if not name:
		return None
	return frappe.db.get_value(doctype, name, BRANCH_FIELD)
