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
	from eduedge.education.academic_validation import before_validate_institution_owned_master

	before_validate_institution_owned_master(doc, method)
	if not doc.meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
		return
	branch = doc.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if not branch:
		return
	branch_row = frappe.db.get_value(
		"EduEdge School Branch", branch, ["institution", "enabled"], as_dict=True
	)
	if not branch_row or not branch_row.enabled:
		frappe.throw(_("Select an enabled Primary School Branch / Campus."), frappe.ValidationError)
	if institution and branch_row.institution != institution:
		frappe.throw(_("Primary School Branch / Campus must belong to the Instructor's Institution."), frappe.ValidationError)
	if doc.meta.has_field(INSTITUTION_FIELD) and not institution:
		doc.set(INSTITUTION_FIELD, branch_row.institution)
