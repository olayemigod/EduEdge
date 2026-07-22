from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import (
	ACADEMIC_LEVEL_FIELD,
	ACADEMIC_SECTION_FIELD,
	ENROLLMENT_STATUS_FIELD,
	INSTITUTION_FIELD,
	OFFERING_FIELD,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import PURPOSE_FIELD, assert_branch_access


def get_offering(name: str | None, *, purpose: str | None = None) -> frappe._dict | None:
	if not name:
		return None
	row = frappe.db.get_value(
		"EduEdge Program Offering",
		name,
		[
			"name", "offering_title", "offering_code", "school_branch", "institution", "program",
			"academic_section", "academic_level", "academic_year", "academic_term", "student_batch",
			"is_active", "admission_enabled", "enrollment_enabled", "application_start_date", "application_end_date",
		],
		as_dict=True,
	)
	if not row or not row.is_active:
		frappe.throw(_("Select an active Programme Offering."), frappe.ValidationError)
	if purpose:
		fieldname = PURPOSE_FIELD[purpose]
		if not row.get(fieldname):
			frappe.throw(_("The selected Programme Offering is not enabled for {0}.").format(purpose), frappe.ValidationError)
		if purpose == "admission":
			today = getdate(nowdate())
			if row.application_start_date and getdate(row.application_start_date) > today:
				frappe.throw(_("Applications for the selected Programme Offering have not opened."), frappe.ValidationError)
			if row.application_end_date and getdate(row.application_end_date) < today:
				frappe.throw(_("Applications for the selected Programme Offering have closed."), frappe.ValidationError)
	assert_branch_access(row.school_branch)
	return row


def resolve_exact_offering(doc, *, purpose: str) -> frappe._dict | None:
	if not doc.meta.has_field(OFFERING_FIELD):
		return None
	offering = get_offering(doc.get(OFFERING_FIELD), purpose=purpose)
	if not offering:
		matches = _matching_offerings(doc, purpose=purpose)
		if len(matches) == 1:
			doc.set(OFFERING_FIELD, matches[0].name)
			offering = get_offering(matches[0].name, purpose=purpose)
		elif len(matches) > 1:
			frappe.throw(
				_("More than one Programme Offering matches this record. Select the exact Offering before saving."),
				frappe.ValidationError,
			)
	if offering:
		apply_offering_context(doc, offering)
	return offering


def _matching_offerings(doc, *, purpose: str) -> list[frappe._dict]:
	branch = doc.get(BRANCH_FIELD)
	program = doc.get("program")
	academic_year = doc.get("academic_year")
	if not branch or not program or not academic_year:
		return []
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters={
			"school_branch": branch,
			"program": program,
			"academic_year": academic_year,
			"is_active": 1,
			PURPOSE_FIELD[purpose]: 1,
		},
		fields=["name", "academic_term"],
	)
	academic_term = doc.get("academic_term")
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	return rows


def apply_offering_context(doc, offering: frappe._dict) -> None:
	mapping = {
		BRANCH_FIELD: "school_branch",
		INSTITUTION_FIELD: "institution",
		"program": "program",
		"academic_year": "academic_year",
		"academic_term": "academic_term",
		"student_batch": "student_batch",
		ACADEMIC_LEVEL_FIELD: "academic_level",
	}
	for target, source in mapping.items():
		if doc.meta.has_field(target) and offering.get(source):
			doc.set(target, offering.get(source))


def before_validate_program(doc, method=None) -> None:
	validate_master_institution(doc)
	section = doc.get(ACADEMIC_SECTION_FIELD) if doc.meta.has_field(ACADEMIC_SECTION_FIELD) else None
	if section:
		section_institution = frappe.db.get_value("EduEdge Academic Section", section, "institution")
		if section_institution != doc.get(INSTITUTION_FIELD):
			frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)


def before_validate_course(doc, method=None) -> None:
	validate_master_institution(doc)


def before_validate_student_applicant_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="admission")


def before_validate_program_enrollment_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="enrollment")
	if doc.meta.has_field(ENROLLMENT_STATUS_FIELD) and not doc.get(ENROLLMENT_STATUS_FIELD):
		doc.set(ENROLLMENT_STATUS_FIELD, "Active")


def before_validate_student_group_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="enrollment")


def before_validate_fee_structure(doc, method=None) -> None:
	if doc.meta.has_field(OFFERING_FIELD) and doc.get(OFFERING_FIELD):
		apply_offering_context(doc, get_offering(doc.get(OFFERING_FIELD)) or frappe._dict())
	validate_master_institution(doc, required=False)


def before_validate_fee_schedule(doc, method=None) -> None:
	source_from_link(doc, "fee_structure", "Fee Structure")
	if doc.meta.has_field(OFFERING_FIELD) and doc.get(OFFERING_FIELD):
		apply_offering_context(doc, get_offering(doc.get(OFFERING_FIELD)) or frappe._dict())


def before_validate_fees(doc, method=None) -> None:
	source_from_link(doc, "program_enrollment", "Program Enrollment")
	if doc.meta.has_field(INSTITUTION_FIELD) and not doc.get(INSTITUTION_FIELD):
		source_from_link(doc, "fee_structure", "Fee Structure")


def before_validate_student_leave(doc, method=None) -> None:
	branch = None
	for fieldname, doctype in (("course_schedule", "Course Schedule"), ("student_group", "Student Group"), ("student", "Student")):
		value = doc.get(fieldname)
		if value and frappe.get_meta(doctype).has_field(BRANCH_FIELD):
			branch = frappe.db.get_value(doctype, value, BRANCH_FIELD)
			if branch:
				break
	set_branch_and_institution(doc, branch)


def before_validate_student_log(doc, method=None) -> None:
	branch = frappe.db.get_value("Student", doc.get("student"), BRANCH_FIELD) if doc.get("student") else None
	set_branch_and_institution(doc, branch)


def source_from_link(doc, fieldname: str, doctype: str) -> None:
	name = doc.get(fieldname)
	if not name or not frappe.db.exists(doctype, name):
		return
	meta = frappe.get_meta(doctype)
	fields = [field for field in (OFFERING_FIELD, INSTITUTION_FIELD, BRANCH_FIELD, ACADEMIC_LEVEL_FIELD) if meta.has_field(field)]
	if not fields:
		return
	row = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	for field in fields:
		if doc.meta.has_field(field) and row.get(field):
			doc.set(field, row.get(field))


def set_branch_and_institution(doc, branch: str | None) -> None:
	if not branch:
		return
	if doc.meta.has_field(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if doc.meta.has_field(INSTITUTION_FIELD) and institution:
		doc.set(INSTITUTION_FIELD, institution)


def validate_master_institution(doc, *, required: bool = False) -> None:
	if not doc.meta.has_field(INSTITUTION_FIELD):
		return
	institution = doc.get(INSTITUTION_FIELD)
	if not institution:
		if required:
			frappe.throw(_("Institution is required."), frappe.ValidationError)
		return
	if not frappe.db.exists("EduEdge Institution", {"name": institution, "enabled": 1}):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
