from __future__ import annotations

import frappe

from eduedge.education import institution_types as registry

ADDITIONAL_TERM_KEYS = (
	"department",
	"program_enrollment",
	"student",
	"assessment",
	"assessment_group",
	"assessment_plan",
	"assessment_result",
)

INSTITUTION_TERM_OVERRIDES = {
	"PRIMARY": {
		"department": ("School Section", "School Sections"),
		"programme": ("Class", "Classes"),
		"programme_offering": ("Class Intake", "Class Intakes"),
		"class_session": ("Period", "Periods"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student": ("Pupil", "Pupils"),
		"assessment": ("Examination", "Examinations"),
		"assessment_group": ("Examination Group", "Examination Groups"),
		"assessment_plan": ("Examination Plan", "Examination Plans"),
		"assessment_result": ("Examination Result", "Examination Results"),
	},
	"SECONDARY": {
		"department": ("School Section", "School Sections"),
		"programme": ("Class", "Classes"),
		"programme_offering": ("Class Intake", "Class Intakes"),
		"class_session": ("Period", "Periods"),
		"program_enrollment": ("Class Enrollment", "Class Enrollments"),
		"student": ("Student", "Students"),
		"assessment": ("Examination", "Examinations"),
		"assessment_group": ("Examination Group", "Examination Groups"),
		"assessment_plan": ("Examination Plan", "Examination Plans"),
		"assessment_result": ("Examination Result", "Examination Results"),
	},
	"TERTIARY": {
		"department": ("Department", "Departments"),
		"programme": ("Programme", "Programmes"),
		"programme_offering": ("Programme Intake", "Programme Intakes"),
		"program_enrollment": ("Programme Enrollment", "Programme Enrollments"),
		"student": ("Student", "Students"),
		"assessment": ("Assessment", "Assessments"),
		"assessment_group": ("Assessment Group", "Assessment Groups"),
		"assessment_plan": ("Assessment Plan", "Assessment Plans"),
		"assessment_result": ("Assessment Result", "Assessment Results"),
	},
	"TRAINING_CENTRE": {
		"department": ("Training Category", "Training Categories"),
		"programme": ("Programme", "Programmes"),
		"programme_offering": ("Intake", "Intakes"),
		"program_enrollment": ("Trainee Enrollment", "Trainee Enrollments"),
		"student": ("Trainee", "Trainees"),
		"assessment": ("Evaluation", "Evaluations"),
		"assessment_group": ("Evaluation Group", "Evaluation Groups"),
		"assessment_plan": ("Evaluation Plan", "Evaluation Plans"),
		"assessment_result": ("Evaluation Result", "Evaluation Results"),
	},
}


def apply_institution_type_defaults() -> None:
	"""Apply approved EduEdge terminology defaults after the protected registry seed."""
	registry.TERM_KEYS = tuple(dict.fromkeys((*registry.TERM_KEYS, *ADDITIONAL_TERM_KEYS)))
	for code, terms in INSTITUTION_TERM_OVERRIDES.items():
		definition = registry.INSTITUTION_TYPE_SEEDS.get(code)
		if definition:
			definition["terms"].update(terms)

	# Re-run the idempotent registry writer with the approved in-memory defaults.
	registry.ensure_institution_types()
	frappe.clear_cache(doctype="EduEdge Institution Type")
