from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api.session_launch import _get_launch_by_name, _require_manager
from eduedge.education.custom_fields import BRANCH_FIELD


SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
TEMPLATE_DOCTYPE = "EduEdge CBT Exam Template"
QUESTION_DOCTYPE = "EduEdge CBT Question"
SCHOOL_EXAM = "School Examination"
FIXED_TEMPLATE = "Fixed Question Set"
MAX_ROWS = 5000


def _require_read(doctype: str) -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You are not permitted to view {0}.").format(doctype), frappe.PermissionError)


def _launch(name: str):
	# The orchestration DocType intentionally remains System Manager-only. Normal
	# Session Launch managers access it through this governed API, while every
	# downstream Assessment/CBT list still applies its own Frappe permissions.
	_require_manager("get_session_launch_assessment_cbt_readiness")
	return _get_launch_by_name(str(name or "").strip())


def _terms(academic_year: str) -> list[dict]:
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Term",
			filters={"academic_year": academic_year},
			fields=["name", "term_name", "term_start_date", "term_end_date"],
			order_by="term_start_date asc, name asc",
			page_length=500,
		)
	]


def _branches(institution: str) -> list[dict]:
	return [
		dict(row)
		for row in frappe.get_list(
			"EduEdge School Branch",
			filters={"institution": institution, "enabled": 1},
			fields=["name", "branch_name", "institution", "company"],
			order_by="branch_name asc, name asc",
			page_length=500,
		)
	]


def _class_arms(branches: list[str], academic_year: str) -> list[dict]:
	if not branches or not frappe.get_meta("Student Group").has_field(BRANCH_FIELD):
		return []
	return [
		dict(row)
		for row in frappe.get_list(
			"Student Group",
			filters={BRANCH_FIELD: ["in", branches], "academic_year": academic_year, "disabled": 0},
			fields=["name", "student_group_name", "program", BRANCH_FIELD],
			order_by="student_group_name asc, name asc",
			page_length=MAX_ROWS,
		)
	]


def _assessment_plans(branches: list[str], academic_year: str) -> list[dict]:
	if not branches:
		return []
	_require_read("Assessment Plan")
	return [
		dict(row)
		for row in frappe.get_list(
			"Assessment Plan",
			filters={BRANCH_FIELD: ["in", branches], "academic_year": academic_year},
			fields=[
				"name",
				"assessment_name",
				"student_group",
				"assessment_group",
				"course",
				"academic_term",
				"schedule_date",
				"examiner_name",
				"docstatus",
				BRANCH_FIELD,
			],
			order_by="schedule_date asc, name asc",
			page_length=MAX_ROWS,
		)
	]


def _approved_templates(institution: str, branches: list[dict]) -> list[dict]:
	if not frappe.has_permission(TEMPLATE_DOCTYPE, "read"):
		return []
	branch_names = {row["name"] for row in branches}
	companies = {row.get("company") for row in branches if row.get("company")}
	rows = frappe.get_list(
		TEMPLATE_DOCTYPE,
		filters={"exam_scope": SCHOOL_EXAM, "template_mode": FIXED_TEMPLATE, "status": "Approved"},
		fields=[
			"name",
			"template_title",
			"template_reuse_scope",
			"company",
			"institution",
			"school_branch",
			"academic_year",
			"academic_term",
			"course",
			"question_count",
			"default_examination_centre",
		],
		page_length=MAX_ROWS,
	)
	visible: list[dict] = []
	for raw in rows:
		row = dict(raw)
		scope = row.get("template_reuse_scope")
		if scope == "Branch-wide" and row.get("school_branch") not in branch_names:
			continue
		if scope == "Institution-wide" and row.get("institution") != institution:
			continue
		if scope == "Universal" and row.get("company") not in companies:
			continue
		visible.append(row)
	return visible


def _approved_question_count(institution: str, branches: list[str]) -> int:
	if not frappe.has_permission(QUESTION_DOCTYPE, "read") or not branches:
		return 0
	return len(
		frappe.get_list(
			QUESTION_DOCTYPE,
			filters={
				"ownership_scope": "School Question Bank",
				"institution": institution,
				"school_branch": ["in", branches],
				"status": "Approved",
			},
			fields=["name"],
			page_length=MAX_ROWS,
		)
	)


def _cbt_schedules(branches: list[str], academic_year: str) -> list[dict]:
	if not branches or not frappe.has_permission(SCHEDULE_DOCTYPE, "read"):
		return []
	return [
		dict(row)
		for row in frappe.get_list(
			SCHEDULE_DOCTYPE,
			filters={"exam_scope": SCHOOL_EXAM, "school_branch": ["in", branches], "academic_year": academic_year},
			fields=[
				"name",
				"schedule_title",
				"school_branch",
				"course",
				"student_group",
				"academic_term",
				"assessment_plan",
				"exam_template",
				"examination_centre",
				"primary_invigilator",
				"scheduled_start",
				"status",
			],
			order_by="scheduled_start asc, name asc",
			page_length=MAX_ROWS,
		)
	]


def _candidate_counts(schedules: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
	names = [row["name"] for row in schedules]
	if not names or not frappe.has_permission(ASSIGNMENT_DOCTYPE, "read"):
		return {}, {}
	assigned: dict[str, int] = defaultdict(int)
	for row in frappe.get_list(
		ASSIGNMENT_DOCTYPE,
		filters={"exam_schedule": ["in", names]},
		fields=["exam_schedule", "assignment_status"],
		page_length=MAX_ROWS,
	):
		if row.assignment_status not in {"Withdrawn", "Disqualified"}:
			assigned[row.exam_schedule] += 1

	expected: dict[str, int] = {}
	for schedule in schedules:
		group = schedule.get("student_group")
		if not group:
			expected[schedule["name"]] = 0
			continue
		expected[schedule["name"]] = cint(
			frappe.db.count("Student Group Student", {"parent": group, "active": 1})
		)
	return dict(assigned), expected


def _assessment_term_row(term: dict, plans: list[dict], class_arms: list[dict]) -> dict:
	term_plans = [row for row in plans if row.get("academic_term") == term["name"]]
	submitted = [row for row in term_plans if cint(row.get("docstatus")) == 1]
	drafts = [row for row in term_plans if cint(row.get("docstatus")) == 0]
	planned_groups = {row.get("student_group") for row in submitted if row.get("student_group")}
	missing_groups = [row for row in class_arms if row["name"] not in planned_groups]
	missing_examiner = [row for row in submitted if not row.get("examiner_name")]

	if not class_arms:
		status = "Attention"
		message = "No active Class Arms are available in the accessible Branch scope for this Session."
	elif not term_plans:
		status = "Attention"
		message = "No Assessment Plans have been prepared for this Term."
	elif drafts or missing_groups or missing_examiner:
		status = "Attention"
		message = "Assessment planning has unresolved coverage or draft records."
	else:
		status = "Ready"
		message = "Every active Class Arm has at least one submitted Assessment Plan for this Term."

	return {
		"academic_term": term["name"],
		"term_name": term.get("term_name") or term["name"],
		"status": status,
		"message": message,
		"plans": len(term_plans),
		"submitted_plans": len(submitted),
		"draft_plans": len(drafts),
		"class_arms": len(class_arms),
		"covered_class_arms": len({row["name"] for row in class_arms if row["name"] in planned_groups}),
		"missing_class_arms": len(missing_groups),
		"missing_examiner": len(missing_examiner),
		"missing_class_arm_names": [row.get("student_group_name") or row["name"] for row in missing_groups[:20]],
	}


def _cbt_term_row(term: dict, schedules: list[dict], assigned: dict[str, int], expected: dict[str, int]) -> dict:
	term_schedules = [row for row in schedules if row.get("academic_term") == term["name"]]
	if not term_schedules:
		return {
			"academic_term": term["name"],
			"term_name": term.get("term_name") or term["name"],
			"status": "Not Planned",
			"message": "No CBT sitting is configured for this Term. This does not block Session Launch.",
			"schedules": 0,
			"ready_schedules": 0,
			"attention_schedules": 0,
			"assigned_candidates": 0,
			"expected_candidates": 0,
			"candidate_gap": 0,
		}

	attention: list[str] = []
	ready_count = 0
	total_assigned = 0
	total_expected = 0
	for row in term_schedules:
		name = row["name"]
		actual = cint(assigned.get(name))
		planned = cint(expected.get(name))
		total_assigned += actual
		total_expected += planned
		missing = []
		if not row.get("student_group"):
			missing.append("Class Arm")
		if not row.get("course"):
			missing.append("Subject")
		if not row.get("assessment_plan"):
			missing.append("submitted Assessment Plan")
		if not row.get("examination_centre"):
			missing.append("Examination Centre")
		if not row.get("primary_invigilator"):
			missing.append("Primary Invigilator")
		if planned and actual < planned:
			missing.append(f"Candidate coverage {actual}/{planned}")
		if row.get("status") == "Draft":
			missing.append("Ready status")
		if missing:
			attention.append(f"{row.get('schedule_title') or name}: {', '.join(missing)}")
		else:
			ready_count += 1

	status = "Ready" if not attention else "Attention"
	return {
		"academic_term": term["name"],
		"term_name": term.get("term_name") or term["name"],
		"status": status,
		"message": "Configured CBT sittings are operationally ready." if status == "Ready" else "Configured CBT sittings need attention before they are used.",
		"schedules": len(term_schedules),
		"ready_schedules": ready_count,
		"attention_schedules": len(term_schedules) - ready_count,
		"assigned_candidates": total_assigned,
		"expected_candidates": total_expected,
		"candidate_gap": max(total_expected - total_assigned, 0),
		"issues": attention[:20],
	}


@frappe.whitelist()
def get_assessment_cbt_readiness(launch: str) -> dict:
	"""Return read-only Session Launch readiness for Assessment and optional CBT setup.

	Assessment is a launch-readiness concern. CBT is optional: an unplanned Term is
	neutral, while an existing CBT Schedule must satisfy the governed schedule,
	assessment-plan, centre, invigilation and candidate-assignment contracts.
	"""
	doc = _launch(launch)
	terms = _terms(doc.academic_year)
	branch_rows = _branches(doc.institution)
	branch_names = [row["name"] for row in branch_rows]
	class_arms = _class_arms(branch_names, doc.academic_year)
	plans = _assessment_plans(branch_names, doc.academic_year)
	templates = _approved_templates(doc.institution, branch_rows)
	schedules = _cbt_schedules(branch_names, doc.academic_year)
	assigned, expected = _candidate_counts(schedules)

	assessment_rows = [_assessment_term_row(term, plans, class_arms) for term in terms]
	cbt_rows = [_cbt_term_row(term, schedules, assigned, expected) for term in terms]
	assessment_ready = bool(terms) and all(row["status"] == "Ready" for row in assessment_rows)
	cbt_attention = any(row["status"] == "Attention" for row in cbt_rows)
	cbt_planned = any(row["status"] != "Not Planned" for row in cbt_rows)

	return {
		"launch": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"branches": branch_rows,
		"terms": terms,
		"assessment": {
			"status": "Ready" if assessment_ready else "Attention",
			"ready": assessment_ready,
			"plans": len(plans),
			"submitted_plans": sum(1 for row in plans if cint(row.get("docstatus")) == 1),
			"draft_plans": sum(1 for row in plans if cint(row.get("docstatus")) == 0),
			"class_arms": len(class_arms),
			"term_rows": assessment_rows,
		},
		"cbt": {
			"status": "Attention" if cbt_attention else "Ready" if cbt_planned else "Not Planned",
			"planned": cbt_planned,
			"ready": cbt_planned and not cbt_attention,
			"approved_templates": len(templates),
			"templates_with_questions": sum(1 for row in templates if cint(row.get("question_count")) > 0),
			"approved_question_bank_questions": _approved_question_count(doc.institution, branch_names),
			"schedules": len(schedules),
			"term_rows": cbt_rows,
		},
		"overall": {
			"status": "Ready" if assessment_ready and not cbt_attention else "Attention",
			"ready": assessment_ready and not cbt_attention,
			"cbt_optional": True,
			"message": (
				"Assessment readiness is complete and any configured CBT sittings are ready."
				if assessment_ready and not cbt_attention
				else "Resolve Assessment readiness and any configured CBT exceptions before final Session review."
			),
		},
		"actions": [
			{"key": "assessment_operations", "label": "Assessment Operations", "route": "/app/eduedge-assessment-operations"},
			{"key": "question_bank", "label": "Question Bank", "route": "/app/eduedge-question-bank"},
			{"key": "exam_templates", "label": "Exam Templates", "route": "/app/eduedge-exam-templates"},
			{"key": "cbt_schedule", "label": "CBT Schedules", "route": "/app/eduedge-cbt-schedules"},
		],
	}
