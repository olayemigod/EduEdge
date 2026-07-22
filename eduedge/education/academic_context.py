from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import getdate, nowdate

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.institution_types import SEED_UPDATE_FLAG
from eduedge.education.offerings import PURPOSE_FIELD, assert_branch_access

INSTITUTION_FIELD = "eduedge_institution"
OFFERING_FIELD = "eduedge_program_offering"
ACADEMIC_SECTION_FIELD = "eduedge_academic_section"
ACADEMIC_LEVEL_FIELD = "eduedge_academic_level"
ENROLLMENT_STATUS_FIELD = "eduedge_enrollment_status"

ACADEMIC_CONTEXT_CUSTOM_FIELDS = {
	"Program": [
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Academic institution that owns this curriculum or class.",
		},
		{
			"fieldname": ACADEMIC_SECTION_FIELD,
			"fieldtype": "Link",
			"label": "Academic Section",
			"options": "EduEdge Academic Section",
			"in_standard_filter": 1,
			"description": "Optional grouping such as Primary, Junior Secondary, Senior Secondary, Faculty, or Training Category.",
		},
	],
	"Course": [
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Institution that owns this Subject, Course, or Module.",
		},
	],
	"Student Applicant": [
		{
			"fieldname": OFFERING_FIELD,
			"fieldtype": "Link",
			"label": "Programme Offering",
			"options": "EduEdge Program Offering",
			"insert_after": "program",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Exact Class Intake, Programme Intake, or Training Intake selected by the applicant.",
		},
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"read_only": 1,
			"in_standard_filter": 1,
			"description": "Derived from the selected Programme Offering.",
		},
		{
			"fieldname": ACADEMIC_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Academic Level",
			"options": "EduEdge Academic Level",
			"read_only": 1,
			"in_standard_filter": 1,
		},
	],
	"Program Enrollment": [
		{
			"fieldname": OFFERING_FIELD,
			"fieldtype": "Link",
			"label": "Programme Offering",
			"options": "EduEdge Program Offering",
			"insert_after": "program",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Exact Class Intake, Programme Intake, or Training Intake for this enrollment.",
		},
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"read_only": 1,
			"in_standard_filter": 1,
			"description": "Derived from the selected Programme Offering.",
		},
		{
			"fieldname": ACADEMIC_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Academic Level",
			"options": "EduEdge Academic Level",
			"read_only": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": ENROLLMENT_STATUS_FIELD,
			"fieldtype": "Select",
			"label": "Enrollment Status",
			"options": "Active\nCompleted\nPromoted\nWithdrawn\nSuspended\nTransferred\nGraduated\nCancelled",
			"default": "Active",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Current lifecycle state. Changes should be recorded through EduEdge Enrollment Status Log.",
		},
		{
			"fieldname": BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "School Branch / Campus",
			"options": "EduEdge School Branch",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Derived from the selected Programme Offering; not from the Student's current profile.",
		},
	],
	"Student Group": [
		{
			"fieldname": OFFERING_FIELD,
			"fieldtype": "Link",
			"label": "Programme Offering",
			"options": "EduEdge Program Offering",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Offering that this Class Arm, Lecture Group, or Training Class belongs to.",
		},
		{
			"fieldname": INSTITUTION_FIELD,
			"fieldtype": "Link",
			"label": "Institution",
			"options": "EduEdge Institution",
			"read_only": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": ACADEMIC_LEVEL_FIELD,
			"fieldtype": "Link",
			"label": "Academic Level",
			"options": "EduEdge Academic Level",
			"read_only": 1,
			"in_standard_filter": 1,
		},
	],
	"Student Batch Name": [_institution_field("Admission Set / Cohort institution")],
	"Student House": [_institution_field("Institution that owns this Student House")],
	"Instructor": [_institution_field("Institution that primarily employs or assigns this Instructor")],
	"Assessment Group": [_institution_field("Institution that owns this Assessment Group")],
	"Grading Scale": [_institution_field("Institution that owns this Grading Scale")],
	"Fee Structure": [
		_institution_field("Institution that owns this fee structure"),
		_optional_branch_field("Optional Branch-specific fee structure"),
		_offering_field("Optional exact Offering for this fee structure"),
		_level_field(read_only=False),
	],
	"Fee Schedule": [
		_institution_field("Derived from the selected Fee Structure or Programme Offering", read_only=True),
		_optional_branch_field("Derived Branch for this fee schedule", read_only=True),
		_offering_field("Programme Offering covered by this fee schedule"),
	],
	"Fees": [
		_institution_field("Derived from Program Enrollment or Fee Structure", read_only=True),
		_optional_branch_field("Derived Branch for this fee record", read_only=True),
		_offering_field("Derived from the selected Program Enrollment", read_only=True),
	],
	"Student Leave Application": [
		_optional_branch_field("Derived from Course Schedule, Student Group, or Student", read_only=True),
		_institution_field("Derived from the resolved Branch", read_only=True),
	],
	"Student Log": [
		_optional_branch_field("Derived from the selected Student", read_only=True),
		_institution_field("Derived from the resolved Branch", read_only=True),
	],
}

TERMINOLOGY_OVERRIDES = {
	"PRIMARY": {
		"programme": ("Class", "Classes"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student": ("Pupil", "Pupils"),
		"student_applicant": ("Pupil Applicant", "Pupil Applicants"),
		"academic_section": ("School Section", "School Sections"),
		"academic_level": ("Class", "Classes"),
	},
	"SECONDARY": {
		"programme": ("Class", "Classes"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student": ("Student", "Students"),
		"student_applicant": ("Student Applicant", "Student Applicants"),
		"academic_section": ("School Section", "School Sections"),
		"academic_level": ("Class", "Classes"),
	},
	"TERTIARY": {
		"program_enrollment": ("Programme Enrollment", "Programme Enrollments"),
		"student": ("Student", "Students"),
		"student_applicant": ("Student Applicant", "Student Applicants"),
		"academic_section": ("Faculty / School", "Faculties / Schools"),
		"academic_level": ("Level", "Levels"),
	},
	"TRAINING_CENTRE": {
		"program_enrollment": ("Trainee Enrollment", "Trainee Enrollments"),
		"student": ("Trainee", "Trainees"),
		"student_applicant": ("Trainee Applicant", "Trainee Applicants"),
		"academic_section": ("Training Category", "Training Categories"),
		"academic_level": ("Training Level", "Training Levels"),
	},
}


def _institution_field(description: str, *, read_only: bool = False) -> dict:
	return {
		"fieldname": INSTITUTION_FIELD,
		"fieldtype": "Link",
		"label": "Institution",
		"options": "EduEdge Institution",
		"read_only": int(read_only),
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": description,
	}


def _optional_branch_field(description: str, *, read_only: bool = False) -> dict:
	return {
		"fieldname": BRANCH_FIELD,
		"fieldtype": "Link",
		"label": "School Branch / Campus",
		"options": "EduEdge School Branch",
		"read_only": int(read_only),
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": description,
	}


def _offering_field(description: str, *, read_only: bool = False) -> dict:
	return {
		"fieldname": OFFERING_FIELD,
		"fieldtype": "Link",
		"label": "Programme Offering",
		"options": "EduEdge Program Offering",
		"read_only": int(read_only),
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": description,
	}


def _level_field(*, read_only: bool) -> dict:
	return {
		"fieldname": ACADEMIC_LEVEL_FIELD,
		"fieldtype": "Link",
		"label": "Academic Level",
		"options": "EduEdge Academic Level",
		"read_only": int(read_only),
		"in_standard_filter": 1,
	}


def ensure_academic_context_foundation() -> None:
	available = {
		doctype: fields
		for doctype, fields in ACADEMIC_CONTEXT_CUSTOM_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}
	if available:
		create_custom_fields(available, update=True)
	ensure_academic_terminology()
	backfill_program_offering_identity()


def ensure_academic_terminology() -> None:
	if not frappe.db.exists("DocType", "EduEdge Institution Type"):
		return
	setattr(frappe.flags, SEED_UPDATE_FLAG, True)
	try:
		for code, overrides in TERMINOLOGY_OVERRIDES.items():
			if not frappe.db.exists("EduEdge Institution Type", code):
				continue
			doc = frappe.get_doc("EduEdge Institution Type", code)
			rows = {row.canonical_key: row for row in doc.get("terms") or []}
			changed = False
			for key, (singular, plural) in overrides.items():
				row = rows.get(key)
				if not row:
					row = doc.append("terms", {"canonical_key": key})
					rows[key] = row
					changed = True
				for fieldname, value in {
					"singular_label": singular,
					"plural_label": plural,
					"short_label": singular,
					"show_feature": 1,
				}.items():
					if row.get(fieldname) != value:
						row.set(fieldname, value)
						changed = True
				if not row.sequence:
					row.sequence = (len(rows) + 1) * 10
					changed = True
			if changed:
				doc.save(ignore_permissions=True)
	finally:
		setattr(frappe.flags, SEED_UPDATE_FLAG, False)
	frappe.clear_cache(doctype="EduEdge Institution Type")


def backfill_program_offering_identity() -> None:
	if not frappe.db.exists("DocType", "EduEdge Program Offering"):
		return
	meta = frappe.get_meta("EduEdge Program Offering")
	if not meta.has_field("offering_code"):
		return
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters={"offering_code": ["in", ["", None]]},
		fields=["name", "school_branch", "program", "academic_year", "academic_term"],
	)
	for row in rows:
		code = _offering_code(row)
		title = " · ".join(value for value in (row.program, row.academic_year, row.academic_term, row.school_branch) if value)
		frappe.db.set_value(
			"EduEdge Program Offering",
			row.name,
			{"offering_code": code, "offering_title": title or row.name},
			update_modified=False,
		)


def _offering_code(row) -> str:
	seed = "::".join(str(row.get(key) or "") for key in ("name", "school_branch", "program", "academic_year", "academic_term"))
	return f"OFR-{hashlib.sha1(seed.encode()).hexdigest()[:12].upper()}"


def get_offering(name: str | None, *, purpose: str | None = None) -> frappe._dict | None:
	if not name:
		return None
	fields = [
		"name", "offering_title", "offering_code", "school_branch", "institution", "program",
		"academic_section", "academic_level", "academic_year", "academic_term", "student_batch",
		"is_active", "admission_enabled", "enrollment_enabled", "application_start_date", "application_end_date",
	]
	row = frappe.db.get_value("EduEdge Program Offering", name, fields, as_dict=True)
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
		_apply_offering_context(doc, offering)
	return offering


def _matching_offerings(doc, *, purpose: str) -> list[frappe._dict]:
	branch = doc.get(BRANCH_FIELD)
	program = doc.get("program")
	academic_year = doc.get("academic_year")
	if not branch or not program or not academic_year:
		return []
	filters = {
		"school_branch": branch,
		"program": program,
		"academic_year": academic_year,
		"is_active": 1,
		PURPOSE_FIELD[purpose]: 1,
	}
	rows = frappe.get_all("EduEdge Program Offering", filters=filters, fields=["name", "academic_term"])
	academic_term = doc.get("academic_term")
	if academic_term:
		rows = [row for row in rows if not row.academic_term or row.academic_term == academic_term]
	return rows


def _apply_offering_context(doc, offering: frappe._dict) -> None:
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
	_validate_master_institution(doc)
	section = doc.get(ACADEMIC_SECTION_FIELD) if doc.meta.has_field(ACADEMIC_SECTION_FIELD) else None
	if section:
		section_institution = frappe.db.get_value("EduEdge Academic Section", section, "institution")
		if section_institution != doc.get(INSTITUTION_FIELD):
			frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)


def before_validate_course(doc, method=None) -> None:
	_validate_master_institution(doc)


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
		_apply_offering_context(doc, get_offering(doc.get(OFFERING_FIELD)) or frappe._dict())
	_validate_master_institution(doc, required=False)


def before_validate_fee_schedule(doc, method=None) -> None:
	_source_from_link(doc, "fee_structure", "Fee Structure")
	if doc.meta.has_field(OFFERING_FIELD) and doc.get(OFFERING_FIELD):
		_apply_offering_context(doc, get_offering(doc.get(OFFERING_FIELD)) or frappe._dict())


def before_validate_fees(doc, method=None) -> None:
	_source_from_link(doc, "program_enrollment", "Program Enrollment")
	if not doc.get(INSTITUTION_FIELD):
		_source_from_link(doc, "fee_structure", "Fee Structure")


def before_validate_student_leave(doc, method=None) -> None:
	branch = None
	for fieldname, doctype in (("course_schedule", "Course Schedule"), ("student_group", "Student Group"), ("student", "Student")):
		value = doc.get(fieldname)
		if value and frappe.get_meta(doctype).has_field(BRANCH_FIELD):
			branch = frappe.db.get_value(doctype, value, BRANCH_FIELD)
			if branch:
				break
	_set_branch_and_institution(doc, branch)


def before_validate_student_log(doc, method=None) -> None:
	branch = frappe.db.get_value("Student", doc.get("student"), BRANCH_FIELD) if doc.get("student") else None
	_set_branch_and_institution(doc, branch)


def _source_from_link(doc, fieldname: str, doctype: str) -> None:
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


def _set_branch_and_institution(doc, branch: str | None) -> None:
	if not branch:
		return
	if doc.meta.has_field(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if doc.meta.has_field(INSTITUTION_FIELD) and institution:
		doc.set(INSTITUTION_FIELD, institution)


def _validate_master_institution(doc, *, required: bool = False) -> None:
	if not doc.meta.has_field(INSTITUTION_FIELD):
		return
	institution = doc.get(INSTITUTION_FIELD)
	if not institution:
		if required:
			frappe.throw(_("Institution is required."), frappe.ValidationError)
		return
	if not frappe.db.exists("EduEdge Institution", {"name": institution, "enabled": 1}):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
