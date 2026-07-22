from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_operations import (
	before_validate_course_schedule,
	before_validate_room,
	before_validate_student_attendance,
	before_validate_student_group as _before_validate_student_group,
)
from eduedge.education.academic_validation import (
	before_validate_program_enrollment_context,
	before_validate_student_applicant_context,
)
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import (
	get_context_branch,
	validate_program_enrollment,
	validate_student_admission,
	validate_student_applicant,
)
from eduedge.services.branch_context import get_allowed_school_branches


def before_naming_student_admission(doc, method=None) -> None:
	_assign_branch(doc)
	_validate_branch(doc)
	if not doc.title and doc.academic_year and doc.get(BRANCH_FIELD):
		branch_label = frappe.db.get_value(
			"EduEdge School Branch", doc.get(BRANCH_FIELD), "branch_name"
		) or doc.get(BRANCH_FIELD)
		doc.title = _("Admissions for {0} - {1}").format(doc.academic_year, branch_label)


def before_validate_student_admission(doc, method=None) -> None:
	_assign_branch(doc)
	_validate_branch(doc)
	validate_student_admission(doc)


def before_validate_student_applicant(doc, method=None) -> None:
	admission_branch = _linked_value(
		"Student Admission", getattr(doc, "student_admission", None), BRANCH_FIELD
	)
	if not doc.get(OFFERING_FIELD):
		_assign_branch(doc, preferred_branch=admission_branch)
	before_validate_student_applicant_context(doc)
	_validate_branch(doc)
	if admission_branch and doc.get(BRANCH_FIELD) != admission_branch:
		frappe.throw(
			_("Student Applicant Branch must match the selected Student Admission Branch."),
			frappe.ValidationError,
		)
	validate_student_applicant(doc)


def before_validate_student(doc, method=None) -> None:
	applicant_branch = _linked_value(
		"Student Applicant", getattr(doc, "student_applicant", None), BRANCH_FIELD
	)
	_assign_branch(doc, preferred_branch=applicant_branch)
	_validate_branch(doc)
	if applicant_branch and doc.get(BRANCH_FIELD) != applicant_branch:
		frappe.throw(
			_("Student Primary Branch must match the originating Student Applicant Branch."),
			frappe.ValidationError,
		)
	# Student Branch is only a primary/home responsibility context. Submitted
	# Programme Enrollments may legitimately belong to other Branches or Campuses.


def before_validate_program_enrollment(doc, method=None) -> None:
	student_branch = _linked_value("Student", getattr(doc, "student", None), BRANCH_FIELD)
	if not doc.get(OFFERING_FIELD):
		_assign_branch(doc, preferred_branch=student_branch)
	before_validate_program_enrollment_context(doc)
	_validate_branch(doc)
	validate_program_enrollment(doc)


def before_validate_student_group(doc, method=None) -> None:
	_before_validate_student_group(doc, method)


def _assign_branch(doc, preferred_branch: str | None = None) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return
	if doc.get(BRANCH_FIELD):
		return
	branch = preferred_branch or get_context_branch()
	if branch:
		doc.set(BRANCH_FIELD, branch)


def _validate_branch(doc) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return
	branch = doc.get(BRANCH_FIELD)
	configured_branch_count = frappe.db.count("EduEdge School Branch", {"enabled": 1})
	if not branch:
		if configured_branch_count:
			frappe.throw(
				_("Select a School Branch / Campus before saving this record."),
				frappe.ValidationError,
			)
		return

	branch_row = frappe.db.get_value(
		"EduEdge School Branch", branch, ["name", "enabled"], as_dict=True
	)
	if not branch_row or not branch_row.enabled:
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

	if frappe.session.user in {"Guest", "Administrator"}:
		return
	if "System Manager" in set(frappe.get_roles(frappe.session.user)):
		return
	allowed = {row["name"] for row in get_allowed_school_branches()}
	if branch not in allowed:
		frappe.throw(
			_("You do not have access to School Branch / Campus {0}.").format(branch),
			frappe.PermissionError,
		)


def _linked_value(doctype: str, name: str | None, fieldname: str) -> str | None:
	if not name:
		return None
	return frappe.db.get_value(doctype, name, fieldname)
