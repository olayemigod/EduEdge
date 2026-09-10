from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from eduedge.cbt.result_readiness import assert_result_approval_ready
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

SCHOOL_EXAM = "School Examination"
SYNC_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


@contextmanager
def _result_sync_service():
	previous = getattr(frappe.flags, "in_cbt_result_sync_service", False)
	frappe.flags.in_cbt_result_sync_service = True
	try:
		yield
	finally:
		frappe.flags.in_cbt_result_sync_service = previous


def _require_sync_role(action: str) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(SYNC_ROLES):
		frappe.throw(
			_("You are not authorised to {0}.").format(action),
			frappe.PermissionError,
		)


def _lock(doctype: str, name: str) -> None:
	frappe.db.sql(f"select name from `tab{doctype}` where name=%s for update", name)


def _schedule_context(exam_schedule: str):
	if not exam_schedule:
		frappe.throw(_("Examination Schedule is required."), frappe.ValidationError)
	_lock("EduEdge CBT Exam Schedule", exam_schedule)
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read", doc=schedule):
		frappe.throw(_("You are not permitted to synchronise this Examination Schedule."), frappe.PermissionError)
	if schedule.exam_scope != SCHOOL_EXAM:
		frappe.throw(
			_("Public examination results remain with the central signed-result service."),
			frappe.PermissionError,
		)
	assert_branch_access(schedule.school_branch)
	if schedule.status != "Completed":
		frappe.throw(
			_("Complete the CBT Examination Schedule before preparing academic results."),
			frappe.ValidationError,
		)
	if not schedule.assessment_plan:
		frappe.throw(
			_("Link a submitted Assessment Plan to the CBT Examination Schedule first."),
			frappe.ValidationError,
		)
	plan = frappe.get_doc("Assessment Plan", schedule.assessment_plan)
	if plan.docstatus != 1:
		frappe.throw(_("The linked Assessment Plan must remain submitted."), frappe.ValidationError)
	if plan.get(BRANCH_FIELD) != schedule.school_branch:
		frappe.throw(_("Assessment Plan Branch no longer matches the CBT schedule."), frappe.ValidationError)
	if plan.student_group != schedule.student_group or plan.course != schedule.course:
		frappe.throw(_("Assessment Plan class or subject no longer matches the CBT schedule."), frappe.ValidationError)
	criteria = list(plan.get("assessment_criteria") or [])
	if len(criteria) != 1:
		frappe.throw(
			_("CBT Result Sync V1.1 requires exactly one Assessment Criterion."),
			frappe.ValidationError,
		)
	criterion = criteria[0]
	if abs(flt(plan.maximum_assessment_score) - flt(criterion.maximum_score)) > 0.0001:
		frappe.throw(_("Assessment Plan maximum score must match its single criterion."), frappe.ValidationError)
	return schedule, plan, criterion


def _approved_results(schedule, plan) -> tuple[list, dict]:
	readiness = assert_result_approval_ready(schedule.name)
	rows = frappe.get_list(
		"EduEdge CBT Result",
		filters={"exam_schedule": schedule.name},
		fields=[
			"name",
			"attempt",
			"result_status",
			"school_branch",
			"course",
			"student",
			"candidate_name",
			"total_marks",
			"total_awarded_marks",
			"assessment_plan",
			"assessment_result",
			"assessment_result_status",
		],
		order_by="candidate_name asc",
		page_length=0,
	)
	if not rows or len(rows) != cint(readiness.get("latest_attempt_count")):
		frappe.throw(
			_("Every completed CBT attempt must have one approved CBT Result before academic sync."),
			frappe.ValidationError,
		)
	for row in rows:
		if row.result_status != "Approved":
			frappe.throw(
				_("CBT Result {0} is not approved.").format(row.name),
				frappe.ValidationError,
			)
		if not row.student:
			frappe.throw(_("CBT Result {0} has no linked Student.").format(row.name), frappe.ValidationError)
		if row.school_branch != schedule.school_branch or row.course != schedule.course:
			frappe.throw(_("CBT Result context does not match its Examination Schedule."), frappe.ValidationError)
		if abs(flt(row.total_marks) - flt(plan.maximum_assessment_score)) > 0.0001:
			frappe.throw(
				_("CBT Result {0} maximum marks do not match the Assessment Plan.").format(row.name),
				frappe.ValidationError,
			)
	return rows, readiness


def _academic_score(cbt_result) -> float:
	return max(0.0, flt(cbt_result.total_awarded_marks))


def _find_existing_assessment_result(cbt_result, plan):
	name = cbt_result.assessment_result
	if name and frappe.db.exists("Assessment Result", name):
		return frappe.get_doc("Assessment Result", name)
	name = frappe.db.get_value(
		"Assessment Result",
		{"eduedge_cbt_result": cbt_result.name},
		"name",
	)
	if name:
		return frappe.get_doc("Assessment Result", name)
	name = frappe.db.get_value(
		"Assessment Result",
		{
			"assessment_plan": plan.name,
			"student": cbt_result.student,
			"docstatus": ["!=", 2],
		},
		"name",
	)
	return frappe.get_doc("Assessment Result", name) if name else None


def _assert_source_owned(assessment_result, cbt_result, schedule, plan, criterion) -> None:
	if assessment_result.assessment_plan != plan.name or assessment_result.student != cbt_result.student:
		frappe.throw(
			_("Assessment Result {0} belongs to another student or plan.").format(assessment_result.name),
			frappe.ValidationError,
		)
	if assessment_result.get("eduedge_cbt_result") != cbt_result.name:
		frappe.throw(
			_("Assessment Result {0} already exists for this student and was not prepared from the selected CBT Result.").format(
				assessment_result.name
			),
			frappe.DuplicateEntryError,
		)
	if assessment_result.get("eduedge_cbt_exam_schedule") != schedule.name:
		frappe.throw(_("Assessment Result CBT schedule source does not match."), frappe.ValidationError)
	if assessment_result.docstatus == 2:
		frappe.throw(
			_("The source-linked Assessment Result is cancelled. Prepare a governed replacement before continuing."),
			frappe.ValidationError,
		)
	if len(assessment_result.details) != 1:
		frappe.throw(_("The prepared Assessment Result criteria were changed manually."), frappe.ValidationError)
	detail = assessment_result.details[0]
	if detail.assessment_criteria != criterion.assessment_criteria:
		frappe.throw(_("The prepared Assessment Result criterion was changed manually."), frappe.ValidationError)
	if abs(flt(detail.score) - _academic_score(cbt_result)) > 0.0001:
		frappe.throw(
			_("The prepared Assessment Result score differs from the approved CBT Result. Resolve it manually; EduEdge will not overwrite it."),
			frappe.ValidationError,
		)


def _update_cbt_result_link(cbt_result_name: str, assessment_result, plan, status: str) -> None:
	cbt_result = frappe.get_doc("EduEdge CBT Result", cbt_result_name)
	cbt_result.assessment_plan = plan.name
	cbt_result.assessment_result = assessment_result.name
	cbt_result.assessment_result_status = status
	if status == "Draft Prepared" and not cbt_result.assessment_result_prepared_on:
		cbt_result.assessment_result_prepared_by = frappe.session.user
		cbt_result.assessment_result_prepared_on = now_datetime()
	if status == "Submitted":
		cbt_result.assessment_result_submitted_by = frappe.session.user
		cbt_result.assessment_result_submitted_on = now_datetime()
	with _result_sync_service():
		cbt_result.save(ignore_permissions=True)


def _append_sync_log(cbt_result, assessment_result, schedule, plan, action: str, from_docstatus: int, note: str) -> None:
	with _result_sync_service():
		frappe.get_doc(
			{
				"doctype": "EduEdge CBT Result Sync Log",
				"cbt_result": cbt_result.name,
				"assessment_result": assessment_result.name,
				"exam_schedule": schedule.name,
				"school_branch": schedule.school_branch,
				"student": cbt_result.student,
				"assessment_plan": plan.name,
				"action": action,
				"from_docstatus": from_docstatus,
				"to_docstatus": assessment_result.docstatus,
				"score_snapshot": _academic_score(cbt_result),
				"acted_by": frappe.session.user,
				"acted_on": now_datetime(),
				"note": note,
			}
		).insert(ignore_permissions=True)


def _prepare_one(cbt_result, schedule, plan, criterion):
	_lock("EduEdge CBT Result", cbt_result.name)
	existing = _find_existing_assessment_result(cbt_result, plan)
	if existing:
		_assert_source_owned(existing, cbt_result, schedule, plan, criterion)
		status = "Submitted" if existing.docstatus == 1 else "Draft Prepared"
		_update_cbt_result_link(cbt_result.name, existing, plan, status)
		return existing, False

	doc = frappe.get_doc(
		{
			"doctype": "Assessment Result",
			"assessment_plan": plan.name,
			"student": cbt_result.student,
			"details": [
				{
					"assessment_criteria": criterion.assessment_criteria,
					"score": _academic_score(cbt_result),
				}
			],
			"comment": _("Prepared from approved EduEdge CBT Result {0}.").format(cbt_result.name),
			"eduedge_cbt_result": cbt_result.name,
			"eduedge_cbt_exam_schedule": schedule.name,
		}
	)
	doc.insert(ignore_permissions=True)
	_update_cbt_result_link(cbt_result.name, doc, plan, "Draft Prepared")
	_append_sync_log(
		cbt_result,
		doc,
		schedule,
		plan,
		"Prepared Draft",
		0,
		_("Created a draft Assessment Result from an approved school CBT Result."),
	)
	return doc, True


@frappe.whitelist()
def prepare_schedule_assessment_results(exam_schedule: str) -> dict:
	"""Prepare source-linked draft Assessment Results without submitting or publishing them."""
	_require_sync_role("prepare CBT Assessment Results")
	schedule, plan, criterion = _schedule_context(exam_schedule)
	results, readiness = _approved_results(schedule, plan)
	prepared = []
	existing = []
	for cbt_result in results:
		assessment_result, created = _prepare_one(cbt_result, schedule, plan, criterion)
		if created:
			prepared.append(assessment_result.name)
		else:
			existing.append(assessment_result.name)
	return {
		"exam_schedule": schedule.name,
		"assessment_plan": plan.name,
		"prepared_count": len(prepared),
		"existing_count": len(existing),
		"prepared_results": prepared,
		"existing_results": existing,
		"readiness": readiness,
	}


@frappe.whitelist()
def submit_schedule_assessment_results(exam_schedule: str) -> dict:
	"""Submit only source-linked, unchanged drafts prepared by the governed sync service."""
	_require_sync_role("submit CBT Assessment Results")
	schedule, plan, criterion = _schedule_context(exam_schedule)
	results, readiness = _approved_results(schedule, plan)
	submitted = []
	existing_submitted = []
	for cbt_result in results:
		_lock("EduEdge CBT Result", cbt_result.name)
		assessment_result = _find_existing_assessment_result(cbt_result, plan)
		if not assessment_result:
			frappe.throw(
				_("Prepare Assessment Result drafts before submission. Missing draft for {0}.").format(cbt_result.candidate_name),
				frappe.ValidationError,
			)
		_assert_source_owned(assessment_result, cbt_result, schedule, plan, criterion)
		if assessment_result.docstatus == 1:
			_update_cbt_result_link(cbt_result.name, assessment_result, plan, "Submitted")
			existing_submitted.append(assessment_result.name)
			continue
		if assessment_result.docstatus != 0:
			frappe.throw(_("Only draft Assessment Results can be submitted."), frappe.ValidationError)
		assessment_result.flags.ignore_permissions = True
		assessment_result.submit()
		_update_cbt_result_link(cbt_result.name, assessment_result, plan, "Submitted")
		_append_sync_log(
			cbt_result,
			assessment_result,
			schedule,
			plan,
			"Submitted",
			0,
			_("Submitted the source-linked Assessment Result. Publication remains a separate approval action."),
		)
		submitted.append(assessment_result.name)
	return {
		"exam_schedule": schedule.name,
		"assessment_plan": plan.name,
		"submitted_count": len(submitted),
		"existing_submitted_count": len(existing_submitted),
		"submitted_results": submitted,
		"existing_submitted_results": existing_submitted,
		"readiness": readiness,
	}


@frappe.whitelist()
def get_schedule_result_sync_status(exam_schedule: str) -> dict:
	_require_sync_role("review CBT Assessment Result sync status")
	schedule, plan, _criterion = _schedule_context(exam_schedule)
	rows = frappe.get_list(
		"EduEdge CBT Result",
		filters={"exam_schedule": schedule.name},
		fields=[
			"name",
			"candidate_name",
			"student",
			"result_status",
			"assessment_result",
			"assessment_result_status",
		],
		order_by="candidate_name asc",
		page_length=0,
	)
	return {
		"exam_schedule": schedule.name,
		"assessment_plan": plan.name,
		"total": len(rows),
		"draft_prepared": sum(1 for row in rows if row.assessment_result_status == "Draft Prepared"),
		"submitted": sum(1 for row in rows if row.assessment_result_status == "Submitted"),
		"not_prepared": sum(1 for row in rows if row.assessment_result_status in (None, "", "Not Prepared")),
		"rows": rows,
	}
