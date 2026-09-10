from __future__ import annotations

from contextlib import contextmanager
import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from eduedge.cbt.result_readiness import assert_result_approval_ready

SCHOOL_EXAM = "School Examination"
OBJECTIVE_TYPES = {"Single Choice", "Multiple Choice", "True/False", "Yes/No"}
SCOREABLE_ATTEMPT_STATUSES = {"Submitted", "Auto Submitted"}
SCHEDULE_SCORING_STATUSES = SCOREABLE_ATTEMPT_STATUSES | {"Under Review", "Scored"}
MARKER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}
APPROVER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


@contextmanager
def _result_service():
	previous = getattr(frappe.flags, "in_cbt_result_service", False)
	frappe.flags.in_cbt_result_service = True
	try:
		yield
	finally:
		frappe.flags.in_cbt_result_service = previous


def _require_role(allowed_roles: set[str], action: str) -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(allowed_roles):
		frappe.throw(
			_("You are not authorised to {0}.").format(action),
			frappe.PermissionError,
		)


def _lock(doctype: str, name: str) -> None:
	frappe.db.sql(f"select name from `tab{doctype}` where name=%s for update", name)


def _json(value, fallback):
	if value in (None, ""):
		return fallback
	if isinstance(value, (dict, list)):
		return value
	try:
		return json.loads(value)
	except (TypeError, ValueError):
		return fallback


def _require_attempt_access(attempt):
	if not frappe.has_permission("EduEdge CBT Attempt", "read", doc=attempt):
		frappe.throw(_("You are not permitted to score this CBT Attempt."), frappe.PermissionError)
	if attempt.exam_scope != SCHOOL_EXAM:
		frappe.throw(
			_("Public examination scoring is performed by the central signed-result service."),
			frappe.PermissionError,
		)
	return attempt


def _require_result_access(result):
	if not frappe.has_permission("EduEdge CBT Result", "write", doc=result):
		frappe.throw(_("You are not permitted to mark this CBT Result."), frappe.PermissionError)
	return result


def _answer_is_empty(payload: dict) -> bool:
	return not (
		payload.get("selected_option_ids")
		or str(payload.get("text") or "").strip()
		or payload.get("value") not in (None, "")
	)


def _score_objective(answer_payload: dict, scoring_key, marking_policy: str) -> float:
	"""Use exact option-set matching; partial multiple-choice credit is deliberately excluded."""
	if _answer_is_empty(answer_payload):
		return 0.0
	selected = {str(value) for value in answer_payload.get("selected_option_ids") or []}
	correct = {str(value) for value in _json(scoring_key.correct_option_ids_json, [])}
	if selected == correct:
		return flt(scoring_key.mark)
	if marking_policy == "Disable Negative Marking":
		return 0.0
	return -abs(flt(scoring_key.negative_mark))


def _summary(result) -> dict:
	return {
		"result": result.name,
		"attempt": result.attempt,
		"exam_schedule": result.exam_schedule,
		"candidate_name": result.candidate_name,
		"result_status": result.result_status,
		"question_count": cint(result.question_count),
		"total_marks": flt(result.total_marks),
		"objective_marks_awarded": flt(result.objective_marks_awarded),
		"manual_marks_awarded": flt(result.manual_marks_awarded),
		"total_awarded_marks": flt(result.total_awarded_marks),
		"percentage": flt(result.percentage),
		"pass_percentage": flt(result.pass_percentage),
		"outcome": result.outcome,
		"manual_pending_count": cint(result.manual_pending_count),
	}


def _recalculate_result(result) -> None:
	objective = sum(
		flt(row.awarded_mark)
		for row in result.items
		if row.scoring_method == "Auto Objective"
	)
	manual = sum(
		flt(row.awarded_mark)
		for row in result.items
		if row.scoring_method == "Manual"
	)
	pending = sum(1 for row in result.items if row.marking_status == "Manual Required")
	total_awarded = objective + manual
	percentage = (max(0.0, total_awarded) / flt(result.total_marks) * 100) if flt(result.total_marks) else 0
	result.objective_marks_awarded = objective
	result.manual_marks_awarded = manual
	result.total_awarded_marks = total_awarded
	result.percentage = percentage
	result.manual_pending_count = pending
	if pending:
		result.result_status = "Manual Marking Required"
		result.outcome = "Pending"
	else:
		result.result_status = "Ready for Review"
		result.outcome = "Pass" if percentage >= flt(result.pass_percentage) else "Fail"


@frappe.whitelist()
def score_objective_attempt(attempt_name: str) -> dict:
	"""Create one governed result and auto-score objective questions idempotently."""
	_require_role(APPROVER_ROLES, "score CBT attempts")
	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _require_attempt_access(frappe.get_doc("EduEdge CBT Attempt", attempt_name))

	existing = frappe.db.get_value("EduEdge CBT Result", {"attempt": attempt.name}, "name")
	if existing:
		return _summary(_require_result_access(frappe.get_doc("EduEdge CBT Result", existing)))

	if attempt.attempt_status not in SCOREABLE_ATTEMPT_STATUSES:
		frappe.throw(
			_("Only Submitted or Auto Submitted attempts can be scored."),
			frappe.ValidationError,
		)
	if cint(attempt.reported_pending_sync_count):
		frappe.throw(_("Pending browser answers must be resolved before scoring."), frappe.ValidationError)
	if cint(attempt.requires_review):
		frappe.throw(_("Complete the integrity review before scoring this attempt."), frappe.ValidationError)

	answers = {
		row.question_snapshot_key: _json(row.answer_payload_json, {})
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt.name},
			fields=["question_snapshot_key", "answer_payload_json"],
		)
	}
	keys = {
		row.question_snapshot_key: row
		for row in frappe.get_all(
			"EduEdge CBT Attempt Scoring Key",
			filters={"attempt": attempt.name},
			fields=[
				"question_snapshot_key",
				"question_type",
				"correct_option_ids_json",
				"answer_key",
				"marking_guide",
				"mark",
				"negative_mark",
			],
		)
	}
	if len(keys) != len(attempt.questions):
		frappe.throw(_("The protected scoring-key snapshot is incomplete."), frappe.ValidationError)

	result = frappe.get_doc(
		{
			"doctype": "EduEdge CBT Result",
			"attempt": attempt.name,
			"exam_schedule": attempt.exam_schedule,
			"exam_template": attempt.exam_template,
			"school_branch": attempt.school_branch,
			"course": attempt.course,
			"candidate_assignment": attempt.candidate_assignment,
			"student": attempt.student,
			"candidate_name": attempt.candidate_name,
			"attempt_number": attempt.attempt_number,
			"result_status": "Draft",
			"question_count": len(attempt.questions),
			"total_marks": sum(flt(row.mark) for row in attempt.questions),
			"pass_percentage": attempt.pass_percentage,
		}
	)
	for question in attempt.questions:
		key = keys.get(question.snapshot_key)
		if not key:
			frappe.throw(_("A question is missing its protected scoring key."), frappe.ValidationError)
		payload = answers.get(question.snapshot_key, {})
		if question.question_type in OBJECTIVE_TYPES:
			awarded = _score_objective(payload, key, attempt.marking_policy)
			scoring_method = "Auto Objective"
			marking_status = "Auto Scored"
		else:
			awarded = 0.0
			scoring_method = "Manual"
			marking_status = "Manual Required"
		result.append(
			"items",
			{
				"question_snapshot_key": question.snapshot_key,
				"question_code": question.question_code,
				"question_type": question.question_type,
				"question_text": question.question_text,
				"available_mark": key.mark,
				"negative_mark": key.negative_mark,
				"awarded_mark": awarded,
				"scoring_method": scoring_method,
				"marking_status": marking_status,
			},
		)
	_recalculate_result(result)
	with _result_service():
		result.insert(ignore_permissions=True)
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		"attempt_status",
		"Under Review" if result.manual_pending_count else "Scored",
		update_modified=False,
	)
	return _summary(result)


def _manual_question_context(result, item) -> dict:
	answer = frappe.db.get_value(
		"EduEdge CBT Attempt Answer",
		{"attempt": result.attempt, "question_snapshot_key": item.question_snapshot_key},
		"answer_payload_json",
	)
	key = frappe.db.get_value(
		"EduEdge CBT Attempt Scoring Key",
		{"attempt": result.attempt, "question_snapshot_key": item.question_snapshot_key},
		["answer_key", "marking_guide"],
		as_dict=True,
	)
	return {
		"result": result.name,
		"attempt": result.attempt,
		"exam_schedule": result.exam_schedule,
		"school_branch": result.school_branch,
		"candidate_name": result.candidate_name,
		"student": result.student,
		"question_snapshot_key": item.question_snapshot_key,
		"question_code": item.question_code,
		"question_type": item.question_type,
		"question_text": item.question_text,
		"available_mark": flt(item.available_mark),
		"awarded_mark": flt(item.awarded_mark),
		"marking_status": item.marking_status,
		"candidate_answer": _json(answer, {}),
		"answer_key": key.answer_key if key else "",
		"marking_guide": key.marking_guide if key else "",
		"marker": item.marker,
		"marked_on": item.marked_on,
		"marker_comment": item.marker_comment,
	}


@frappe.whitelist()
def get_manual_marking_queue(
	exam_schedule: str | None = None,
	school_branch: str | None = None,
	limit_start: int = 0,
	limit_page_length: int = 50,
) -> dict:
	_require_role(MARKER_ROLES, "mark CBT responses")
	filters = {"result_status": "Manual Marking Required"}
	if exam_schedule:
		filters["exam_schedule"] = exam_schedule
	if school_branch:
		filters["school_branch"] = school_branch
	result_names = frappe.get_list(
		"EduEdge CBT Result",
		filters=filters,
		pluck="name",
		order_by="modified asc",
		limit_page_length=500,
	)
	queue = []
	for result_name in result_names:
		result = _require_result_access(frappe.get_doc("EduEdge CBT Result", result_name))
		for item in result.items:
			if item.scoring_method != "Manual" or item.marking_status != "Manual Required":
				continue
			queue.append(_manual_question_context(result, item))
	queue.sort(key=lambda row: (row["candidate_name"] or "", row["question_code"] or ""))
	start = max(0, cint(limit_start))
	page_length = min(200, max(1, cint(limit_page_length)))
	return {
		"total": len(queue),
		"limit_start": start,
		"limit_page_length": page_length,
		"rows": queue[start : start + page_length],
	}


@frappe.whitelist()
def apply_manual_mark(
	result_name: str,
	question_snapshot_key: str,
	awarded_mark: float,
	marker_comment: str | None = None,
) -> dict:
	_require_role(MARKER_ROLES, "mark CBT responses")
	_lock("EduEdge CBT Result", result_name)
	result = _require_result_access(frappe.get_doc("EduEdge CBT Result", result_name))
	if result.result_status not in {"Manual Marking Required", "Ready for Review"}:
		frappe.throw(_("This CBT Result is no longer open for marking."), frappe.ValidationError)
	item = next((row for row in result.items if row.question_snapshot_key == question_snapshot_key), None)
	if not item or item.scoring_method != "Manual":
		frappe.throw(_("Select a valid manual-marking question."), frappe.ValidationError)
	new_mark = flt(awarded_mark)
	if new_mark < 0 or new_mark > flt(item.available_mark):
		frappe.throw(
			_("Awarded Mark must be between 0 and {0}.").format(flt(item.available_mark)),
			frappe.ValidationError,
		)
	comment = (marker_comment or "").strip()
	previous_mark = flt(item.awarded_mark)
	if item.marking_status == "Manually Marked" and new_mark != previous_mark and not comment:
		frappe.throw(
			_("A Marker Comment is required when revising a completed manual mark."),
			frappe.ValidationError,
		)
	item.awarded_mark = new_mark
	item.marking_status = "Manually Marked"
	item.marker = frappe.session.user
	item.marked_on = now_datetime()
	item.marker_comment = comment
	_recalculate_result(result)
	with _result_service():
		result.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "EduEdge CBT Marking Log",
				"result": result.name,
				"attempt": result.attempt,
				"exam_schedule": result.exam_schedule,
				"school_branch": result.school_branch,
				"candidate_name": result.candidate_name,
				"question_snapshot_key": question_snapshot_key,
				"previous_mark": previous_mark,
				"new_mark": new_mark,
				"marker_comment": item.marker_comment,
				"acted_by": frappe.session.user,
				"acted_on": now_datetime(),
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		result.attempt,
		"attempt_status",
		"Under Review" if result.manual_pending_count else "Scored",
		update_modified=False,
	)
	return _summary(result)


@frappe.whitelist()
def score_schedule_objective(exam_schedule: str) -> dict:
	_require_role(APPROVER_ROLES, "score CBT attempts")
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read", doc=schedule):
		frappe.throw(_("You are not permitted to score this Examination Schedule."), frappe.PermissionError)
	attempts = frappe.get_list(
		"EduEdge CBT Attempt",
		filters={"exam_schedule": exam_schedule, "attempt_status": ["in", sorted(SCHEDULE_SCORING_STATUSES)]},
		pluck="name",
		order_by="candidate_name asc",
		limit_page_length=1000,
	)
	results = []
	skipped = []
	for attempt_name in attempts:
		try:
			results.append(score_objective_attempt(attempt_name))
		except (frappe.PermissionError, frappe.ValidationError) as error:
			skipped.append({"attempt": attempt_name, "reason": str(error)})
	return {"exam_schedule": exam_schedule, "scored": results, "skipped": skipped}


@frappe.whitelist()
def approve_schedule_results(exam_schedule: str, approval_note: str | None = None) -> dict:
	_require_role(APPROVER_ROLES, "approve CBT results")
	readiness = assert_result_approval_ready(exam_schedule)
	attempt_names = frappe.get_all(
		"EduEdge CBT Attempt",
		filters={"exam_schedule": exam_schedule, "attempt_status": "Scored"},
		pluck="name",
	)
	if not attempt_names:
		frappe.throw(_("No scored attempts are available for approval."), frappe.ValidationError)
	result_names = frappe.get_all(
		"EduEdge CBT Result",
		filters={"attempt": ["in", attempt_names]},
		pluck="name",
	)
	if len(result_names) != len(attempt_names):
		frappe.throw(_("Every scored attempt must have a CBT Result before approval."), frappe.ValidationError)
	approved = []
	for result_name in result_names:
		_lock("EduEdge CBT Result", result_name)
		result = _require_result_access(frappe.get_doc("EduEdge CBT Result", result_name))
		if result.result_status == "Approved":
			approved.append(result.name)
			continue
		if result.result_status != "Ready for Review" or cint(result.manual_pending_count):
			frappe.throw(
				_("Result {0} is not ready for approval.").format(result.name),
				frappe.ValidationError,
			)
		result.result_status = "Approved"
		result.approved_by = frappe.session.user
		result.approved_on = now_datetime()
		result.approval_note = (approval_note or "").strip()
		with _result_service():
			result.save(ignore_permissions=True)
		approved.append(result.name)
	return {
		"exam_schedule": exam_schedule,
		"approved_count": len(approved),
		"approved_results": approved,
		"readiness": readiness,
	}
