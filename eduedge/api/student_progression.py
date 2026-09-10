from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import (
	PROGRAM_ALLOW_REPETITION_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
	PROGRESSION_LEVEL_FIELD,
	get_program_progression,
	progression_target,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.enrollment_progression_fields import (
	PROGRESSION_EVIDENCE_FIELD,
	PROGRESSION_OUTCOME_FIELD,
	PROGRESSION_REASON_FIELD,
	PROGRESSION_RECOMMENDATION_FIELD,
	PROGRESSION_SOURCE_FIELD,
	PROGRESSION_TARGET_GROUP_FIELD,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_BATCH = 200
TARGET_OUTCOMES = {"Promote", "Repeat", "Transfer"}
DIRECT_OUTCOMES = {"Complete", "Graduate", "Withdraw", "Defer", "Hold", "Suspend", "Reactivate"}
FINAL_STATUS = {
	"Promote": "Promoted",
	"Repeat": "Repeated",
	"Transfer": "Transferred",
	"Complete": "Completed",
	"Graduate": "Graduated",
	"Withdraw": "Withdrawn",
	"Defer": "Deferred",
	"Hold": "Held for Review",
	"Suspend": "Suspended",
	"Reactivate": "Active",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_access(action: str) -> None:
	_require_login()
	require_eduedge_access(feature_key="academics", action=action)


def _require_manager(*, create_enrollment: bool = False) -> None:
	if not frappe.has_permission("Program Enrollment", "read"):
		frappe.throw(_("You are not permitted to review Program Enrollments."), frappe.PermissionError)
	if create_enrollment and not frappe.has_permission("Program Enrollment", "create"):
		frappe.throw(_("You are not permitted to create destination Program Enrollments."), frappe.PermissionError)
	if not frappe.has_permission("EduEdge Enrollment Status Log", "create"):
		frappe.throw(_("You are not permitted to approve enrollment lifecycle changes."), frappe.PermissionError)


def _parse_names(value: Any, *, label: str = "students") -> list[str]:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, list):
		frappe.throw(_("Select one or more {0}.").format(label), frappe.ValidationError)
	result: list[str] = []
	seen: set[str] = set()
	for item in value:
		name = str(item.get("name") if isinstance(item, dict) else item or "").strip()
		if name and name not in seen:
			seen.add(name)
			result.append(name)
	if not result:
		frappe.throw(_("Select at least one {0}.").format(label), frappe.ValidationError)
	if len(result) > MAX_BATCH:
		frappe.throw(_("A maximum of {0} students can be processed in one batch.").format(MAX_BATCH), frappe.ValidationError)
	return result


def _allowed_branch(branch: str | None) -> dict:
	allowed = get_allowed_school_branches()
	if not branch:
		current = get_current_school_branch() or {}
		branch = current.get("name")
	row = next((item for item in allowed if item.get("name") == branch), None)
	if not row:
		frappe.throw(_("Select a Branch / Campus within your Branch Governance scope."), frappe.PermissionError)
	assert_branch_access(branch)
	return row


def _academic_years() -> list[dict]:
	# Academic Year is a global academic master. Keep progression session discovery
	# aligned with Class Intake instead of applying value-level User Permission filters.
	if not frappe.has_permission("Academic Year", "read"):
		return []
	fields = ["name", "year_start_date", "year_end_date"]
	return frappe.get_all("Academic Year", fields=fields, order_by="year_start_date asc", page_length=200)


def _is_later_year(target_year: str | None, source_year: str | None) -> bool:
	if not target_year or not source_year or target_year == source_year:
		return False
	target_start = frappe.db.get_value("Academic Year", target_year, "year_start_date")
	source_start = frappe.db.get_value("Academic Year", source_year, "year_start_date")
	if target_start and source_start:
		return getdate(target_start) > getdate(source_start)
	return target_year != source_year


def _status_map(enrollment_names: list[str]) -> dict[str, str]:
	statuses = {name: "Active" for name in enrollment_names}
	if not enrollment_names:
		return statuses
	rows = frappe.get_all(
		"EduEdge Enrollment Status Log",
		filters={"program_enrollment": ["in", enrollment_names]},
		fields=["program_enrollment", "new_status", "effective_date", "creation"],
		order_by="effective_date desc, creation desc",
		page_length=0,
	)
	seen: set[str] = set()
	for row in rows:
		if row.program_enrollment in seen:
			continue
		statuses[row.program_enrollment] = row.new_status
		seen.add(row.program_enrollment)
	return statuses


def _planned_target_map(enrollment_names: list[str]) -> dict[str, dict]:
	if not enrollment_names or not frappe.get_meta("Program Enrollment").has_field(PROGRESSION_SOURCE_FIELD):
		return {}
	rows = frappe.get_list(
		"Program Enrollment",
		filters={PROGRESSION_SOURCE_FIELD: ["in", enrollment_names], "docstatus": ["!=", 2]},
		fields=[
			"name", "student", "student_name", "program", "academic_year", "docstatus", OFFERING_FIELD,
			PROGRESSION_LEVEL_FIELD, PROGRESSION_SOURCE_FIELD, PROGRESSION_OUTCOME_FIELD,
			PROGRESSION_TARGET_GROUP_FIELD, PROGRESSION_RECOMMENDATION_FIELD,
		],
		order_by="creation desc",
		page_length=0,
	)
	result: dict[str, dict] = {}
	for row in rows:
		result.setdefault(row.get(PROGRESSION_SOURCE_FIELD), dict(row))
	return result


def _active_group_students(
	student_group: str,
	*,
	branch: str,
	academic_year: str,
	program: str,
) -> list[str]:
	"""Resolve a source Class Arm before paging Program Enrollments.

	The group itself is permission-checked and must match the explicit Branch,
	Academic Session and Programme filter. This prevents a crafted Class Arm name
	from widening or crossing the progression scope.
	"""
	group = frappe.get_doc("Student Group", student_group)
	group.check_permission("read")
	if cint(group.disabled):
		frappe.throw(_("Selected source Class Arm / Group is disabled."), frappe.ValidationError)
	if group.get(BRANCH_FIELD) != branch:
		frappe.throw(_("Selected source Class Arm / Group belongs to another Branch / Campus."), frappe.PermissionError)
	if group.academic_year != academic_year:
		frappe.throw(_("Selected source Class Arm / Group belongs to another Academic Session."), frappe.ValidationError)
	if group.program != program:
		frappe.throw(_("Selected source Class Arm / Group belongs to another Class / Programme."), frappe.ValidationError)

	students: list[str] = []
	for row in group.get("students") or []:
		if row.meta.has_field("active") and not cint(row.active):
			continue
		if row.student:
			students.append(row.student)
	return list(dict.fromkeys(students))


def _source_group_map(branch: str, academic_year: str, students: list[str]) -> dict[str, dict]:
	if not students:
		return {}
	groups = frappe.get_list(
		"Student Group",
		filters={BRANCH_FIELD: branch, "academic_year": academic_year, "disabled": 0},
		fields=["name", "student_group_name", "program", "course", "academic_year", OFFERING_FIELD, PROGRESSION_LEVEL_FIELD],
		order_by="student_group_name asc",
		page_length=500,
	)
	if not groups:
		return {}
	group_names = [row.name for row in groups]
	child_meta = frappe.get_meta("Student Group Student")
	fields = ["parent", "student"]
	if child_meta.has_field("active"):
		fields.append("active")
	memberships = frappe.get_all(
		"Student Group Student",
		filters={"parent": ["in", group_names], "student": ["in", students]},
		fields=fields,
		page_length=0,
	)
	group_map = {row.name: row for row in groups}
	result: dict[str, dict] = {}
	for membership in memberships:
		if "active" in membership and not cint(membership.active):
			continue
		group = group_map.get(membership.parent)
		if group and membership.student not in result:
			result[membership.student] = dict(group)
	return result


def _evidence_map(branch: str, academic_year: str, students: list[str]) -> dict[str, dict]:
	result = {
		student: {"submitted_assessment_results": 0, "approved_cbt_results": 0, "pending_cbt_results": 0}
		for student in students
	}
	if not students:
		return result

	assessment_rows = frappe.get_list(
		"Assessment Result",
		filters={"student": ["in", students], "docstatus": 1},
		fields=["name", "student", "assessment_plan"],
		page_length=0,
	)
	plan_names = list({row.assessment_plan for row in assessment_rows if row.assessment_plan})
	plan_context: dict[str, dict] = {}
	if plan_names:
		plan_rows = frappe.get_list(
			"Assessment Plan",
			filters={"name": ["in", plan_names]},
			fields=["name", "academic_year", BRANCH_FIELD],
			page_length=0,
		)
		plan_context = {row.name: dict(row) for row in plan_rows}
	for row in assessment_rows:
		plan = plan_context.get(row.assessment_plan) or {}
		if plan.get("academic_year") == academic_year and plan.get(BRANCH_FIELD) == branch:
			result[row.student]["submitted_assessment_results"] += 1

	if frappe.db.exists("DocType", "EduEdge CBT Result"):
		cbt_rows = frappe.get_list(
			"EduEdge CBT Result",
			filters={"student": ["in", students]},
			fields=["student", "result_status", "exam_schedule"],
			page_length=0,
		)
		schedule_names = list({row.exam_schedule for row in cbt_rows if row.exam_schedule})
		schedules: dict[str, dict] = {}
		if schedule_names:
			schedule_rows = frappe.get_list(
				"EduEdge CBT Exam Schedule",
				filters={"name": ["in", schedule_names]},
				fields=["name", "academic_year", "school_branch"],
				page_length=0,
			)
			schedules = {row.name: dict(row) for row in schedule_rows}
		for row in cbt_rows:
			schedule = schedules.get(row.exam_schedule) or {}
			if schedule.get("academic_year") != academic_year or schedule.get("school_branch") != branch:
				continue
			if row.result_status == "Approved":
				result[row.student]["approved_cbt_results"] += 1
			else:
				result[row.student]["pending_cbt_results"] += 1
	return result


def _recommendation(source: dict, current_status: str, evidence: dict) -> dict:
	try:
		target = progression_target(source.get("program"), source.get(PROGRESSION_LEVEL_FIELD))
	except frappe.ValidationError as exc:
		return {"label": "Review Required", "reason": str(exc), "target": {}}
	if current_status not in {"Active", "Completed", "Held for Review"}:
		return {"label": "Review Required", "reason": f"Current enrollment status is {current_status}.", "target": target}
	if target.get("terminal"):
		return {"label": "Completion / Graduation Review", "reason": "The current Class/Level is terminal.", "target": target}
	if not target.get("program"):
		return {"label": "Manual Decision Required", "reason": "No automatic progression target is configured.", "target": target}
	if evidence.get("pending_cbt_results"):
		return {"label": "Review Required", "reason": "Pending CBT results must be resolved before approval.", "target": target}
	if evidence.get("submitted_assessment_results") or evidence.get("approved_cbt_results"):
		return {"label": "Promotion Review Ready", "reason": "Submitted academic evidence is available for management review.", "target": target}
	return {"label": "Review Required", "reason": "No submitted assessment evidence was found for this Academic Session.", "target": target}


@frappe.whitelist()
def get_student_progression_page(
	branch: str | None = None,
	source_academic_year: str | None = None,
	program: str | None = None,
	student_group: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	_require_access("view_student_progression")
	_require_manager()
	branch_row = _allowed_branch(branch)
	branch = branch_row.get("name")
	start = max(0, cint(start))
	page_length = min(100, max(10, cint(page_length) or 50))

	filters: dict = {BRANCH_FIELD: branch, "docstatus": 1}
	if source_academic_year:
		filters["academic_year"] = source_academic_year
	if program:
		filters["program"] = program
	if student_group:
		if not source_academic_year or not program:
			frappe.throw(
				_("Select the source Academic Session and Class / Programme before filtering by Class Arm / Group."),
				frappe.ValidationError,
			)
		group_students = _active_group_students(
			student_group,
			branch=branch,
			academic_year=source_academic_year,
			program=program,
		)
		# A deliberately impossible Student name keeps pagination and has_more accurate
		# when the selected Class Arm has an empty roster.
		filters["student"] = ["in", group_students or ["__eduedge_no_student__"]]
	or_filters = None
	if search:
		or_filters = {"student": ["like", f"%{search}%"], "student_name": ["like", f"%{search}%"]}

	rows = frappe.get_list(
		"Program Enrollment",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "student", "student_name", "program", "academic_year", "academic_term", "student_batch_name",
			OFFERING_FIELD, INSTITUTION_FIELD, BRANCH_FIELD, PROGRESSION_LEVEL_FIELD,
		],
		order_by="student_name asc, student asc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	students = [row.student for row in rows]
	statuses = _status_map([row.name for row in rows])
	planned = _planned_target_map([row.name for row in rows])
	groups = _source_group_map(branch, source_academic_year, students) if source_academic_year else {}
	evidence = _evidence_map(branch, source_academic_year, students) if source_academic_year else {student: {} for student in students}

	program_names = list({row.program for row in rows if row.program})
	program_labels = {
		row.name: row.program_name or row.name
		for row in frappe.get_list("Program", filters={"name": ["in", program_names]}, fields=["name", "program_name"], page_length=0)
	} if program_names else {}
	level_names = list({row.get(PROGRESSION_LEVEL_FIELD) for row in rows if row.get(PROGRESSION_LEVEL_FIELD)})
	level_labels = {
		row.name: row.level_name
		for row in frappe.get_list("EduEdge Academic Level", filters={"name": ["in", level_names]}, fields=["name", "level_name"], page_length=0)
	} if level_names else {}

	payload_rows = []
	for row in rows:
		row_dict = dict(row)
		status = statuses.get(row.name, "Active")
		student_evidence = evidence.get(row.student) or {}
		recommendation = _recommendation(row_dict, status, student_evidence)
		group = groups.get(row.student)
		payload_rows.append({
			**row_dict,
			"program_label": program_labels.get(row.program, row.program),
			"progression_level_label": level_labels.get(row.get(PROGRESSION_LEVEL_FIELD), row.get(PROGRESSION_LEVEL_FIELD)),
			"current_status": status,
			"source_student_group": group,
			"evidence": student_evidence,
			"recommendation": recommendation,
			"planned_target": planned.get(row.name),
		})

	programs = frappe.get_list(
		"Program",
		filters={INSTITUTION_FIELD: branch_row.get("institution")},
		fields=["name", "program_name", PROGRAM_PROGRESSION_MODE_FIELD, "eduedge_terminal_program"],
		order_by="program_name asc",
		page_length=500,
	)
	group_filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	if source_academic_year:
		group_filters["academic_year"] = source_academic_year
	if program:
		group_filters["program"] = program
	groups_list = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=["name", "student_group_name", "program", PROGRESSION_LEVEL_FIELD],
		order_by="student_group_name asc",
		page_length=500,
	)
	return {
		"selected_branch": branch_row,
		"allowed_branches": get_allowed_school_branches(),
		"academic_years": _academic_years(),
		"programs": programs,
		"student_groups": groups_list,
		"rows": payload_rows,
		"filters": {"branch": branch, "source_academic_year": source_academic_year or "", "program": program or "", "student_group": student_group or "", "search": search or ""},
		"paging": {"start": start, "page_length": page_length, "has_more": has_more, "next_start": start + page_length},
		"permissions": {
			"can_prepare": bool(frappe.has_permission("Program Enrollment", "create")),
			"can_finalize": bool(frappe.has_permission("EduEdge Enrollment Status Log", "create")),
		},
	}


def _source_enrollment(name: str):
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Progression requires a submitted source Program Enrollment."), frappe.ValidationError)
	if doc.meta.has_field(BRANCH_FIELD) and doc.get(BRANCH_FIELD):
		assert_branch_access(doc.get(BRANCH_FIELD))
	return doc


def _validate_outcome(source, outcome: str) -> None:
	if outcome not in TARGET_OUTCOMES | DIRECT_OUTCOMES:
		frappe.throw(_("Select a valid progression outcome."), frappe.ValidationError)
	current = _status_map([source.name]).get(source.name, "Active")
	allowed = {
		"Active": {"Promote", "Repeat", "Transfer", "Complete", "Graduate", "Withdraw", "Defer", "Hold", "Suspend"},
		"Completed": {"Promote", "Repeat", "Graduate"},
		"Held for Review": {"Promote", "Repeat", "Transfer", "Withdraw", "Defer", "Reactivate"},
		"Suspended": {"Transfer", "Withdraw", "Defer", "Hold", "Reactivate"},
		"Deferred": {"Transfer", "Withdraw", "Reactivate"},
	}.get(current, set())
	if outcome not in allowed:
		frappe.throw(_("Outcome {0} is not allowed from enrollment status {1}.").format(outcome, current), frappe.ValidationError)
	if outcome == "Repeat" and not cint(get_program_progression(source.program).get(PROGRAM_ALLOW_REPETITION_FIELD)):
		frappe.throw(_("Repetition is disabled for this Programme / Class."), frappe.ValidationError)


def _destination_offering(source, outcome: str, destination_year: str | None, target_branch: str | None):
	if outcome not in TARGET_OUTCOMES:
		return None
	if not destination_year:
		frappe.throw(_("Destination Academic Session is required."), frappe.ValidationError)
	source_branch = source.get(BRANCH_FIELD)
	branch = target_branch if outcome == "Transfer" and target_branch else source_branch
	branch_row = _allowed_branch(branch)
	source_institution = source.get(INSTITUTION_FIELD)
	if branch_row.get("institution") != source_institution:
		frappe.throw(_("Progression and internal transfer must remain within the same Institution."), frappe.ValidationError)

	source_level = source.get(PROGRESSION_LEVEL_FIELD) if source.meta.has_field(PROGRESSION_LEVEL_FIELD) else None
	if outcome == "Promote":
		target = progression_target(source.program, source_level)
		if target.get("terminal") or not target.get("program"):
			frappe.throw(_("The source Class/Level is terminal or has no configured promotion target."), frappe.ValidationError)
		if not _is_later_year(destination_year, source.academic_year):
			frappe.throw(_("Promotion destination must be a later Academic Session."), frappe.ValidationError)
		target_program = target.get("program")
		target_level = target.get("progression_level")
	elif outcome == "Repeat":
		if not _is_later_year(destination_year, source.academic_year):
			frappe.throw(_("Repeat destination must be a later Academic Session."), frappe.ValidationError)
		target_program = source.program
		target_level = source_level
	else:
		target_program = source.program
		target_level = source_level
		if branch == source_branch and destination_year == source.academic_year:
			frappe.throw(_("Internal transfer must change Branch/Campus or Academic Session."), frappe.ValidationError)

	filters = {
		"school_branch": branch,
		"institution": source_institution,
		"program": target_program,
		"academic_year": destination_year,
		"academic_term": ["is", "not set"],
		"is_active": 1,
		"enrollment_enabled": 1,
	}
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		fields=["name", "offering_title", "offering_code", "school_branch", "institution", "program", "academic_year", "student_batch"],
		order_by="offering_title asc",
		page_length=10,
	)
	if not rows:
		frappe.throw(_("No active sessional Programme Offering matches the destination Class/Programme, Branch and Academic Session."), frappe.ValidationError)
	if len(rows) > 1:
		frappe.throw(_("More than one destination Programme Offering matches this progression. Resolve the duplicate Offering setup first."), frappe.ValidationError)
	return rows[0], target_level


def _destination_groups(offering, target_level: str | None) -> list[dict]:
	filters = {
		BRANCH_FIELD: offering.school_branch,
		OFFERING_FIELD: offering.name,
		"program": offering.program,
		"academic_year": offering.academic_year,
		"academic_term": ["is", "not set"],
		"disabled": 0,
	}
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=["name", "student_group_name", PROGRESSION_LEVEL_FIELD],
		order_by="student_group_name asc",
		page_length=500,
	)
	if target_level:
		rows = [row for row in rows if not row.get(PROGRESSION_LEVEL_FIELD) or row.get(PROGRESSION_LEVEL_FIELD) == target_level]
	return [dict(row) for row in rows]


@frappe.whitelist()
def get_progression_destination_options(
	source_enrollment: str,
	outcome: str,
	destination_academic_year: str | None = None,
	target_branch: str | None = None,
) -> dict:
	_require_access("get_progression_destination_options")
	_require_manager()
	source = _source_enrollment(source_enrollment)
	_validate_outcome(source, outcome)
	if outcome not in TARGET_OUTCOMES:
		return {"source": source.name, "outcome": outcome, "offering": None, "student_groups": []}
	offering, target_level = _destination_offering(source, outcome, destination_academic_year, target_branch)
	return {
		"source": source.name,
		"outcome": outcome,
		"offering": dict(offering),
		"target_program": offering.program,
		"target_progression_level": target_level,
		"student_groups": _destination_groups(offering, target_level),
	}


def _validate_target_group(group_name: str | None, offering, target_level: str | None) -> dict | None:
	if not group_name:
		return None
	group = frappe.get_doc("Student Group", group_name)
	group.check_permission("read")
	if cint(group.disabled):
		frappe.throw(_("Destination Class Arm / Group must be active."), frappe.ValidationError)
	if group.get(BRANCH_FIELD) != offering.school_branch or group.get(OFFERING_FIELD) != offering.name:
		frappe.throw(_("Destination Class Arm / Group must belong to the destination Programme Offering and Branch."), frappe.ValidationError)
	if group.program != offering.program or group.academic_year != offering.academic_year:
		frappe.throw(_("Destination Class Arm / Group must match the destination Programme and Academic Session."), frappe.ValidationError)
	if target_level and group.meta.has_field(PROGRESSION_LEVEL_FIELD) and group.get(PROGRESSION_LEVEL_FIELD) not in (None, "", target_level):
		frappe.throw(_("Destination Class Arm / Group Academic Level does not match the progression target."), frappe.ValidationError)
	return {"name": group.name, "student_group_name": group.student_group_name}


def _plan_row(source_name: str, outcome: str, destination_year: str | None, target_branch: str | None, target_group: str | None) -> dict:
	source = _source_enrollment(source_name)
	_validate_outcome(source, outcome)
	evidence = _evidence_map(source.get(BRANCH_FIELD), source.academic_year, [source.student]).get(source.student) or {}
	recommendation = _recommendation(source.as_dict(), _status_map([source.name]).get(source.name, "Active"), evidence)
	plan = {
		"source_enrollment": source.name,
		"student": source.student,
		"student_name": source.student_name,
		"source_program": source.program,
		"source_academic_year": source.academic_year,
		"source_progression_level": source.get(PROGRESSION_LEVEL_FIELD) if source.meta.has_field(PROGRESSION_LEVEL_FIELD) else None,
		"outcome": outcome,
		"recommendation": recommendation,
		"evidence": evidence,
		"target_offering": None,
		"target_program": None,
		"target_progression_level": None,
		"target_student_group": None,
		"status": "ready",
		"blocker": "",
	}
	if outcome in TARGET_OUTCOMES:
		offering, target_level = _destination_offering(source, outcome, destination_year, target_branch)
		group = _validate_target_group(target_group, offering, target_level)
		plan.update({
			"target_offering": dict(offering),
			"target_program": offering.program,
			"target_progression_level": target_level,
			"target_student_group": group,
		})
	return plan


def _batch_payload(payload: str | dict) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("Progression payload is invalid."), frappe.ValidationError)
	return payload


@frappe.whitelist(methods=["POST"])
def preview_progression_batch(payload: str | dict) -> dict:
	_require_access("preview_progression_batch")
	_require_manager()
	data = _batch_payload(payload)
	sources = _parse_names(data.get("source_enrollments"), label="students")
	outcome = str(data.get("outcome") or "").strip()
	destination_year = str(data.get("destination_academic_year") or "").strip() or None
	target_branch = str(data.get("target_branch") or "").strip() or None
	target_group = str(data.get("target_student_group") or "").strip() or None
	rows = []
	for source in sources:
		try:
			rows.append(_plan_row(source, outcome, destination_year, target_branch, target_group))
		except (frappe.ValidationError, frappe.PermissionError) as exc:
			rows.append({"source_enrollment": source, "outcome": outcome, "status": "blocked", "blocker": str(exc)})
	return {
		"outcome": outcome,
		"destination_academic_year": destination_year,
		"target_branch": target_branch,
		"target_student_group": target_group,
		"rows": rows,
		"summary": {
			"selected": len(rows),
			"ready": sum(1 for row in rows if row.get("status") == "ready"),
			"blocked": sum(1 for row in rows if row.get("status") == "blocked"),
		},
	}


def _course_names(program: str) -> list[str]:
	return [
		row.course
		for row in frappe.get_all(
			"Program Course",
			filters={"parent": program, "parenttype": "Program"},
			fields=["course", "idx"],
			order_by="idx asc",
			page_length=0,
		)
		if row.course
	]


def _prepare_target_enrollment(plan: dict, reason: str) -> tuple[dict, bool]:
	source = _source_enrollment(plan["source_enrollment"])
	offering = frappe._dict(plan["target_offering"])
	existing = frappe.db.get_value(
		"Program Enrollment",
		{
			"student": source.student,
			OFFERING_FIELD: offering.name,
			"docstatus": ["!=", 2],
		},
		["name", "docstatus", PROGRESSION_SOURCE_FIELD, PROGRESSION_OUTCOME_FIELD],
		as_dict=True,
	)
	if existing:
		if existing.get(PROGRESSION_SOURCE_FIELD) != source.name or existing.get(PROGRESSION_OUTCOME_FIELD) != plan["outcome"]:
			frappe.throw(_("A destination enrollment already exists outside this progression plan. Review it manually."), frappe.DuplicateEntryError)
		return {"name": existing.name, "docstatus": existing.docstatus}, False

	doc = frappe.new_doc("Program Enrollment")
	doc.student = source.student
	doc.student_name = source.student_name
	doc.enrollment_date = nowdate()
	doc.program = offering.program
	doc.academic_year = offering.academic_year
	doc.academic_term = None
	doc.student_batch_name = offering.get("student_batch")
	if doc.meta.has_field(OFFERING_FIELD):
		doc.set(OFFERING_FIELD, offering.name)
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, offering.institution)
	if doc.meta.has_field(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, offering.school_branch)
	if doc.meta.has_field(PROGRESSION_LEVEL_FIELD):
		doc.set(PROGRESSION_LEVEL_FIELD, plan.get("target_progression_level"))
	for course in _course_names(offering.program):
		doc.append("courses", {"course": course})
	doc.set(PROGRESSION_SOURCE_FIELD, source.name)
	doc.set(PROGRESSION_OUTCOME_FIELD, plan["outcome"])
	doc.set(PROGRESSION_REASON_FIELD, reason)
	doc.set(PROGRESSION_TARGET_GROUP_FIELD, (plan.get("target_student_group") or {}).get("name"))
	doc.set(PROGRESSION_RECOMMENDATION_FIELD, (plan.get("recommendation") or {}).get("label"))
	doc.set(PROGRESSION_EVIDENCE_FIELD, json.dumps(plan.get("evidence") or {}, sort_keys=True))
	doc.insert()
	return {"name": doc.name, "docstatus": doc.docstatus}, True


@frappe.whitelist(methods=["POST"])
def prepare_progression_batch(payload: str | dict) -> dict:
	_require_access("prepare_progression_batch")
	_require_manager(create_enrollment=True)
	data = _batch_payload(payload)
	preview = preview_progression_batch(data)
	if preview["summary"]["blocked"]:
		frappe.throw(_("Resolve all progression blockers before preparing destination enrollments."), frappe.ValidationError)
	outcome = preview.get("outcome")
	if outcome not in TARGET_OUTCOMES:
		frappe.throw(_("This outcome does not require a destination enrollment. Use Finalize after preview approval."), frappe.ValidationError)
	reason = str(data.get("reason") or "").strip()
	if not reason:
		frappe.throw(_("Enter a progression decision note/reason before preparing destination enrollments."), frappe.ValidationError)
	created = []
	existing = []
	for row in preview["rows"]:
		result, was_created = _prepare_target_enrollment(row, reason)
		(created if was_created else existing).append(result)
	return {"created": created, "existing": existing, "created_count": len(created), "existing_count": len(existing), "preview": preview}


def _existing_prepared_target(source_name: str, outcome: str):
	row = frappe.db.get_value(
		"Program Enrollment",
		{PROGRESSION_SOURCE_FIELD: source_name, PROGRESSION_OUTCOME_FIELD: outcome, "docstatus": ["!=", 2]},
		["name", "docstatus", PROGRESSION_TARGET_GROUP_FIELD, PROGRESSION_RECOMMENDATION_FIELD, PROGRESSION_EVIDENCE_FIELD],
		as_dict=True,
	)
	return row


def _allocate_student_to_group(source, target, group_name: str | None) -> None:
	if not group_name:
		return
	group = frappe.get_doc("Student Group", group_name)
	group.check_permission("write")
	if cint(group.disabled):
		frappe.throw(_("Destination Class Arm / Group is disabled."), frappe.ValidationError)
	if group.get(OFFERING_FIELD) != target.get(OFFERING_FIELD) or group.program != target.program or group.academic_year != target.academic_year:
		frappe.throw(_("Destination Class Arm / Group no longer matches the submitted target enrollment."), frappe.ValidationError)
	existing = next((row for row in group.get("students") or [] if row.student == source.student), None)
	if existing:
		if existing.meta.has_field("active"):
			existing.active = 1
	else:
		group.append("students", {"student": source.student, "student_name": source.student_name, "active": 1})
	group.save()


def _existing_final_log(source_name: str, target_name: str | None, new_status: str) -> str | None:
	filters = {"program_enrollment": source_name, "new_status": new_status}
	if target_name:
		filters["target_program_enrollment"] = target_name
	return frappe.db.get_value("EduEdge Enrollment Status Log", filters, "name")


def _existing_finalized_retry(source_name: str, outcome: str) -> dict | None:
	"""Return the latest final decision only when this request is an exact retry.

	Lifecycle statuses can legitimately recur later (for example Suspend -> Reactivate
	-> Suspend). Checking only the latest log avoids treating an old matching status as
	idempotency evidence for a new transition.
	"""
	status = FINAL_STATUS.get(outcome)
	if not status:
		return None
	rows = frappe.get_all(
		"EduEdge Enrollment Status Log",
		filters={"program_enrollment": source_name},
		fields=["name", "new_status", "target_program_enrollment", "target_student_group", "effective_date", "creation"],
		order_by="effective_date desc, creation desc",
		page_length=1,
	)
	if not rows or rows[0].new_status != status:
		return None
	row = rows[0]
	result = {"name": row.name, "new_status": row.new_status, "existing": True}
	if row.target_program_enrollment:
		result["target_program_enrollment"] = row.target_program_enrollment
	if row.target_student_group:
		result["target_student_group"] = row.target_student_group
	return result


def _finalize_target_outcome(source_name: str, outcome: str, reason: str, effective_date: str | None) -> dict:
	source = _source_enrollment(source_name)
	prepared = _existing_prepared_target(source.name, outcome)
	if not prepared:
		frappe.throw(_("Prepare the destination Program Enrollment before finalising this progression."), frappe.ValidationError)
	if cint(prepared.docstatus) != 1:
		frappe.throw(_("Submit the prepared destination Program Enrollment before finalising progression."), frappe.ValidationError)
	target = frappe.get_doc("Program Enrollment", prepared.name)
	status = FINAL_STATUS[outcome]
	existing_log = _existing_final_log(source.name, target.name, status)
	if existing_log:
		return {"name": existing_log, "new_status": status, "target_program_enrollment": target.name, "existing": True}
	log = frappe.get_doc({
		"doctype": "EduEdge Enrollment Status Log",
		"program_enrollment": source.name,
		"new_status": status,
		"effective_date": effective_date or nowdate(),
		"reason": reason,
		"target_program_enrollment": target.name,
		"target_student_group": prepared.get(PROGRESSION_TARGET_GROUP_FIELD),
		"calculated_recommendation": prepared.get(PROGRESSION_RECOMMENDATION_FIELD),
		"evidence_snapshot": prepared.get(PROGRESSION_EVIDENCE_FIELD),
	})
	log.insert()
	_allocate_student_to_group(source, target, prepared.get(PROGRESSION_TARGET_GROUP_FIELD))
	return {"name": log.name, "new_status": log.new_status, "target_program_enrollment": target.name, "target_student_group": log.target_student_group, "existing": False}


def _finalize_direct_outcome(source_name: str, outcome: str, reason: str, effective_date: str | None) -> dict:
	source = _source_enrollment(source_name)
	existing_retry = _existing_finalized_retry(source.name, outcome)
	if existing_retry:
		return existing_retry
	_validate_outcome(source, outcome)
	status = FINAL_STATUS[outcome]
	evidence = _evidence_map(source.get(BRANCH_FIELD), source.academic_year, [source.student]).get(source.student) or {}
	recommendation = _recommendation(source.as_dict(), _status_map([source.name]).get(source.name, "Active"), evidence)
	if outcome == "Graduate":
		target = progression_target(source.program, source.get(PROGRESSION_LEVEL_FIELD) if source.meta.has_field(PROGRESSION_LEVEL_FIELD) else None)
		if not target.get("terminal"):
			frappe.throw(_("Graduate is only valid for a terminal Class or Academic Level."), frappe.ValidationError)
	log = frappe.get_doc({
		"doctype": "EduEdge Enrollment Status Log",
		"program_enrollment": source.name,
		"new_status": status,
		"effective_date": effective_date or nowdate(),
		"reason": reason,
		"calculated_recommendation": recommendation.get("label"),
		"evidence_snapshot": json.dumps(evidence, sort_keys=True),
	})
	log.insert()
	return {"name": log.name, "new_status": log.new_status, "existing": False}


@frappe.whitelist(methods=["POST"])
def finalize_progression_batch(payload: str | dict) -> dict:
	_require_access("finalize_progression_batch")
	_require_manager()
	data = _batch_payload(payload)
	sources = _parse_names(data.get("source_enrollments"), label="students")
	outcome = str(data.get("outcome") or "").strip()
	reason = str(data.get("reason") or "").strip()
	if not reason:
		frappe.throw(_("Enter the final progression decision reason/note."), frappe.ValidationError)
	effective_date = str(data.get("effective_date") or "").strip() or None
	results = []
	blocked = []
	for source in sources:
		try:
			source_doc = _source_enrollment(source)
			existing_retry = _existing_finalized_retry(source_doc.name, outcome)
			if existing_retry:
				results.append(existing_retry)
				continue
			_validate_outcome(source_doc, outcome)
			if outcome in TARGET_OUTCOMES:
				results.append(_finalize_target_outcome(source, outcome, reason, effective_date))
			else:
				results.append(_finalize_direct_outcome(source, outcome, reason, effective_date))
		except (frappe.ValidationError, frappe.PermissionError, frappe.DuplicateEntryError) as exc:
			blocked.append({"source_enrollment": source, "reason": str(exc)})
	return {"outcome": outcome, "finalized": results, "blocked": blocked, "finalized_count": len(results), "blocked_count": len(blocked)}
