from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_operations import (
	before_validate_course_schedule as _before_validate_course_schedule,
	before_validate_room,
	before_validate_student_attendance,
	before_validate_student_group as _before_validate_student_group,
)
from eduedge.education.academic_validation import (
	before_validate_program_enrollment_context,
	before_validate_student_applicant_context,
)
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.academic_progression import (
	validate_progression_level_on_enrollment,
	validate_progression_level_on_student_group,
)
from eduedge.education.class_arm_identity import validate_student_group_class_arm
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.enrollment_progression_fields import (
	PROGRESSION_OUTCOME_FIELD,
	PROGRESSION_SOURCE_FIELD,
)
from eduedge.education.instructor_assignments import assert_schedule_instructor_assignment
from eduedge.education.offerings import (
	get_context_branch,
	validate_program_enrollment,
	validate_student_admission,
	validate_student_applicant,
)
from eduedge.education.schedule_conflicts import validate_course_schedule_conflicts
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
	_validate_student_enrollment_institution(doc, student_branch)
	_validate_progression_transfer_session(doc)
	validate_program_enrollment(doc)
	validate_progression_level_on_enrollment(doc)
	_prepare_native_required_courses_for_progression(doc)


def _validate_progression_transfer_session(doc) -> None:
	"""Keep Student Progression transfers compatible with native Enrollment truth.

	Frappe Education permits only one active Program Enrollment per Student,
	Programme and Academic Session. A mid-session Branch move therefore cannot be
	modelled safely as a second progression Enrollment. The EdgeSuite progression UI
	already offers later Sessions only; this backend guard protects crafted/direct API
	calls before native duplicate-enrollment validation emits a generic error.
	"""
	if not doc.is_new() or not doc.meta.has_field(PROGRESSION_SOURCE_FIELD):
		return
	if doc.get(PROGRESSION_OUTCOME_FIELD) != "Transfer" or not doc.get(PROGRESSION_SOURCE_FIELD):
		return
	source = frappe.db.get_value(
		"Program Enrollment",
		doc.get(PROGRESSION_SOURCE_FIELD),
		["academic_year", BRANCH_FIELD, "docstatus"],
		as_dict=True,
	)
	if not source or int(source.docstatus or 0) != 1:
		return
	if source.academic_year == doc.academic_year:
		frappe.throw(
			_(
				"Mid-session Branch transfer cannot create a second Program Enrollment in the same Academic Session. "
				"Handle the Branch move outside Student Progression; Progression transfer requires a later Academic Session."
			),
			frappe.ValidationError,
		)


def _prepare_native_required_courses_for_progression(doc) -> None:
	"""Let Frappe Education populate required Programme courses on first insert.

	Student Progression creates a destination Enrollment draft. It must not silently
	enroll every optional Programme Course. Clearing the freshly constructed child
	table here lets native ProgramEnrollment.validate() populate only required courses.
	After the draft exists, administrators may still add permitted optional courses
	through the normal Enrollment workflow before submission.
	"""
	if not doc.is_new() or not doc.meta.has_field(PROGRESSION_SOURCE_FIELD):
		return
	if not doc.get(PROGRESSION_SOURCE_FIELD):
		return
	if doc.meta.has_field("courses"):
		doc.set("courses", [])


def before_validate_student_group(doc, method=None) -> None:
	_before_validate_student_group(doc, method)
	validate_student_group_class_arm(doc)
	validate_progression_level_on_student_group(doc)


def before_validate_course_schedule(doc, method=None) -> None:
	_before_validate_course_schedule(doc, method)
	assert_schedule_instructor_assignment(doc)
	validate_course_schedule_conflicts(doc)


def _validate_student_enrollment_institution(doc, student_branch: str | None) -> None:
	if not student_branch or not doc.get(BRANCH_FIELD):
		return
	student_institution = frappe.db.get_value("EduEdge School Branch", student_branch, "institution")
	target_institution = frappe.db.get_value("EduEdge School Branch", doc.get(BRANCH_FIELD), "institution")
	if student_institution and target_institution and student_institution != target_institution:
		frappe.throw(
			_("A Student may enroll across Campuses within the same Institution, but not into another Institution."),
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
