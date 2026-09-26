from __future__ import annotations

from collections import Counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt

from eduedge.api.assessment_assignment_options import assessment_result_plan_query
from eduedge.api.assessment_result_tool_safe import (
	_authorized_plan,
	get_assessment_details as get_safe_assessment_details,
	get_assessment_students as get_safe_assessment_students,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import guard_eduedge_action
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_ANALYTICS_ROWS = 100
MAX_ANALYTICS_SUMMARY = 2000
RESULT_ANALYTICS_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _resolve_branch(branch: str | None = None) -> str:
	resolved = str(branch or (get_current_school_branch() or {}).get("name") or "").strip()
	if not resolved:
		allowed = get_allowed_school_branches()
		if len(allowed) == 1:
			resolved = str(allowed[0].get("name") or "")
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus first."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved


def _get_mark_entry_plan(name: str):
	plan, _group = _authorized_plan(name)
	return plan


def _plan_options(branch: str) -> list[dict]:
	"""Return only submitted plans the current user may operate for mark entry."""
	rows = assessment_result_plan_query(
		"Assessment Plan",
		"",
		"name",
		0,
		250,
		{BRANCH_FIELD: branch},
	)
	return [
		{
			"name": row[0],
			"assessment_name": row[1],
			"student_group": row[2],
			"course": row[3],
			"schedule_date": row[4],
		}
		for row in rows
	]


def _result_can_submit() -> bool:
	try:
		return bool(frappe.has_permission("Assessment Result", "submit"))
	except frappe.PermissionError:
		return False


@frappe.whitelist()
def get_marks_entry_context(
	branch: str | None = None,
	assessment_plan: str | None = None,
) -> dict:
	_require_login()
	resolved_branch = _resolve_branch(branch)
	plans = _plan_options(resolved_branch)
	selected = None
	criteria: list[dict] = []
	students: list[dict] = []
	if assessment_plan:
		plan = _get_mark_entry_plan(assessment_plan)
		if plan.docstatus != 1:
			frappe.throw(_("Marks can only be entered against a submitted Assessment Plan."), frappe.ValidationError)
		if plan.get(BRANCH_FIELD) and plan.get(BRANCH_FIELD) != resolved_branch:
			frappe.throw(_("Assessment Plan belongs to another Branch / Campus."), frappe.PermissionError)
		selected = {
			"name": plan.name,
			"assessment_name": plan.assessment_name,
			"student_group": plan.student_group,
			"assessment_group": plan.assessment_group,
			"course": plan.course,
			"schedule_date": plan.schedule_date,
			"maximum_assessment_score": plan.maximum_assessment_score,
		}
		criteria = get_safe_assessment_details(plan.name) or []
		students = get_safe_assessment_students(plan.name, plan.student_group) or []

	return {
		"allowed_branches": get_allowed_school_branches(),
		"branch": resolved_branch,
		"plans": plans,
		"selected_plan": selected,
		"criteria": criteria,
		"students": students,
		"permissions": {
			"can_create": bool(frappe.has_permission("Assessment Result", "create")),
			"can_write": bool(frappe.has_permission("Assessment Result", "write")),
			"can_submit": _result_can_submit(),
		},
	}


def _parse_scores(scores: str | dict | None) -> dict[str, float]:
	parsed = frappe.parse_json(scores) if isinstance(scores, str) else (scores or {})
	if not isinstance(parsed, dict):
		frappe.throw(_("Scores must be a JSON object."), frappe.ValidationError)
	return {str(key): flt(value) for key, value in parsed.items()}


@frappe.whitelist()
@guard_eduedge_action("assessment", action="save_marks_entry")
def save_marks_entry(
	assessment_plan: str,
	student: str,
	scores: str | dict,
	comment: str | None = None,
) -> dict:
	_require_login()
	plan = _get_mark_entry_plan(assessment_plan)
	if plan.docstatus != 1:
		frappe.throw(_("Marks can only be entered against a submitted Assessment Plan."), frappe.ValidationError)

	criteria_rows = frappe.get_all(
		"Assessment Plan Criteria",
		filters={"parent": plan.name},
		fields=["assessment_criteria", "maximum_score"],
		order_by="idx",
	)
	maximums = {row.assessment_criteria: flt(row.maximum_score) for row in criteria_rows}
	parsed_scores = _parse_scores(scores)
	if set(parsed_scores) != set(maximums):
		frappe.throw(_("Enter a score for every assessment criterion before saving."), frappe.ValidationError)
	for criterion, value in parsed_scores.items():
		if value < 0 or value > maximums[criterion]:
			frappe.throw(
				_("Score for {0} must be between 0 and {1}.").format(criterion, maximums[criterion]),
				frappe.ValidationError,
			)

	existing = frappe.get_list(
		"Assessment Result",
		filters={
			"assessment_plan": plan.name,
			"student": student,
			"docstatus": ["!=", 2],
		},
		fields=["name", "docstatus"],
		limit_page_length=1,
	)
	if existing:
		doc = frappe.get_doc("Assessment Result", existing[0].name)
		if doc.docstatus == 1:
			frappe.throw(_("Submitted Assessment Results cannot be edited."), frappe.ValidationError)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc("Assessment Result")
		doc.assessment_plan = plan.name
		doc.student = student
		if frappe.get_meta("Assessment Result").has_field(BRANCH_FIELD):
			doc.set(BRANCH_FIELD, plan.get(BRANCH_FIELD))
		doc.check_permission("create")

	doc.assessment_plan = plan.name
	doc.student = student
	doc.comment = str(comment or "").strip()
	doc.set(
		"details",
		[
			{"assessment_criteria": criterion, "score": parsed_scores[criterion]}
			for criterion in maximums
		],
	)
	doc.save()
	return {
		"name": doc.name,
		"student": doc.student,
		"student_name": doc.student_name,
		"total_score": doc.total_score,
		"maximum_score": doc.maximum_score,
		"grade": doc.grade,
		"docstatus": doc.docstatus,
		"comment": doc.comment,
		"details": {
			row.assessment_criteria: {"score": row.score, "grade": row.grade}
			for row in doc.details
		},
	}


@frappe.whitelist()
@guard_eduedge_action("assessment", action="submit_marks_entry")
def submit_marks_entry(assessment_plan: str) -> dict:
	_require_login()
	plan = _get_plan(assessment_plan)
	if plan.docstatus != 1:
		frappe.throw(_("Assessment Plan must be submitted before results can be submitted."), frappe.ValidationError)

	rows = frappe.get_list(
		"Assessment Result",
		filters={"assessment_plan": plan.name, "docstatus": 0},
		fields=["name"],
		order_by="name",
		limit_page_length=1000,
	)
	submitted = []
	for row in rows:
		doc = frappe.get_doc("Assessment Result", row.name)
		doc.check_permission("submit")
		doc.submit()
		submitted.append(doc.name)
	return {"submitted": len(submitted), "names": submitted}


def _analytics_filters(
	*,
	branch: str,
	academic_year: str | None,
	academic_term: str | None,
	student_group: str | None,
	course: str | None,
	assessment_group: str | None,
	status: str | None,
) -> dict:
	filters: dict[str, Any] = {}
	meta = frappe.get_meta("Assessment Result")
	if meta.has_field(BRANCH_FIELD):
		filters[BRANCH_FIELD] = branch
	for fieldname, value in (
		("academic_year", academic_year),
		("academic_term", academic_term),
		("student_group", student_group),
		("course", course),
		("assessment_group", assessment_group),
	):
		if value:
			filters[fieldname] = value
	if status == "Draft":
		filters["docstatus"] = 0
	elif status == "Submitted":
		filters["docstatus"] = 1
	elif status == "Cancelled":
		filters["docstatus"] = 2
	return filters


def _analytics_options(branch: str) -> dict:
	filters = {}
	if frappe.get_meta("Assessment Result").has_field(BRANCH_FIELD):
		filters[BRANCH_FIELD] = branch
	rows = frappe.get_list(
		"Assessment Result",
		filters=filters,
		fields=["academic_year", "academic_term", "student_group", "course", "assessment_group"],
		order_by="modified desc",
		limit_page_length=1000,
	)
	def unique(fieldname: str) -> list[str]:
		return sorted({str(row.get(fieldname)) for row in rows if row.get(fieldname)})
	return {
		"academic_years": unique("academic_year"),
		"academic_terms": unique("academic_term"),
		"student_groups": unique("student_group"),
		"courses": unique("course"),
		"assessment_groups": unique("assessment_group"),
	}


@frappe.whitelist()
def get_result_analytics(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	assessment_group: str | None = None,
	status: str | None = None,
) -> dict:
	_require_login()
	if frappe.session.user != "Administrator" and not RESULT_ANALYTICS_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to view Result Analytics."), frappe.PermissionError)
	if not frappe.has_permission("Assessment Result", "read"):
		frappe.throw(_("You are not permitted to view Assessment Results."), frappe.PermissionError)
	resolved_branch = _resolve_branch(branch)
	filters = _analytics_filters(
		branch=resolved_branch,
		academic_year=academic_year,
		academic_term=academic_term,
		student_group=student_group,
		course=course,
		assessment_group=assessment_group,
		status=status,
	)
	fields = [
		"name",
		"student",
		"student_name",
		"assessment_plan",
		"course",
		"student_group",
		"assessment_group",
		"academic_year",
		"academic_term",
		"total_score",
		"maximum_score",
		"grade",
		"docstatus",
	]
	rows = frappe.get_list(
		"Assessment Result",
		filters=filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=MAX_ANALYTICS_SUMMARY + 1,
	)
	truncated = len(rows) > MAX_ANALYTICS_SUMMARY
	rows = rows[:MAX_ANALYTICS_SUMMARY]
	percentages = [
		(flt(row.total_score) / flt(row.maximum_score)) * 100
		for row in rows
		if flt(row.maximum_score) > 0
	]
	grade_counts = Counter(str(row.grade or "Ungraded") for row in rows)
	visible_rows = rows[:MAX_ANALYTICS_ROWS]
	for row in visible_rows:
		row["percentage"] = round(
			(flt(row.total_score) / flt(row.maximum_score)) * 100,
			2,
		) if flt(row.maximum_score) > 0 else 0
		row["status_label"] = "Submitted" if cint(row.docstatus) == 1 else "Cancelled" if cint(row.docstatus) == 2 else "Draft"

	return {
		"allowed_branches": get_allowed_school_branches(),
		"branch": resolved_branch,
		"filters": {
			"academic_year": academic_year or "",
			"academic_term": academic_term or "",
			"student_group": student_group or "",
			"course": course or "",
			"assessment_group": assessment_group or "",
			"status": status or "",
		},
		"options": _analytics_options(resolved_branch),
		"summary": {
			"results": len(rows),
			"submitted": sum(1 for row in rows if cint(row.docstatus) == 1),
			"draft": sum(1 for row in rows if cint(row.docstatus) == 0),
			"average_percentage": round(sum(percentages) / len(percentages), 2) if percentages else 0,
			"highest_percentage": round(max(percentages), 2) if percentages else 0,
			"lowest_percentage": round(min(percentages), 2) if percentages else 0,
			"summary_truncated": truncated,
		},
		"grade_distribution": [
			{"grade": grade, "count": count}
			for grade, count in sorted(grade_counts.items(), key=lambda item: (-item[1], item[0]))
		],
		"rows": visible_rows,
		"row_limit": MAX_ANALYTICS_ROWS,
	}
