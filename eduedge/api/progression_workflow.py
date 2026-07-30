from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import progression as base
from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD
from eduedge.education.academic_progression import progression_target
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.enrollment_progression_fields import (
	PROGRESSION_OUTCOME_FIELD,
	PROGRESSION_REASON_FIELD,
	PROGRESSION_SOURCE_FIELD,
)
from eduedge.education.native_identity import DISPLAY_FIELD


@frappe.whitelist()
def get_progression_options(program_enrollment: str) -> dict:
	payload = base.get_progression_options(program_enrollment)
	if frappe.get_meta("Program Enrollment").has_field(PROGRESSION_SOURCE_FIELD):
		payload["planned_targets"] = frappe.get_list(
			"Program Enrollment",
			filters={PROGRESSION_SOURCE_FIELD: program_enrollment, "docstatus": ["!=", 2]},
			fields=[
				"name", "student", "student_name", "program", "academic_year", "academic_term",
				"eduedge_program_offering", PROGRESSION_OUTCOME_FIELD, PROGRESSION_REASON_FIELD, "docstatus",
			],
			order_by="creation desc",
			page_length=20,
		)
	else:
		payload["planned_targets"] = []
	return payload


@frappe.whitelist()
def get_student_group_rollover_options(student_group: str) -> dict:
	base._require_progression_access("view_student_group_rollover")
	source = frappe.get_doc("Student Group", student_group)
	source.check_permission("read")
	level = source.get(ACADEMIC_LEVEL_FIELD) if source.meta.has_field(ACADEMIC_LEVEL_FIELD) else None
	target = progression_target(source.program, level)
	institution = source.get(INSTITUTION_FIELD) if source.meta.has_field(INSTITUTION_FIELD) else None
	if not institution and source.get(BRANCH_FIELD):
		institution = frappe.db.get_value("EduEdge School Branch", source.get(BRANCH_FIELD), "institution")
	candidate_offerings = base._candidate_offerings(
		institution=institution,
		program=target.get("program"),
		academic_level=target.get("academic_level"),
		exclude_year=source.academic_year,
	)
	return {
		"source": {
			"name": source.name,
			"display_name": source.get(DISPLAY_FIELD) or source.student_group_name or source.name,
			"program": source.program,
			"academic_level": level,
			"academic_year": source.academic_year,
			"academic_term": source.academic_term,
		},
		"progression": target,
		"suggested_group_name": _suggest_group_name(source, target),
		"target_offerings": candidate_offerings,
	}


def _suggest_group_name(source, target: dict) -> str:
	friendly = str(source.get(DISPLAY_FIELD) or source.student_group_name or source.name or "").strip()
	source_program = _program_label(source.program)
	target_program = _program_label(target.get("program"))
	if source_program and target_program and source_program != target_program and friendly.casefold().startswith(source_program.casefold()):
		return f"{target_program}{friendly[len(source_program):]}".strip()
	source_level = _level_label(source.get(ACADEMIC_LEVEL_FIELD)) if source.meta.has_field(ACADEMIC_LEVEL_FIELD) else ""
	target_level = _level_label(target.get("academic_level"))
	if source_level and target_level and source_level != target_level and friendly.casefold().startswith(source_level.casefold()):
		return f"{target_level}{friendly[len(source_level):]}".strip()
	return friendly


def _program_label(program: str | None) -> str:
	if not program:
		return ""
	return frappe.db.get_value("Program", program, DISPLAY_FIELD) or frappe.db.get_value("Program", program, "program_name") or program


def _level_label(level: str | None) -> str:
	return frappe.db.get_value("EduEdge Academic Level", level, "level_name") if level else ""


@frappe.whitelist(methods=["POST"])
def create_progression_draft(
	program_enrollment: str,
	outcome: str,
	target_program_offering: str,
	reason: str | None = None,
) -> dict:
	result = base.create_progression_draft(
		program_enrollment=program_enrollment,
		outcome=outcome,
		target_program_offering=target_program_offering,
		reason=reason,
	)
	target = frappe.get_doc("Program Enrollment", result["name"])
	target.check_permission("write" if target.docstatus == 0 else "read")
	if not target.meta.has_field(PROGRESSION_SOURCE_FIELD):
		frappe.throw(_("Run site migration before using the progression workflow."), frappe.ValidationError)
	existing_source = target.get(PROGRESSION_SOURCE_FIELD)
	if existing_source and existing_source != program_enrollment:
		frappe.throw(_("The target enrollment is already linked to another progression plan."), frappe.ValidationError)
	if not result.get("created") and not existing_source:
		frappe.throw(
			_("A target enrollment already exists outside the guided progression workflow. Review it manually instead of claiming it as a new progression draft."),
			frappe.ValidationError,
		)
	if target.docstatus == 0:
		target.set(PROGRESSION_SOURCE_FIELD, program_enrollment)
		target.set(PROGRESSION_OUTCOME_FIELD, outcome)
		target.set(PROGRESSION_REASON_FIELD, str(reason or "").strip())
		target.save()
	result.update(
		{
			"source_program_enrollment": program_enrollment,
			"outcome": outcome,
			"reason": str(reason or "").strip(),
		}
	)
	return result


@frappe.whitelist(methods=["POST"])
def finalize_progression(
	program_enrollment: str,
	target_program_enrollment: str,
	outcome: str | None = None,
	reason: str | None = None,
	effective_date: str | None = None,
) -> dict:
	target = frappe.get_doc("Program Enrollment", target_program_enrollment)
	target.check_permission("read")
	if not target.meta.has_field(PROGRESSION_SOURCE_FIELD):
		frappe.throw(_("Run site migration before finalising progression."), frappe.ValidationError)
	if target.get(PROGRESSION_SOURCE_FIELD) != program_enrollment:
		frappe.throw(_("Target enrollment does not belong to this progression plan."), frappe.ValidationError)
	planned_outcome = target.get(PROGRESSION_OUTCOME_FIELD)
	if outcome and planned_outcome and outcome != planned_outcome:
		frappe.throw(_("Outcome does not match the target enrollment progression plan."), frappe.ValidationError)
	return base.finalize_progression(
		program_enrollment=program_enrollment,
		target_program_enrollment=target_program_enrollment,
		outcome=planned_outcome or outcome,
		reason=str(reason or target.get(PROGRESSION_REASON_FIELD) or "").strip(),
		effective_date=effective_date,
	)


@frappe.whitelist(methods=["POST"])
def record_enrollment_outcome(**kwargs) -> dict:
	return base.record_enrollment_outcome(**kwargs)


@frappe.whitelist(methods=["POST"])
def rollover_student_group(**kwargs) -> dict:
	return base.rollover_student_group(**kwargs)
