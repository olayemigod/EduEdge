from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, nowdate

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import (
	OFFERING_LEVEL_FIELD,
	PROGRAM_ALLOW_REPETITION_FIELD,
	get_program_progression,
	get_programme_course_rows,
	progression_target,
)
from eduedge.education.academic_validation import get_offering
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.native_identity import DISPLAY_FIELD
from eduedge.platform.access import require_eduedge_access
from eduedge.services.enrollment_lifecycle import get_current_enrollment_status

DRAFT_OUTCOMES = {"Promote", "Repeat", "Transfer"}
FINAL_OUTCOME_STATUS = {
	"Promote": "Promoted",
	"Repeat": "Repeated",
	"Transfer": "Transferred",
	"Complete": "Completed",
	"Graduate": "Graduated",
	"Withdraw": "Withdrawn",
	"Hold": "Held for Review",
	"Suspend": "Suspended",
	"Reactivate": "Active",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_progression_access(action: str) -> None:
	_require_login()
	require_eduedge_access(feature_key="academics", action=action)


def _source_enrollment(name: str):
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Progression requires a submitted source Program Enrollment."), frappe.ValidationError)
	return doc


@frappe.whitelist()
def get_progression_options(program_enrollment: str) -> dict:
	_require_progression_access("view_progression_options")
	source = _source_enrollment(program_enrollment)
	current_status = get_current_enrollment_status(source.name)
	source_level = source.get(ACADEMIC_LEVEL_FIELD) if source.meta.has_field(ACADEMIC_LEVEL_FIELD) else None
	suggested = progression_target(source.program, source_level)
	institution = source.get(INSTITUTION_FIELD) if source.meta.has_field(INSTITUTION_FIELD) else None
	return {
		"source": _enrollment_summary(source),
		"current_status": current_status,
		"progression": {
			"mode": suggested.get("mode"),
			"next_program": suggested.get("program"),
			"next_academic_level": suggested.get("academic_level"),
		},
		"outcomes": _allowed_outcomes(current_status, source),
		"promotion_offerings": _candidate_offerings(
			institution=institution,
			program=suggested.get("program"),
			academic_level=suggested.get("academic_level"),
			exclude_year=source.academic_year,
		),
		"repeat_offerings": _candidate_offerings(
			institution=institution,
			program=source.program,
			academic_level=source_level,
			exclude_year=source.academic_year,
		) if cint(get_program_progression(source.program).get(PROGRAM_ALLOW_REPETITION_FIELD)) else [],
		"transfer_offerings": _candidate_offerings(
			institution=institution,
			program=source.program,
			academic_level=source_level,
			exclude_year=None,
		),
		"permissions": {
			"can_create_enrollment": bool(frappe.has_permission("Program Enrollment", "create")),
			"can_create_status_log": bool(frappe.has_permission("EduEdge Enrollment Status Log", "create")),
		},
	}


def _allowed_outcomes(current_status: str, source) -> list[str]:
	if current_status == "Active":
		outcomes = ["Promote", "Repeat", "Complete", "Graduate", "Withdraw", "Hold", "Suspend", "Transfer"]
	elif current_status == "Completed":
		outcomes = ["Promote", "Repeat", "Graduate"]
	elif current_status in {"Suspended", "Held for Review"}:
		outcomes = ["Reactivate", "Withdraw", "Transfer"]
	else:
		outcomes = []
	if not cint(get_program_progression(source.program).get(PROGRAM_ALLOW_REPETITION_FIELD)):
		outcomes = [value for value in outcomes if value != "Repeat"]
	return outcomes


def _candidate_offerings(
	*,
	institution: str | None,
	program: str | None,
	academic_level: str | None,
	exclude_year: str | None,
) -> list[dict]:
	if not institution or not program or not frappe.has_permission("EduEdge Program Offering", "read"):
		return []
	filters = {
		"institution": institution,
		"program": program,
		"is_active": 1,
		"enrollment_enabled": 1,
		OFFERING_LEVEL_FIELD: academic_level or ["is", "not set"],
	}
	if exclude_year:
		filters["academic_year"] = ["!=", exclude_year]
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name", "offering_title", "offering_code", "school_branch", "institution", "program",
			OFFERING_LEVEL_FIELD, "academic_year", "academic_term", "student_batch", "capacity",
		],
		order_by="academic_year asc, academic_term asc, offering_title asc",
		page_length=500,
	)
	return [dict(row) for row in rows]


@frappe.whitelist(methods=["POST"])
def create_progression_draft(
	program_enrollment: str,
	outcome: str,
	target_program_offering: str,
	reason: str | None = None,
) -> dict:
	_require_progression_access("create_progression_draft")
	if outcome not in DRAFT_OUTCOMES:
		frappe.throw(_("Outcome must be Promote, Repeat or Transfer."), frappe.ValidationError)
	if not frappe.has_permission("Program Enrollment", "create"):
		frappe.throw(_("You are not permitted to create Program Enrollments."), frappe.PermissionError)
	source = _source_enrollment(program_enrollment)
	current_status = get_current_enrollment_status(source.name)
	if outcome not in _allowed_outcomes(current_status, source):
		frappe.throw(_("Outcome {0} is not allowed from enrollment status {1}.").format(outcome, current_status), frappe.ValidationError)
	offering = get_offering(target_program_offering, purpose="enrollment")
	_validate_target_offering(source, offering, outcome)

	existing = frappe.db.get_value(
		"Program Enrollment",
		{
			"student": source.student,
			OFFERING_FIELD: offering.name,
			"docstatus": ["!=", 2],
		},
		["name", "docstatus"],
		as_dict=True,
	)
	if existing:
		return {"name": existing.name, "docstatus": existing.docstatus, "created": False}

	target = frappe.new_doc("Program Enrollment")
	target.student = source.student
	target.student_name = source.student_name
	target.enrollment_date = nowdate()
	target.program = offering.program
	target.academic_year = offering.academic_year
	target.academic_term = offering.academic_term
	target.student_batch_name = offering.student_batch
	if target.meta.has_field(OFFERING_FIELD):
		target.set(OFFERING_FIELD, offering.name)
	if target.meta.has_field(INSTITUTION_FIELD):
		target.set(INSTITUTION_FIELD, offering.institution)
	if target.meta.has_field(BRANCH_FIELD):
		target.set(BRANCH_FIELD, offering.school_branch)
	if target.meta.has_field(ACADEMIC_LEVEL_FIELD):
		target.set(ACADEMIC_LEVEL_FIELD, offering.get(OFFERING_LEVEL_FIELD))
	for row in _target_course_rows(offering):
		target.append("courses", {"course": row.course})
	target.flags.eduedge_progression_source = source.name
	target.insert()
	return {
		"name": target.name,
		"docstatus": target.docstatus,
		"created": True,
		"outcome": outcome,
		"reason": str(reason or "").strip(),
	}


def _validate_target_offering(source, offering, outcome: str) -> None:
	source_institution = source.get(INSTITUTION_FIELD) if source.meta.has_field(INSTITUTION_FIELD) else None
	source_level = source.get(ACADEMIC_LEVEL_FIELD) if source.meta.has_field(ACADEMIC_LEVEL_FIELD) else None
	if source.get(OFFERING_FIELD) == offering.name:
		frappe.throw(_("Target Programme Offering must differ from the source Offering."), frappe.ValidationError)
	if outcome in {"Promote", "Repeat"} and source_institution and offering.institution != source_institution:
		frappe.throw(_("Promotion and repetition must remain within the same Institution."), frappe.ValidationError)
	if outcome == "Transfer" and source_institution and offering.institution != source_institution:
		frappe.throw(_("Automatic transfer is limited to Branches within the same Institution. Use a new admission for another Institution."), frappe.ValidationError)

	if outcome == "Promote":
		expected = progression_target(source.program, source_level)
		if not expected.get("program"):
			frappe.throw(_("The source Programme has no configured promotion target."), frappe.ValidationError)
		if offering.program != expected.get("program") or offering.get(OFFERING_LEVEL_FIELD) != expected.get("academic_level"):
			frappe.throw(_("Target Offering does not match the configured next Class or Academic Level."), frappe.ValidationError)
		if offering.academic_year == source.academic_year:
			frappe.throw(_("Promotion target must use a later Academic Session."), frappe.ValidationError)
	elif outcome == "Repeat":
		if not cint(get_program_progression(source.program).get(PROGRAM_ALLOW_REPETITION_FIELD)):
			frappe.throw(_("Repetition is disabled for this Programme / Class."), frappe.ValidationError)
		if offering.program != source.program or offering.get(OFFERING_LEVEL_FIELD) != source_level:
			frappe.throw(_("Repeat target must retain the same Programme / Class and Academic Level."), frappe.ValidationError)
		if offering.academic_year == source.academic_year:
			frappe.throw(_("Repeat target must use a different Academic Session."), frappe.ValidationError)
	elif outcome == "Transfer":
		if offering.program != source.program or offering.get(OFFERING_LEVEL_FIELD) != source_level:
			frappe.throw(_("Internal transfer must retain the same Programme / Class and Academic Level."), frappe.ValidationError)


def _target_course_rows(offering) -> list[frappe._dict]:
	period_number = _period_number(offering)
	return get_programme_course_rows(
		offering.program,
		academic_level=offering.get(OFFERING_LEVEL_FIELD),
		period_number=period_number,
	)


def _period_number(offering) -> int | None:
	if not offering.academic_term:
		return None
	calendar = frappe.db.get_value(
		"EduEdge Institution Academic Calendar",
		{"institution": offering.institution, "academic_year": offering.academic_year, "enabled": 1},
		"name",
	)
	if not calendar:
		return None
	return frappe.db.get_value(
		"EduEdge Academic Calendar Period",
		{"parent": calendar, "parenttype": "EduEdge Institution Academic Calendar", "academic_term": offering.academic_term},
		"sequence",
	)


@frappe.whitelist(methods=["POST"])
def finalize_progression(
	program_enrollment: str,
	target_program_enrollment: str,
	outcome: str,
	reason: str,
	effective_date: str | None = None,
) -> dict:
	_require_progression_access("finalize_progression")
	if outcome not in DRAFT_OUTCOMES:
		frappe.throw(_("Outcome must be Promote, Repeat or Transfer."), frappe.ValidationError)
	if not frappe.has_permission("EduEdge Enrollment Status Log", "create"):
		frappe.throw(_("You are not permitted to create Enrollment Status Logs."), frappe.PermissionError)
	source = _source_enrollment(program_enrollment)
	target = frappe.get_doc("Program Enrollment", target_program_enrollment)
	target.check_permission("read")
	if target.docstatus != 1:
		frappe.throw(_("Submit the target Program Enrollment before finalising progression."), frappe.ValidationError)
	if target.student != source.student:
		frappe.throw(_("Source and target Program Enrollments must belong to the same Student."), frappe.ValidationError)
	log = frappe.get_doc(
		{
			"doctype": "EduEdge Enrollment Status Log",
			"program_enrollment": source.name,
			"new_status": FINAL_OUTCOME_STATUS[outcome],
			"effective_date": effective_date or nowdate(),
			"reason": str(reason or "").strip(),
			"target_program_enrollment": target.name,
		}
	)
	log.insert()
	return {"name": log.name, "new_status": log.new_status, "target_program_enrollment": target.name}


@frappe.whitelist(methods=["POST"])
def record_enrollment_outcome(
	program_enrollment: str,
	outcome: str,
	reason: str,
	effective_date: str | None = None,
) -> dict:
	_require_progression_access("record_enrollment_outcome")
	if outcome not in {"Complete", "Graduate", "Withdraw", "Hold", "Suspend", "Reactivate"}:
		frappe.throw(_("Invalid enrollment outcome."), frappe.ValidationError)
	if not frappe.has_permission("EduEdge Enrollment Status Log", "create"):
		frappe.throw(_("You are not permitted to create Enrollment Status Logs."), frappe.PermissionError)
	source = _source_enrollment(program_enrollment)
	current_status = get_current_enrollment_status(source.name)
	if outcome not in _allowed_outcomes(current_status, source):
		frappe.throw(_("Outcome {0} is not allowed from enrollment status {1}.").format(outcome, current_status), frappe.ValidationError)
	log = frappe.get_doc(
		{
			"doctype": "EduEdge Enrollment Status Log",
			"program_enrollment": source.name,
			"new_status": FINAL_OUTCOME_STATUS[outcome],
			"effective_date": effective_date or nowdate(),
			"reason": str(reason or "").strip(),
		}
	)
	log.insert()
	return {"name": log.name, "new_status": log.new_status}


@frappe.whitelist(methods=["POST"])
def rollover_student_group(
	student_group: str,
	target_program_offering: str,
	group_name: str | None = None,
) -> dict:
	_require_progression_access("rollover_student_group")
	if not frappe.has_permission("Student Group", "create"):
		frappe.throw(_("You are not permitted to create Student Groups."), frappe.PermissionError)
	source = frappe.get_doc("Student Group", student_group)
	source.check_permission("read")
	offering = get_offering(target_program_offering, purpose="enrollment")
	friendly = " ".join(str(group_name or source.get(DISPLAY_FIELD) or source.student_group_name or "").split())
	if not friendly:
		frappe.throw(_("Student Group / Class Arm / Lecture Group Name is required."), frappe.ValidationError)

	filters = {
		BRANCH_FIELD: offering.school_branch,
		"program": offering.program,
		"academic_year": offering.academic_year,
		"academic_term": offering.academic_term or ["is", "not set"],
		DISPLAY_FIELD: friendly,
		"disabled": 0,
	}
	if frappe.get_meta("Student Group").has_field(ACADEMIC_LEVEL_FIELD):
		filters[ACADEMIC_LEVEL_FIELD] = offering.get(OFFERING_LEVEL_FIELD) or ["is", "not set"]
	existing = frappe.db.get_value("Student Group", filters, "name")
	if existing:
		return {"name": existing, "created": False}

	course = source.course
	allowed_courses = {row.course for row in _target_course_rows(offering) if row.course}
	if course and course not in allowed_courses:
		frappe.throw(_("The source Student Group Course is not available in the target Programme, Level and period."), frappe.ValidationError)

	target = frappe.new_doc("Student Group")
	target.set(DISPLAY_FIELD, friendly)
	target.student_group_name = friendly
	target.group_based_on = source.group_based_on
	target.max_strength = source.max_strength
	target.program = offering.program
	target.academic_year = offering.academic_year
	target.academic_term = offering.academic_term
	target.batch = offering.student_batch
	target.course = course
	target.disabled = 0
	if target.meta.has_field(OFFERING_FIELD):
		target.set(OFFERING_FIELD, offering.name)
	if target.meta.has_field(INSTITUTION_FIELD):
		target.set(INSTITUTION_FIELD, offering.institution)
	if target.meta.has_field(BRANCH_FIELD):
		target.set(BRANCH_FIELD, offering.school_branch)
	if target.meta.has_field(ACADEMIC_LEVEL_FIELD):
		target.set(ACADEMIC_LEVEL_FIELD, offering.get(OFFERING_LEVEL_FIELD))
	# Student and instructor rows are deliberately not copied. Membership and
	# teaching assignments must be confirmed for the new Session/Term.
	target.insert()
	return {"name": target.name, "created": True}


def _enrollment_summary(doc) -> dict:
	return {
		"name": doc.name,
		"student": doc.student,
		"student_name": doc.student_name,
		"program": doc.program,
		"academic_level": doc.get(ACADEMIC_LEVEL_FIELD) if doc.meta.has_field(ACADEMIC_LEVEL_FIELD) else None,
		"academic_year": doc.academic_year,
		"academic_term": doc.academic_term,
		"student_batch": doc.student_batch_name,
		"program_offering": doc.get(OFFERING_FIELD) if doc.meta.has_field(OFFERING_FIELD) else None,
		"institution": doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None,
		"school_branch": doc.get(BRANCH_FIELD) if doc.meta.has_field(BRANCH_FIELD) else None,
	}
