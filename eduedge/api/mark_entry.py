from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt

from education.education.api import get_assessment_details, get_assessment_result_doc

ALLOWED_SCORE_STATES = {"Scored", "Absent", "Exempt", "Not Offered"}


def _load_rows(rows) -> list[dict]:
	if isinstance(rows, str):
		rows = json.loads(rows)
	if not isinstance(rows, list):
		frappe.throw(_("Rows must be a list."), frappe.ValidationError)
	return rows


def _get_plan(assessment_plan: str):
	plan = frappe.get_doc("Assessment Plan", assessment_plan)
	plan.check_permission("read")
	if plan.docstatus != 1:
		frappe.throw(_("Assessment Plan must be submitted before marks can be entered."), frappe.ValidationError)
	return plan


def _criteria_map(assessment_plan: str) -> dict[str, float]:
	return {
		row.assessment_criteria: flt(row.maximum_score)
		for row in get_assessment_details(assessment_plan)
	}


def _student_members(student_group: str) -> set[str]:
	return set(
		frappe.get_all(
			"Student Group Student",
			filters={"parent": student_group, "parenttype": "Student Group", "active": 1},
			pluck="student",
		)
	)


@frappe.whitelist()
def get_mark_entry_context(assessment_plan: str) -> dict:
	plan = _get_plan(assessment_plan)
	criteria = get_assessment_details(assessment_plan)
	students = frappe.get_all(
		"Student Group Student",
		filters={"parent": plan.student_group, "parenttype": "Student Group", "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
	)
	student_names = [row.student for row in students]
	results = {}
	if student_names:
		fields = ["name", "student", "docstatus", "comment", "total_score", "grade"]
		if frappe.get_meta("Assessment Result").has_field("eduedge_score_state"):
			fields.append("eduedge_score_state")
		for row in frappe.get_all(
			"Assessment Result",
			filters={
				"assessment_plan": assessment_plan,
				"student": ["in", student_names],
				"docstatus": ["!=", 2],
			},
			fields=fields,
			page_length=0,
		):
			results[row.student] = {
				"name": row.name,
				"docstatus": row.docstatus,
				"score_state": row.get("eduedge_score_state") or "Scored",
				"comment": row.comment or "",
				"total_score": row.total_score,
				"grade": row.grade,
			}
	return {
		"assessment_plan": plan.name,
		"student_group": plan.student_group,
		"course": plan.course,
		"maximum_assessment_score": plan.maximum_assessment_score,
		"criteria": [dict(row) for row in criteria],
		"students": [dict(row) for row in students],
		"results": results,
		"score_states": sorted(ALLOWED_SCORE_STATES),
	}


@frappe.whitelist(methods=["POST"])
def save_mark_entry_batch(assessment_plan: str, rows) -> dict:
	plan = _get_plan(assessment_plan)
	rows = _load_rows(rows)
	if not rows:
		return {"saved": [], "count": 0}

	criteria_max = _criteria_map(assessment_plan)
	if not criteria_max:
		frappe.throw(_("Assessment Plan has no assessment criteria."), frappe.ValidationError)
	members = _student_members(plan.student_group)
	saved = []

	for row in rows:
		student = row.get("student")
		if not student or student not in members:
			frappe.throw(
				_("Student {0} is not an active member of this Student Group.").format(student or _("(blank)")),
				frappe.ValidationError,
			)

		state = row.get("score_state") or "Scored"
		if state not in ALLOWED_SCORE_STATES:
			frappe.throw(_("Invalid score state {0}.").format(state), frappe.ValidationError)

		existing = frappe.db.get_value(
			"Assessment Result",
			{
				"student": student,
				"assessment_plan": assessment_plan,
				"docstatus": ["!=", 2],
			},
			["name", "docstatus"],
			as_dict=True,
		)
		if existing and existing.docstatus == 1:
			frappe.throw(
				_("Assessment Result for {0} is already submitted and cannot be changed.").format(student),
				frappe.ValidationError,
			)

		scores = row.get("assessment_details") or {}
		details = []
		if state == "Scored":
			missing = [criteria for criteria in criteria_max if criteria not in scores or scores.get(criteria) in (None, "")]
			if missing:
				frappe.throw(
					_("Complete all assessment criteria for {0} before autosave. Missing: {1}").format(
						student, ", ".join(missing)
					),
					frappe.ValidationError,
				)
			for criteria, maximum in criteria_max.items():
				value = flt(scores.get(criteria))
				if value < 0 or value > maximum:
					frappe.throw(
						_("Score for {0} / {1} must be between 0 and {2}.").format(student, criteria, maximum),
						frappe.ValidationError,
					)
				details.append({"assessment_criteria": criteria, "score": value})
		else:
			details = [
				{"assessment_criteria": criteria, "score": 0}
				for criteria in criteria_max
			]

		result = get_assessment_result_doc(student, assessment_plan)
		if result is None:
			frappe.throw(
				_("Assessment Result for {0} cannot be edited.").format(student),
				frappe.ValidationError,
			)
		result.update(
			{
				"student": student,
				"assessment_plan": assessment_plan,
				"comment": row.get("comment") or "",
				"details": details,
			}
		)
		if result.meta.has_field("eduedge_score_state"):
			result.eduedge_score_state = state
		result.save()

		saved.append(
			{
				"student": student,
				"name": result.name,
				"score_state": state,
				"total_score": result.total_score,
				"grade": result.grade,
				"docstatus": result.docstatus,
			}
		)

	return {"saved": saved, "count": len(saved)}


@frappe.whitelist(methods=["POST"])
def submit_mark_entry_batch(assessment_plan: str) -> dict:
	plan = _get_plan(assessment_plan)
	members = _student_members(plan.student_group)
	results = frappe.get_all(
		"Assessment Result",
		filters={
			"assessment_plan": assessment_plan,
			"student": ["in", sorted(members)],
			"docstatus": 0,
		},
		pluck="name",
	)
	submitted = []
	for name in results:
		doc = frappe.get_doc("Assessment Result", name)
		doc.check_permission("submit")
		doc.submit()
		submitted.append(name)
	return {"submitted": submitted, "count": len(submitted)}
