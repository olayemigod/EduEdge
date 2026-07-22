from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import (
	ACADEMIC_LEVEL_FIELD,
	ACADEMIC_SECTION_FIELD,
	INSTITUTION_FIELD,
	OFFERING_FIELD,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import PURPOSE_FIELD, assert_branch_access

CONTEXT_FIELDS = (OFFERING_FIELD, INSTITUTION_FIELD, BRANCH_FIELD, ACADEMIC_LEVEL_FIELD)


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


def offering_context(offering: frappe._dict | None) -> frappe._dict:
	if not offering:
		return frappe._dict()
	return frappe._dict(
		{
			OFFERING_FIELD: offering.name,
			INSTITUTION_FIELD: offering.institution,
			BRANCH_FIELD: offering.school_branch,
			ACADEMIC_LEVEL_FIELD: offering.academic_level,
		}
	)


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
		"student_batch_name": "student_batch",
		"batch": "student_batch",
		ACADEMIC_LEVEL_FIELD: "academic_level",
	}
	for target, source in mapping.items():
		if doc.meta.has_field(target):
			doc.set(target, offering.get(source) or None)


def before_validate_program(doc, method=None) -> None:
	validate_master_institution(doc, required=doc.is_new())
	section = doc.get(ACADEMIC_SECTION_FIELD) if doc.meta.has_field(ACADEMIC_SECTION_FIELD) else None
	if section:
		section_institution = frappe.db.get_value("EduEdge Academic Section", section, "institution")
		if section_institution != doc.get(INSTITUTION_FIELD):
			frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)


def before_validate_course(doc, method=None) -> None:
	validate_master_institution(doc, required=doc.is_new())


def before_validate_institution_owned_master(doc, method=None) -> None:
	validate_master_institution(doc, required=doc.is_new())


def before_validate_student_applicant_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="admission")


def before_validate_program_enrollment_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="enrollment")


def before_validate_student_group_context(doc, method=None) -> None:
	resolve_exact_offering(doc, purpose="enrollment")


def before_validate_fee_structure(doc, method=None) -> None:
	offering = get_offering(doc.get(OFFERING_FIELD)) if doc.meta.has_field(OFFERING_FIELD) and doc.get(OFFERING_FIELD) else None
	context = offering_context(offering)
	if offering:
		_assert_context_compatible(doc, context, label=_("Programme Offering"))
		apply_offering_context(doc, offering)
	validate_master_institution(doc, required=doc.is_new())
	_validate_branch_institution(doc)
	_validate_level_institution(doc)


def before_validate_fee_schedule(doc, method=None) -> None:
	structure_context = linked_context("Fee Structure", doc.get("fee_structure"))
	offering = get_offering(doc.get(OFFERING_FIELD)) if doc.meta.has_field(OFFERING_FIELD) and doc.get(OFFERING_FIELD) else None
	offering_ctx = offering_context(offering)
	if offering_ctx and structure_context:
		_assert_context_dicts_match(structure_context, offering_ctx, _("Fee Structure"), _("Programme Offering"))
	clear_context(doc)
	if structure_context:
		apply_context(doc, structure_context)
	if offering:
		apply_offering_context(doc, offering)


def before_validate_fees(doc, method=None) -> None:
	enrollment_context = linked_context("Program Enrollment", doc.get("program_enrollment"))
	structure_context = linked_context("Fee Structure", doc.get("fee_structure"))
	if enrollment_context and structure_context:
		_assert_context_dicts_match(enrollment_context, structure_context, _("Program Enrollment"), _("Fee Structure"))
	clear_context(doc)
	apply_context(doc, enrollment_context or structure_context or {})


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


def linked_context(doctype: str, name: str | None) -> frappe._dict:
	if not name or not frappe.db.exists(doctype, name):
		return frappe._dict()
	meta = frappe.get_meta(doctype)
	fields = [field for field in CONTEXT_FIELDS if meta.has_field(field)]
	return frappe.db.get_value(doctype, name, fields, as_dict=True) or frappe._dict()


def clear_context(doc) -> None:
	for field in CONTEXT_FIELDS:
		if doc.meta.has_field(field):
			doc.set(field, None)


def apply_context(doc, context: dict) -> None:
	for field in CONTEXT_FIELDS:
		if doc.meta.has_field(field):
			doc.set(field, context.get(field) or None)


def set_branch_and_institution(doc, branch: str | None) -> None:
	if doc.meta.has_field(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch or None)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution") if branch else None
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, institution or None)


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


def _validate_branch_institution(doc) -> None:
	branch = doc.get(BRANCH_FIELD) if doc.meta.has_field(BRANCH_FIELD) else None
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if branch and institution:
		branch_institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
		if branch_institution != institution:
			frappe.throw(_("School Branch / Campus must belong to the selected Institution."), frappe.ValidationError)


def _validate_level_institution(doc) -> None:
	level = doc.get(ACADEMIC_LEVEL_FIELD) if doc.meta.has_field(ACADEMIC_LEVEL_FIELD) else None
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if level and institution:
		level_institution = frappe.db.get_value("EduEdge Academic Level", level, "institution")
		if level_institution != institution:
			frappe.throw(_("Academic Level must belong to the selected Institution."), frappe.ValidationError)


def _assert_context_compatible(doc, context: dict, *, label: str) -> None:
	for field in (INSTITUTION_FIELD, BRANCH_FIELD, ACADEMIC_LEVEL_FIELD):
		if doc.meta.has_field(field) and doc.get(field) and context.get(field) and doc.get(field) != context.get(field):
			frappe.throw(_("{0} conflicts with the selected academic context.").format(label), frappe.ValidationError)


def _assert_context_dicts_match(left: dict, right: dict, left_label: str, right_label: str) -> None:
	for field in (INSTITUTION_FIELD, BRANCH_FIELD, OFFERING_FIELD):
		if left.get(field) and right.get(field) and left.get(field) != right.get(field):
			frappe.throw(
				_("{0} and {1} belong to different academic contexts.").format(left_label, right_label),
				frappe.ValidationError,
			)
