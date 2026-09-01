from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.people_fields import (
	INSTRUCTOR_PRIMARY_BRANCH_FIELD,
	PHOTO_APPROVED_BY_FIELD,
	PHOTO_APPROVED_ON_FIELD,
	PHOTO_LOCKED_FIELD,
	PHOTO_REVIEW_NOTE_FIELD,
	PHOTO_STATUS_FIELD,
)

PEOPLE_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Registrar",
	"Admission Officer",
	"School HR Officer",
	"Education Manager",
}


def _is_people_manager() -> bool:
	return bool(PEOPLE_MANAGER_ROLES.intersection(frappe.get_roles()))


def _inherit_approved_applicant_photo(doc) -> None:
	if not doc.is_new() or not doc.get("student_applicant") or doc.get("image"):
		return
	applicant_meta = frappe.get_meta("Student Applicant")
	if not applicant_meta.has_field(PHOTO_STATUS_FIELD):
		return
	fields = [
		"image",
		PHOTO_STATUS_FIELD,
		PHOTO_LOCKED_FIELD,
		PHOTO_APPROVED_BY_FIELD,
		PHOTO_APPROVED_ON_FIELD,
		PHOTO_REVIEW_NOTE_FIELD,
	]
	applicant = frappe.db.get_value("Student Applicant", doc.student_applicant, fields, as_dict=True)
	if not applicant or applicant.get(PHOTO_STATUS_FIELD) != "Approved" or not applicant.image:
		return
	doc.image = applicant.image
	if doc.meta.has_field(PHOTO_STATUS_FIELD):
		for fieldname in fields[1:]:
			doc.set(fieldname, applicant.get(fieldname))


def before_validate_student(doc, method=None) -> None:
	from eduedge.education.branching import before_validate_student as validate_student

	validate_student(doc, method)
	_inherit_approved_applicant_photo(doc)
	if doc.is_new() or not doc.has_value_changed("image"):
		return
	if not _is_people_manager():
		frappe.throw(_("Students cannot replace or remove the official Student photo."), frappe.PermissionError)
	if doc.meta.has_field(PHOTO_STATUS_FIELD):
		doc.set(PHOTO_STATUS_FIELD, "Pending Review")
		doc.set(PHOTO_LOCKED_FIELD, 0)
		doc.set(PHOTO_APPROVED_BY_FIELD, None)
		doc.set(PHOTO_APPROVED_ON_FIELD, None)
		doc.set(PHOTO_REVIEW_NOTE_FIELD, None)


def before_validate_student_applicant(doc, method=None) -> None:
	from eduedge.education.branching import before_validate_student_applicant as validate_applicant

	validate_applicant(doc, method)
	if doc.is_new() or not doc.has_value_changed("image"):
		return
	if doc.meta.has_field(PHOTO_STATUS_FIELD):
		doc.set(PHOTO_STATUS_FIELD, "Pending Review")
		doc.set(PHOTO_LOCKED_FIELD, 0)
		doc.set(PHOTO_APPROVED_BY_FIELD, None)
		doc.set(PHOTO_APPROVED_ON_FIELD, None)
		doc.set(PHOTO_REVIEW_NOTE_FIELD, None)


def before_validate_instructor(doc, method=None) -> None:
	from eduedge.education.academic_validation import validate_master_institution

	branch = doc.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD) if doc.meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD) else None
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	validate_master_institution(doc, required=doc.is_new())
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if branch:
		branch_row = frappe.db.get_value(
			"EduEdge School Branch", branch, ["institution", "enabled"], as_dict=True
		)
		if not branch_row or not branch_row.enabled:
			frappe.throw(_("Select an enabled Primary Branch / Campus."), frappe.ValidationError)
		if institution and branch_row.institution != institution:
			frappe.throw(_("Primary Branch / Campus must belong to the Instructor's Home Institution."), frappe.ValidationError)
		if doc.meta.has_field(INSTITUTION_FIELD) and not institution:
			doc.set(INSTITUTION_FIELD, branch_row.institution)

	department = doc.get("department") if doc.meta.has_field("department") else None
	if department and institution and frappe.get_meta("Department").has_field(INSTITUTION_FIELD):
		department_institution = frappe.db.get_value("Department", department, INSTITUTION_FIELD)
		if department_institution and department_institution != institution:
			frappe.throw(
				_("Department / School Section must belong to the Instructor's Home Institution."),
				frappe.ValidationError,
			)
	_validate_instructor_employee_identity(doc)


def _validate_instructor_employee_identity(doc) -> None:
	"""Prevent new ambiguous User -> Employee -> Instructor mappings without rewriting legacy history."""
	if not doc.get("employee") or doc.get("status") != "Active":
		return
	before = doc.get_doc_before_save()
	mapping_changed = bool(
		doc.is_new()
		or not before
		or before.get("employee") != doc.get("employee")
		or before.get("status") != doc.get("status")
	)
	if not mapping_changed:
		return
	if not frappe.db.exists("DocType", "Employee"):
		return
	employee = frappe.db.get_value(
		"Employee",
		doc.employee,
		["name", "employee_name", "status", "user_id"],
		as_dict=True,
	)
	if not employee:
		frappe.throw(_("Select a valid Employee for this Instructor."), frappe.ValidationError)
	if employee.status != "Active":
		frappe.throw(_("An active Instructor must link to an active Employee."), frappe.ValidationError)

	other_same_employee = frappe.get_all(
		"Instructor",
		filters={
			"employee": employee.name,
			"status": "Active",
			"name": ["!=", doc.name or ""],
		},
		pluck="name",
		limit_page_length=2,
	)
	if other_same_employee:
		frappe.throw(
			_("Employee {0} is already linked to another active Instructor ({1}).").format(
				employee.employee_name or employee.name,
				other_same_employee[0],
			),
			frappe.ValidationError,
		)

	user_id = str(employee.user_id or "").strip()
	if not user_id:
		return
	active_employees = frappe.get_all(
		"Employee",
		filters={"user_id": user_id, "status": "Active"},
		pluck="name",
		limit_page_length=3,
	)
	if len(active_employees) > 1:
		frappe.throw(
			_("User {0} is linked to more than one active Employee. Correct the Employee mapping before linking this Instructor.").format(user_id),
			frappe.ValidationError,
		)
	other_user_instructors = frappe.get_all(
		"Instructor",
		filters={
			"employee": ["in", active_employees or [employee.name]],
			"status": "Active",
			"name": ["!=", doc.name or ""],
		},
		pluck="name",
		limit_page_length=2,
	)
	if other_user_instructors:
		frappe.throw(
			_("User {0} already resolves to another active Instructor ({1}).").format(
				user_id,
				other_user_instructors[0],
			),
			frappe.ValidationError,
		)
