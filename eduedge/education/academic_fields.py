from __future__ import annotations

import hashlib

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.institution_types import SEED_UPDATE_FLAG

INSTITUTION_FIELD = "eduedge_institution"
OFFERING_FIELD = "eduedge_program_offering"
ACADEMIC_SECTION_FIELD = "eduedge_academic_section"
ACADEMIC_LEVEL_FIELD = "eduedge_academic_level"
ENROLLMENT_STATUS_FIELD = "eduedge_enrollment_status"


def institution_field(description: str, *, read_only: bool = False) -> dict:
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


def branch_field(description: str, *, read_only: bool = False) -> dict:
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


def offering_field(description: str, *, read_only: bool = False) -> dict:
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


def level_field(*, read_only: bool = False) -> dict:
	return {
		"fieldname": ACADEMIC_LEVEL_FIELD,
		"fieldtype": "Link",
		"label": "Academic Level",
		"options": "EduEdge Academic Level",
		"read_only": int(read_only),
		"in_standard_filter": 1,
	}


ACADEMIC_CONTEXT_CUSTOM_FIELDS = {
	"Program": [
		institution_field("Academic institution that owns this curriculum or class."),
		{
			"fieldname": ACADEMIC_SECTION_FIELD,
			"fieldtype": "Link",
			"label": "Academic Section",
			"options": "EduEdge Academic Section",
			"in_standard_filter": 1,
			"description": "Optional grouping such as Primary, Junior Secondary, Faculty, or Training Category.",
		},
	],
	"Course": [institution_field("Institution that owns this Subject, Course, or Module.")],
	"Student Applicant": [
		{
			**offering_field("Exact Class Intake, Programme Intake, or Training Intake selected by the applicant."),
			"insert_after": "program",
		},
		institution_field("Derived from the selected Programme Offering.", read_only=True),
		level_field(read_only=True),
	],
	"Program Enrollment": [
		{
			**offering_field("Exact Class Intake, Programme Intake, or Training Intake for this enrollment."),
			"insert_after": "program",
		},
		institution_field("Derived from the selected Programme Offering.", read_only=True),
		level_field(read_only=True),
		{
			"fieldname": ENROLLMENT_STATUS_FIELD,
			"fieldtype": "Select",
			"label": "Enrollment Status",
			"options": "Active\nCompleted\nPromoted\nWithdrawn\nSuspended\nTransferred\nGraduated\nCancelled",
			"default": "Active",
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Current lifecycle state. Use EduEdge Enrollment Status Log for controlled changes.",
		},
		branch_field("Derived from the selected Programme Offering; not from the Student's current profile.", read_only=True),
	],
	"Student Group": [
		offering_field("Offering that this Class Arm, Lecture Group, or Training Class belongs to."),
		institution_field("Derived from the selected Programme Offering.", read_only=True),
		level_field(read_only=True),
	],
	"Student Batch Name": [institution_field("Institution that owns this Admission Set, Cohort, or Batch.")],
	"Student House": [institution_field("Institution that owns this Student House.")],
	"Instructor": [institution_field("Institution that primarily assigns this Instructor.")],
	"Assessment Group": [institution_field("Institution that owns this Assessment Group.")],
	"Grading Scale": [institution_field("Institution that owns this Grading Scale.")],
	"Fee Structure": [
		institution_field("Institution that owns this fee structure."),
		branch_field("Optional Branch-specific fee structure."),
		offering_field("Optional exact Offering for this fee structure."),
		level_field(),
	],
	"Fee Schedule": [
		institution_field("Derived from Fee Structure or Programme Offering.", read_only=True),
		branch_field("Derived Branch for this fee schedule.", read_only=True),
		offering_field("Programme Offering covered by this fee schedule."),
	],
	"Fees": [
		institution_field("Derived from Program Enrollment or Fee Structure.", read_only=True),
		branch_field("Derived Branch for this fee record.", read_only=True),
		offering_field("Derived from the selected Program Enrollment.", read_only=True),
	],
	"Student Leave Application": [
		branch_field("Derived from Course Schedule, Student Group, or Student.", read_only=True),
		institution_field("Derived from the resolved Branch.", read_only=True),
	],
	"Student Log": [
		branch_field("Derived from the selected Student.", read_only=True),
		institution_field("Derived from the resolved Branch.", read_only=True),
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
		fields=["name", "school_branch", "program", "academic_year", "academic_term", "offering_code", "offering_title"],
	)
	for row in rows:
		updates = {}
		if not row.offering_code:
			seed = "::".join(str(row.get(key) or "") for key in ("name", "school_branch", "program", "academic_year", "academic_term"))
			updates["offering_code"] = f"OFR-{hashlib.sha1(seed.encode()).hexdigest()[:12].upper()}"
		if not row.offering_title:
			updates["offering_title"] = " · ".join(value for value in (row.program, row.academic_year, row.academic_term, row.school_branch) if value) or row.name
		if updates:
			frappe.db.set_value("EduEdge Program Offering", row.name, updates, update_modified=False)
