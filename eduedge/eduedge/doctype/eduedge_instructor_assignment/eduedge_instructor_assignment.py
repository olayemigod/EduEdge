from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

COURSE_REQUIRED_TYPES = {
	"Subject Teacher",
	"Lecturer",
	"Tutor",
	"Practical Instructor",
	"Assistant Instructor",
}


class EduEdgeInstructorAssignment(Document):
	def validate(self) -> None:
		self._validate_dates()
		self._apply_offering_context()
		self._validate_group_context()
		self._validate_instructor_context()
		self._validate_course_context()
		self._validate_duplicate()
		self.assignment_title = self._build_title()

	def _validate_dates(self) -> None:
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

	def _apply_offering_context(self) -> None:
		if not self.program_offering:
			frappe.throw(_("Select a Programme Offering."), frappe.ValidationError)
		offering = frappe.db.get_value(
			"EduEdge Program Offering",
			self.program_offering,
			["name", "institution", "school_branch", "program", "academic_year", "academic_term", "is_active"],
			as_dict=True,
		)
		if not offering or not offering.is_active:
			frappe.throw(_("Select an active Programme Offering."), frappe.ValidationError)
		assert_branch_access(offering.school_branch)
		if self.school_branch and self.school_branch != offering.school_branch:
			frappe.throw(_("Programme Offering must belong to the selected Branch."), frappe.ValidationError)
		if self.institution and self.institution != offering.institution:
			frappe.throw(_("Programme Offering must belong to the selected Institution."), frappe.ValidationError)
		self.school_branch = offering.school_branch
		self.institution = offering.institution
		self.academic_year = offering.academic_year
		self.academic_term = offering.academic_term or None
		self._offering_program = offering.program

	def _validate_group_context(self) -> None:
		if not self.student_group:
			frappe.throw(_("Select a Class Arm / Student Group."), frappe.ValidationError)
		meta = frappe.get_meta("Student Group")
		fields = ["name", "program", "academic_year", "academic_term", "disabled", BRANCH_FIELD]
		if meta.has_field(OFFERING_FIELD):
			fields.append(OFFERING_FIELD)
		group = frappe.db.get_value("Student Group", self.student_group, fields, as_dict=True)
		if not group or group.disabled:
			frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
		if group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Class Arm / Student Group must belong to the selected Branch."), frappe.ValidationError)
		if group.program and group.program != self._offering_program:
			frappe.throw(_("Class Arm / Student Group Programme must match the Programme Offering."), frappe.ValidationError)
		if group.academic_year and group.academic_year != self.academic_year:
			frappe.throw(_("Class Arm / Student Group Academic Session must match the Programme Offering."), frappe.ValidationError)
		if group.academic_term and group.academic_term != self.academic_term:
			frappe.throw(_("Class Arm / Student Group Term must match the Programme Offering."), frappe.ValidationError)
		if meta.has_field(OFFERING_FIELD) and group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != self.program_offering:
			frappe.throw(_("Class Arm / Student Group must belong to the selected Programme Offering."), frappe.ValidationError)

	def _validate_instructor_context(self) -> None:
		if not self.instructor:
			frappe.throw(_("Select an Instructor."), frappe.ValidationError)
		meta = frappe.get_meta("Instructor")
		fields = ["name", "instructor_name", "status"]
		if meta.has_field(INSTITUTION_FIELD):
			fields.append(INSTITUTION_FIELD)
		instructor = frappe.db.get_value("Instructor", self.instructor, fields, as_dict=True)
		if not instructor or instructor.status != "Active":
			frappe.throw(_("Select an active Instructor."), frappe.ValidationError)
		if meta.has_field(INSTITUTION_FIELD) and instructor.get(INSTITUTION_FIELD) and instructor.get(INSTITUTION_FIELD) != self.institution:
			frappe.throw(_("Instructor must belong to the selected Institution."), frappe.ValidationError)
		if not _has_branch_eligibility(self.instructor, self.school_branch, self.valid_from or nowdate(), self.valid_to):
			frappe.throw(
				_("Instructor is not eligible for the selected Branch. Update the Instructor profile or background Branch eligibility first."),
				frappe.ValidationError,
			)
		self.instructor_name = instructor.instructor_name

	def _validate_course_context(self) -> None:
		if self.assignment_type in COURSE_REQUIRED_TYPES and not self.course:
			frappe.throw(_("Course / Subject is required for this assignment type."), frappe.ValidationError)
		if not self.course:
			return
		if not frappe.db.exists("Course", self.course):
			frappe.throw(_("Select a valid Course / Subject."), frappe.ValidationError)
		if self._offering_program and not frappe.db.exists(
			"Program Course",
			{"parent": self._offering_program, "parenttype": "Program", "course": self.course},
		):
			frappe.throw(_("Course / Subject is not configured for the Programme Offering."), frappe.ValidationError)

	def _validate_duplicate(self) -> None:
		if not self.enabled:
			return
		rows = frappe.get_all(
			self.doctype,
			filters={
				"instructor": self.instructor,
				"school_branch": self.school_branch,
				"student_group": self.student_group,
				"assignment_type": self.assignment_type,
				"enabled": 1,
				"name": ["!=", self.name or ""],
			},
			fields=["name", "course", "valid_from", "valid_to"],
		)
		for row in rows:
			if (row.course or "") != (self.course or ""):
				continue
			if _date_ranges_overlap(self.valid_from, self.valid_to, row.valid_from, row.valid_to):
				frappe.throw(_("An overlapping active Instructor Assignment already exists."), frappe.DuplicateEntryError)

	def _build_title(self) -> str:
		parts = [self.instructor_name or self.instructor, self.assignment_type, self.student_group]
		if self.course:
			parts.append(self.course)
		return " · ".join(value for value in parts if value)


def _has_branch_eligibility(instructor: str, branch: str, start_date, end_date=None) -> bool:
	rows = frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor, "school_branch": branch, "enabled": 1},
		fields=["valid_from", "valid_to"],
	)
	return any(_date_ranges_overlap(start_date, end_date, row.valid_from, row.valid_to) for row in rows)


def _date_ranges_overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
	minimum = getdate("1900-01-01")
	maximum = getdate("2999-12-31")
	a_start = getdate(start_a) if start_a else minimum
	a_end = getdate(end_a) if end_a else maximum
	b_start = getdate(start_b) if start_b else minimum
	b_end = getdate(end_b) if end_b else maximum
	return a_start <= b_end and b_start <= a_end
