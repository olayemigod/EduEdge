from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, nowdate

from eduedge.api.academic_operations import _require_academic_operator
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import (
	assignment_capability_enforcement_enabled,
	user_has_instructor_assignment_capability,
)
from eduedge.education.offerings import assert_branch_access


def _resolve_group_offering(group) -> str:
	if not group:
		return ""
	if group.get(OFFERING_FIELD):
		return str(group.get(OFFERING_FIELD) or "")
	filters = {
		"program": group.program,
		"academic_year": group.academic_year,
		"school_branch": group.get(BRANCH_FIELD),
		"is_active": 1,
	}
	if group.academic_term:
		filters["academic_term"] = group.academic_term
	else:
		filters["academic_term"] = ["is", "not set"]
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters=filters,
		pluck="name",
		limit_page_length=2,
	)
	return rows[0] if len(rows) == 1 else ""


def _authorized_plan(assessment_plan: str):
	"""Resolve one submitted plan after EduEdge Branch + mark-entry authorization."""
	_require_academic_operator()
	plan_name = str(assessment_plan or "").strip()
	if not plan_name:
		frappe.throw(_("Select an Assessment Plan."), frappe.ValidationError)

	plan = frappe.db.get_value(
		"Assessment Plan",
		plan_name,
		[
			"name",
			"assessment_name",
			"student_group",
			"course",
			"schedule_date",
			"docstatus",
			BRANCH_FIELD,
		],
		as_dict=True,
	)
	if not plan:
		frappe.throw(_("Assessment Plan does not exist."), frappe.DoesNotExistError)
	if cint(plan.docstatus) != 1:
		frappe.throw(_("Only submitted Assessment Plans can be used for mark entry."), frappe.ValidationError)

	branch = str(plan.get(BRANCH_FIELD) or "")
	if not branch:
		frappe.throw(_("Assessment Plan has no School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(branch)

	group_fields = [
		"name",
		"program",
		"academic_year",
		"academic_term",
		"disabled",
		BRANCH_FIELD,
	]
	if frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
		group_fields.append(OFFERING_FIELD)
	group = frappe.db.get_value(
		"Student Group",
		plan.student_group,
		group_fields,
		as_dict=True,
	)
	if not group or group.disabled or group.get(BRANCH_FIELD) != branch:
		frappe.throw(_("Assessment Plan Student Group is not available in this Branch."), frappe.PermissionError)

	if is_teacher_user() and assignment_capability_enforcement_enabled():
		offering = _resolve_group_offering(group)
		if not offering or not user_has_instructor_assignment_capability(
			"can_enter_marks",
			user=frappe.session.user,
			school_branch=branch,
			program_offering=offering,
			student_group=plan.student_group,
			course=plan.course,
			on_date=nowdate(),
		):
			frappe.throw(
				_("You do not have current mark-entry responsibility for this Assessment Plan."),
				frappe.PermissionError,
			)
	else:
		frappe.get_doc("Assessment Plan", plan.name).check_permission("read")

	return plan, group


def _assert_group_matches(plan, student_group: str | None) -> None:
	provided = str(student_group or "").strip()
	if provided and provided != plan.student_group:
		frappe.throw(
			_("Assessment Plan does not belong to the selected Student Group."),
			frappe.ValidationError,
		)


def _active_roster(plan) -> list[dict]:
	return frappe.db.sql(
		f"""
		select
			student.name as student,
			student.student_name,
			group_student.group_roll_number
		from `tabStudent Group Student` group_student
		inner join `tabStudent` student on student.name = group_student.student
		where group_student.parent = %(student_group)s
			and group_student.parenttype = 'Student Group'
			and group_student.active = 1
			and student.enabled = 1
			and student.`{BRANCH_FIELD}` = %(branch)s
		order by group_student.group_roll_number asc, student.student_name asc
		""",
		{
			"student_group": plan.student_group,
			"branch": plan.get(BRANCH_FIELD),
		},
		as_dict=True,
	)


def _assert_active_student(plan, student: str) -> None:
	student_name = str(student or "").strip()
	if not student_name:
		frappe.throw(_("Select a Student."), frappe.ValidationError)
	if not frappe.db.exists(
		"Student Group Student",
		{
			"parent": plan.student_group,
			"parenttype": "Student Group",
			"student": student_name,
			"active": 1,
		},
	):
		frappe.throw(
			_("Student is not an active member of the Assessment Plan class."),
			frappe.PermissionError,
		)
	student_branch = frappe.db.get_value("Student", student_name, BRANCH_FIELD)
	if student_branch != plan.get(BRANCH_FIELD):
		frappe.throw(_("Student belongs to another Branch / Campus."), frappe.PermissionError)


@frappe.whitelist()
def get_assessment_students(assessment_plan, student_group=None):
	"""Compatibility-safe roster/result read for Frappe Education Assessment Result Tool."""
	plan, _group = _authorized_plan(assessment_plan)
	_assert_group_matches(plan, student_group)
	students = _active_roster(plan)
	if not students:
		return []

	student_names = [row.student for row in students]
	results = frappe.get_all(
		"Assessment Result",
		filters={
			"assessment_plan": plan.name,
			"student": ["in", student_names],
			"docstatus": ["!=", 2],
		},
		fields=["name", "student", "docstatus", "total_score", "grade", "comment"],
		limit_page_length=0,
	)
	results_by_student = {row.student: row for row in results}
	details_by_result: dict[str, list] = {}
	if results:
		for detail in frappe.get_all(
			"Assessment Result Detail",
			filters={"parent": ["in", [row.name for row in results]]},
			fields=["parent", "assessment_criteria", "score", "grade"],
			order_by="idx asc",
			limit_page_length=0,
		):
			details_by_result.setdefault(detail.parent, []).append(detail)

	output = []
	for student in students:
		row = dict(student)
		result = results_by_student.get(student.student)
		if not result:
			row["assessment_details"] = None
			output.append(row)
			continue
		student_result = {
			detail.assessment_criteria: [cstr(detail.score), detail.grade]
			for detail in details_by_result.get(result.name, [])
		}
		student_result["total_score"] = [cstr(result.total_score), result.grade]
		row.update(
			{
				"assessment_details": student_result,
				"comment": result.comment,
				"docstatus": result.docstatus,
				"name": result.name,
			}
		)
		output.append(row)
	return output


@frappe.whitelist()
def get_assessment_details(assessment_plan):
	plan, _group = _authorized_plan(assessment_plan)
	return frappe.get_all(
		"Assessment Plan Criteria",
		filters={"parent": plan.name},
		fields=["assessment_criteria", "maximum_score", "docstatus"],
		order_by="idx asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def mark_assessment_result(assessment_plan, scores):
	"""Save one draft result after exact plan, Branch, roster and mark-capability checks."""
	plan, _group = _authorized_plan(assessment_plan)
	payload = frappe.parse_json(scores) if isinstance(scores, str) else (scores or {})
	student = str(payload.get("student") or "").strip()
	_assert_active_student(plan, student)

	existing = frappe.get_all(
		"Assessment Result",
		filters={
			"assessment_plan": plan.name,
			"student": student,
			"docstatus": ["!=", 2],
		},
		pluck="name",
		limit_page_length=2,
	)
	if len(existing) > 1:
		frappe.throw(_("Multiple active Assessment Results exist for this Student and Plan."), frappe.ValidationError)
	result = frappe.get_doc("Assessment Result", existing[0]) if existing else frappe.new_doc("Assessment Result")
	if cint(result.docstatus) == 1:
		frappe.throw(_("Assessment Result is already submitted."), frappe.ValidationError)

	detail_values = payload.get("assessment_details") or {}
	if not isinstance(detail_values, dict):
		frappe.throw(_("Assessment details must be a score map."), frappe.ValidationError)
	result.update(
		{
			"student": student,
			"assessment_plan": plan.name,
			"comment": payload.get("comment"),
		}
	)
	result.set(
		"details",
		[
			{"assessment_criteria": criteria, "score": flt(score)}
			for criteria, score in detail_values.items()
		],
	)
	result.save()

	return {
		"name": result.name,
		"student": result.student,
		"total_score": result.total_score,
		"grade": result.grade,
		"details": {
			row.assessment_criteria: row.grade
			for row in result.details
		},
	}


@frappe.whitelist()
def submit_assessment_results(assessment_plan, student_group=None):
	"""Submit only draft results inside the authorized plan's active roster."""
	plan, _group = _authorized_plan(assessment_plan)
	_assert_group_matches(plan, student_group)
	student_names = [row.student for row in _active_roster(plan)]
	if not student_names:
		return 0

	result_names = frappe.get_all(
		"Assessment Result",
		filters={
			"assessment_plan": plan.name,
			"student": ["in", student_names],
			"docstatus": 0,
		},
		pluck="name",
		limit_page_length=0,
	)
	count = 0
	for name in result_names:
		doc = frappe.get_doc("Assessment Result", name)
		doc.submit()
		count += 1
	return count
