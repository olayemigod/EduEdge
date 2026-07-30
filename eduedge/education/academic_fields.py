from __future__ import annotations

import hashlib

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.institution_types import SEED_UPDATE_FLAG

INSTITUTION_FIELD = "eduedge_institution"
OFFERING_FIELD = "eduedge_program_offering"
ACADEMIC_SECTION_FIELD = "eduedge_academic_section"  # legacy compatibility only
ACADEMIC_LEVEL_FIELD = "eduedge_academic_level"  # legacy compatibility only


def institution_field(description: str, *, read_only: bool = False, insert_after: str | None = None) -> dict:
	field = {
		"fieldname": INSTITUTION_FIELD,
		"fieldtype": "Link",
		"label": "Institution",
		"options": "EduEdge Institution",
		"read_only": int(read_only),
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": description,
	}
	if insert_after:
		field["insert_after"] = insert_after
	return field


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


def legacy_section_field() -> dict:
	return {
		"fieldname": ACADEMIC_SECTION_FIELD,
		"fieldtype": "Link",
		"label": "Legacy Academic Section",
		"options": "EduEdge Academic Section",
		"hidden": 1,
		"read_only": 1,
		"description": "Deprecated migration reference. Use the native Department field.",
	}


def legacy_level_field() -> dict:
	return {
		"fieldname": ACADEMIC_LEVEL_FIELD,
		"fieldtype": "Link",
		"label": "Legacy Academic Level",
		"options": "EduEdge Academic Level",
		"hidden": 1,
		"read_only": 1,
		"description": "Deprecated migration reference. Use Program and Student Group.",
	}


def _display_field(*, insert_after: str, label: str, description: str) -> dict:
	# Imported lazily by the installer as well, avoiding an import cycle with the
	# identity helper which depends on the constants in this module.
	from eduedge.education.native_identity import display_name_field

	return display_name_field(insert_after=insert_after, label=label, description=description)


ACADEMIC_CONTEXT_CUSTOM_FIELDS = {
	"Department": [
		_display_field(
			insert_after="department_name",
			label="Department / School Section Display Name",
			description="Friendly Institution-facing name. The native Department identity may be namespaced when another Institution uses the same name.",
		),
		institution_field(
			"Institution that owns this Faculty, School, Department, or School Section.",
			insert_after="company",
		),
	],
	"Program": [
		_display_field(
			insert_after="program_name",
			label="Programme / Class Display Name",
			description="Friendly name shown to users. The native Program identity is namespaced only when required on a shared site.",
		),
		institution_field(
			"Institution that owns this Programme or Class.",
			insert_after="department",
		),
		legacy_section_field(),
	],
	"Course": [
		_display_field(
			insert_after="course_name",
			label="Course / Subject Display Name",
			description="Friendly name shown to users. The native Course identity is namespaced only when required on a shared site.",
		),
		institution_field("Institution that owns this Subject, Course, or Module.", insert_after="department"),
	],
	"Student Applicant": [
		{
			**offering_field("Exact Class Intake, Programme Intake, or Training Intake selected by the applicant."),
			"insert_after": "program",
		},
		institution_field("Derived from the selected Programme Offering.", read_only=True),
		legacy_level_field(),
	],
	"Program Enrollment": [
		{
			**offering_field("Exact Class Intake, Programme Intake, or Training Intake for this enrollment."),
			"insert_after": "program",
		},
		institution_field("Derived from the selected Programme Offering.", read_only=True),
		legacy_level_field(),
		branch_field("Derived from the selected Programme Offering; not from the Student's current profile.", read_only=True),
	],
	"Student Group": [
		_display_field(
			insert_after="student_group_name",
			label="Class Arm / Level Display Name",
			description="Friendly class arm, level, lecture group, or training class name. Native identity is namespaced when reused across Institutions or Sessions.",
		),
		offering_field("Offering that this Class Arm, Level, Lecture Group, or Training Class belongs to."),
		institution_field("Derived from the selected Programme Offering or Programme.", read_only=True),
		legacy_level_field(),
	],
	"Student Batch Name": [
		_display_field(
			insert_after="batch_name",
			label="Student Batch / Cohort Display Name",
			description="Friendly Admission Set, Cohort, or Batch name shown to users.",
		),
		institution_field("Institution that owns this Admission Set, Cohort, or Batch."),
	],
	"Student House": [institution_field("Institution that owns this Student House.")],
	"Instructor": [institution_field("Institution that primarily assigns this Instructor.")],
	"Assessment Group": [institution_field("Institution that owns this Assessment Group.")],
	"Grading Scale": [institution_field("Institution that owns this Grading Scale.")],
	"Fee Structure": [
		institution_field("Institution that owns this fee structure."),
		branch_field("Optional Branch-specific fee structure."),
		offering_field("Optional exact Offering for this fee structure."),
		legacy_level_field(),
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
		"department": ("School Section", "School Sections"),
		"programme": ("Class", "Classes"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student_group": ("Class Arm", "Class Arms"),
		"student": ("Pupil", "Pupils"),
		"student_applicant": ("Pupil Applicant", "Pupil Applicants"),
		"academic_section": ("School Section", "School Sections"),
		"academic_level": ("Class", "Classes"),
	},
	"SECONDARY": {
		"department": ("School Section", "School Sections"),
		"programme": ("Class", "Classes"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student_group": ("Class Arm", "Class Arms"),
		"student": ("Student", "Students"),
		"student_applicant": ("Student Applicant", "Student Applicants"),
		"academic_section": ("School Section", "School Sections"),
		"academic_level": ("Class", "Classes"),
	},
	"TERTIARY": {
		"department": ("Faculty / School", "Faculties / Schools"),
		"programme": ("Programme", "Programmes"),
		"program_enrollment": ("Programme Enrollment", "Programme Enrollments"),
		"student_group": ("Level / Lecture Group", "Levels / Lecture Groups"),
		"student": ("Student", "Students"),
		"student_applicant": ("Student Applicant", "Student Applicants"),
		"academic_section": ("Faculty / School", "Faculties / Schools"),
		"academic_level": ("Level", "Levels"),
	},
	"TRAINING_CENTRE": {
		"department": ("Training Department", "Training Departments"),
		"programme": ("Programme", "Programmes"),
		"program_enrollment": ("Trainee Enrollment", "Trainee Enrollments"),
		"student_group": ("Training Class", "Training Classes"),
		"student": ("Trainee", "Trainees"),
		"student_applicant": ("Trainee Applicant", "Trainee Applicants"),
		"academic_section": ("Training Department", "Training Departments"),
		"academic_level": ("Training Class", "Training Classes"),
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
	from eduedge.education.native_identity import ensure_native_identity_foundation

	ensure_native_identity_foundation()
	ensure_academic_terminology()
	backfill_legacy_sections_to_departments()
	backfill_program_offering_identity()
	backfill_unambiguous_academic_master_context()


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


def backfill_legacy_sections_to_departments() -> None:
	from eduedge.education.native_hierarchy_migration import backfill_legacy_sections_to_departments as canonical_backfill

	canonical_backfill()


def backfill_program_offering_identity() -> None:
	if not frappe.db.exists("DocType", "EduEdge Program Offering"):
		return
	meta = frappe.get_meta("EduEdge Program Offering")
	if not meta.has_field("offering_code"):
		return
	fields = [
		"name", "school_branch", "program", "academic_year", "academic_term",
		"offering_code", "offering_title", "institution",
	]
	for optional in ("department", "academic_section"):
		if meta.has_field(optional):
			fields.append(optional)
	rows = frappe.get_all("EduEdge Program Offering", fields=fields)
	program_meta = frappe.get_meta("Program")
	for row in rows:
		updates = {}
		if not row.offering_code:
			seed = "::".join(str(row.get(key) or "") for key in ("name", "school_branch", "program", "academic_year", "academic_term"))
			updates["offering_code"] = f"OFR-{hashlib.sha1(seed.encode()).hexdigest()[:12].upper()}"
		if not row.offering_title:
			updates["offering_title"] = " · ".join(value for value in (row.program, row.academic_year, row.academic_term, row.school_branch) if value) or row.name
		if not row.institution and row.school_branch:
			updates["institution"] = frappe.db.get_value("EduEdge School Branch", row.school_branch, "institution")
		if meta.has_field("department") and not row.get("department") and row.program:
			updates["department"] = frappe.db.get_value("Program", row.program, "department")
		if meta.has_field("academic_section") and not row.get("academic_section") and row.program and program_meta.has_field(ACAMIC_SECTION_FIELD):
			updates["academic_section"] = frappe.db.get_value("Program", row.program, ACADEMIC_SECTION_FIELD)
		updates = {key: value for key, value in updates.items() if value not in (None, "")}
		if updates:
			frappe.db.set_value("EduEdge Program Offering", row.name, updates, update_modified=False)


def backfill_unambiguous_academic_master_context() -> None:
	if frappe.get_meta("Program").has_field(INSTITUTION_FIELD):
		frappe.db.sql(
			f"""
			update `tabProgram` program
			inner join (
				select offering.program, min(offering.institution) as institution,
					count(distinct offering.institution) as institution_count
				from `tabEduEdge Program Offering` offering
				where coalesce(offering.institution, '') != ''
				group by offering.program
				having institution_count = 1
			) resolved on resolved.program = program.name
			set program.`{INSTITUTION_FIELD}` = resolved.institution
			where coalesce(program.`{INSTITUTION_FIELD}`, '') = ''
			"""
		)
	if frappe.db.exists("DocType", "Program Course") and frappe.get_meta("Course").has_field(INSTITUTION_FIELD):
		frappe.db.sql(
			f"""
			update `tabCourse` course
			inner join (
				select program_course.course, min(program.`{INSTITUTION_FIELD}`) as institution,
					count(distinct program.`{INSTITUTION_FIELD}`) as institution_count
				from `tabProgram Course` program_course
				inner join `tabProgram` program on program.name = program_course.parent
				where program_course.parenttype = 'Program'
					and coalesce(program.`{INSTITUTION_FIELD}`, '') != ''
				group by program_course.course
				having institution_count = 1
			) resolved on resolved.course = course.name
			set course.`{INSTITUTION_FIELD}` = resolved.institution
			where coalesce(course.`{INSTITUTION_FIELD}`, '') = ''
			"""
		)
	if frappe.get_meta("Student Batch Name").has_field(INSTITUTION_FIELD):
		frappe.db.sql(
			f"""
			update `tabStudent Batch Name` batch
			inner join (
				select offering.student_batch, min(offering.institution) as institution,
					count(distinct offering.institution) as institution_count
				from `tabEduEdge Program Offering` offering
				where coalesce(offering.student_batch, '') != ''
					and coalesce(offering.institution, '') != ''
				group by offering.student_batch
				having institution_count = 1
			) resolved on resolved.student_batch = batch.name
			set batch.`{INSTITUTION_FIELD}` = resolved.institution
			where coalesce(batch.`{INSTITUTION_FIELD}`, '') = ''
			"""
		)
	if frappe.get_meta("Instructor").has_field(INSTITUTION_FIELD) and frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment"):
		frappe.db.sql(
			f"""
			update `tabInstructor` instructor
			inner join (
				select assignment.instructor, min(branch.institution) as institution,
					count(distinct branch.institution) as institution_count
				from `tabEduEdge Instructor Branch Assignment` assignment
				inner join `tabEduEdge School Branch` branch on branch.name = assignment.school_branch
				where assignment.enabled = 1 and coalesce(branch.institution, '') != ''
				group by assignment.instructor
				having institution_count = 1
			) resolved on resolved.instructor = instructor.name
			set instructor.`{INSTITUTION_FIELD}` = resolved.institution
			where coalesce(instructor.`{INSTITUTION_FIELD}`, '') = ''
			"""
		)
