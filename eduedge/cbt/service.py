from __future__ import annotations

import json
import random
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

from eduedge.cbt.domain import (
	canonical_response,
	classify_sync_update,
	compute_server_deadline,
	is_within_sync_grace,
	objective_answer_key,
	score_objective_response,
	stable_hash,
)
from eduedge.education.offerings import assert_branch_access

CBT_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}
CBT_OPERATOR_ROLES = CBT_MANAGER_ROLES | {"CBT Invigilator", "Teacher"}
ACTIVE_ATTEMPT_STATUSES = {"In Progress", "Pending Sync"}
FINAL_ATTEMPT_STATUSES = {"Submitted", "Timed Out", "Cancelled"}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def _require_manager() -> None:
	_require_login()
	if frappe.session.user != "Administrator" and not CBT_MANAGER_ROLES.intersection(_roles()):
		frappe.throw(_("You are not permitted to manage CBT Exams."), frappe.PermissionError)


def _require_operator() -> None:
	_require_login()
	if frappe.session.user != "Administrator" and not CBT_OPERATOR_ROLES.intersection(_roles()):
		frappe.throw(_("You are not permitted to operate CBT Exams."), frappe.PermissionError)


def _is_student_user() -> bool:
	return "Student" in _roles() and frappe.session.user != "Administrator"


def _hash_sensitive(value: str | None) -> str:
	return stable_hash(str(value)) if value else ""


def _resolve_candidate(student: str | None = None) -> tuple[str, str]:
	_require_login()
	if _is_student_user():
		resolved = frappe.db.get_value("Student", {"student_email_id": frappe.session.user}, "name")
		if not resolved:
			frappe.throw(_("Your user account is not linked to a Student record."), frappe.PermissionError)
		if student and student != resolved:
			frappe.throw(_("Students can only start their own CBT Attempt."), frappe.PermissionError)
		return resolved, frappe.session.user

	_require_operator()
	if not student:
		frappe.throw(_("Select a Student for this CBT Attempt."), frappe.ValidationError)
	student_user = frappe.db.get_value("Student", student, "student_email_id")
	if not student_user:
		frappe.throw(_("The selected Student does not have a portal user email."), frappe.ValidationError)
	return student, student_user


def _candidate_is_eligible(exam, student: str) -> bool:
	return bool(
		frappe.db.exists(
			"Student Group Student",
			{
				"parent": exam.student_group,
				"parenttype": "Student Group",
				"student": student,
				"active": 1,
			},
		)
	)


def _get_exam(exam_name: str):
	exam = frappe.get_doc("EduEdge CBT Exam", exam_name)
	if not _is_student_user():
		assert_branch_access(exam.school_branch)
	return exam


def _transition_exam(exam, status: str) -> None:
	updates: dict[str, Any] = {"status": status}
	now = now_datetime()
	if status == "Scheduled":
		updates.update({"scheduled_by": frappe.session.user, "scheduled_on": now})
	elif status == "Active":
		updates.update({"activated_by": frappe.session.user, "activated_on": now})
	elif status == "Closed":
		updates.update({"closed_by": frappe.session.user, "closed_on": now})
	elif status == "Cancelled":
		updates.update({"cancelled_by": frappe.session.user, "cancelled_on": now})
	for fieldname, value in updates.items():
		exam.set(fieldname, value)
	exam.flags.allow_cbt_transition = True
	exam.save()


def schedule_exam(exam_name: str) -> dict:
	_require_manager()
	exam = _get_exam(exam_name)
	if exam.status != "Draft":
		frappe.throw(_("Only Draft CBT Exams can be scheduled."), frappe.ValidationError)
	_transition_exam(exam, "Scheduled")
	return _exam_summary(exam)


def activate_exam(exam_name: str) -> dict:
	_require_operator()
	exam = _get_exam(exam_name)
	if exam.status != "Scheduled":
		frappe.throw(_("Only Scheduled CBT Exams can be activated."), frappe.ValidationError)
	now = now_datetime()
	if now < get_datetime(exam.start_datetime):
		frappe.throw(_("The CBT Exam cannot be activated before its start time."), frappe.ValidationError)
	if now > get_datetime(exam.end_datetime):
		frappe.throw(_("The CBT Exam availability window has ended."), frappe.ValidationError)
	_transition_exam(exam, "Active")
	return _exam_summary(exam)


def close_exam(exam_name: str) -> dict:
	_require_operator()
	exam = _get_exam(exam_name)
	if exam.status not in {"Scheduled", "Active"}:
		frappe.throw(_("Only Scheduled or Active CBT Exams can be closed."), frappe.ValidationError)
	if exam.status == "Scheduled":
		_transition_exam(exam, "Cancelled")
	else:
		_transition_exam(exam, "Closed")
	return _exam_summary(exam)


def get_exam_access(exam_name: str, student: str | None = None) -> dict:
	resolved_student, student_user = _resolve_candidate(student)
	exam = _get_exam(exam_name)
	now = now_datetime()
	eligible = _candidate_is_eligible(exam, resolved_student)
	active_attempt = frappe.db.get_value(
		"EduEdge CBT Attempt",
		{
			"exam": exam.name,
			"student": resolved_student,
			"status": ["in", sorted(ACTIVE_ATTEMPT_STATUSES)],
		},
		["name", "status", "server_deadline", "sync_grace_ends_on"],
		as_dict=True,
	)
	attempt_count = frappe.db.count("EduEdge CBT Attempt", {"exam": exam.name, "student": resolved_student})
	return {
		"server_time": now,
		"student": resolved_student,
		"student_user": student_user,
		"eligible": eligible,
		"exam": _exam_summary(exam),
		"active_attempt": active_attempt,
		"attempt_count": attempt_count,
		"attempts_remaining": max(0, cint(exam.max_attempts) - attempt_count),
		"can_start": bool(
			eligible
			and exam.status in {"Scheduled", "Active"}
			and get_datetime(exam.start_datetime) <= now <= get_datetime(exam.end_datetime)
			and (active_attempt or attempt_count < cint(exam.max_attempts))
		),
	}


def start_attempt(
	exam_name: str,
	student: str | None = None,
	device_id: str | None = None,
	session_id: str | None = None,
) -> dict:
	resolved_student, student_user = _resolve_candidate(student)
	exam = _get_exam(exam_name)
	now = now_datetime()
	if not _candidate_is_eligible(exam, resolved_student):
		frappe.throw(_("Student is not eligible for this CBT Exam."), frappe.PermissionError)
	if now < get_datetime(exam.start_datetime):
		frappe.throw(_("This CBT Exam has not started."), frappe.ValidationError)
	if now > get_datetime(exam.end_datetime):
		frappe.throw(_("This CBT Exam has closed."), frappe.ValidationError)
	if exam.status == "Scheduled":
		_transition_exam(exam, "Active")
	if exam.status != "Active":
		frappe.throw(_("This CBT Exam is not active."), frappe.ValidationError)

	frappe.db.sql(
		"select name from `tabEduEdge CBT Attempt` where exam=%s and student=%s for update",
		(exam.name, resolved_student),
	)
	active_name = frappe.db.get_value(
		"EduEdge CBT Attempt",
		{
			"exam": exam.name,
			"student": resolved_student,
			"status": ["in", sorted(ACTIVE_ATTEMPT_STATUSES)],
		},
		"name",
	)
	if active_name:
		attempt = frappe.get_doc("EduEdge CBT Attempt", active_name)
		if now <= get_datetime(attempt.sync_grace_ends_on) and exam.allow_resume:
			return _attempt_payload(attempt, resumed=True)
		_mark_attempt_timed_out(attempt)

	attempt_count = frappe.db.count("EduEdge CBT Attempt", {"exam": exam.name, "student": resolved_student})
	if attempt_count >= cint(exam.max_attempts):
		frappe.throw(_("Maximum CBT attempts have been used."), frappe.ValidationError)

	seed = frappe.generate_hash(length=32)
	deadline = compute_server_deadline(
		started_on=now,
		duration_minutes=cint(exam.duration_minutes),
		exam_end_datetime=get_datetime(exam.end_datetime),
	)
	attempt = frappe.get_doc(
		{
			"doctype": "EduEdge CBT Attempt",
			"exam": exam.name,
			"student": resolved_student,
			"user": student_user,
			"school_branch": exam.school_branch,
			"student_group": exam.student_group,
			"course": exam.course,
			"attempt_no": attempt_count + 1,
			"status": "In Progress",
			"started_on": now,
			"server_deadline": deadline,
			"sync_grace_ends_on": deadline + timedelta(minutes=max(0, cint(exam.sync_grace_minutes))),
			"last_client_sequence": -1,
			"network_status": "Online",
			"pending_answer_count": 0,
			"total_questions": cint(exam.total_questions),
			"answered_count": 0,
			"result_status": "Pending",
			"device_id_hash": _hash_sensitive(device_id),
			"session_id": session_id or frappe.generate_hash(length=24),
			"ip_address_hash": _hash_sensitive(getattr(frappe.local, "request_ip", "")),
			"random_seed": seed,
		}
	)
	for snapshot in _build_question_snapshot(exam, seed):
		attempt.append("question_snapshot", snapshot)
	attempt.flags.from_cbt_service = True
	attempt.insert()
	return _attempt_payload(attempt, resumed=False)


def resume_attempt(attempt_name: str) -> dict:
	attempt = _get_attempt(attempt_name)
	_refresh_timeout_state(attempt)
	return _attempt_payload(attempt, resumed=True)


def sync_answers(
	attempt_name: str,
	client_batch_id: str,
	answers: str | list[dict],
	client_pending_count: int = 0,
	network_state: str = "Unknown",
) -> dict:
	attempt = _get_attempt(attempt_name)
	_refresh_timeout_state(attempt, preserve_pending=True)
	if attempt.status not in ACTIVE_ATTEMPT_STATUSES:
		frappe.throw(_("This CBT Attempt no longer accepts answer sync."), frappe.ValidationError)
	client_batch_id = str(client_batch_id or "").strip()
	if not client_batch_id:
		frappe.throw(_("Client batch ID is required for idempotent sync."), frappe.ValidationError)
	rows = _parse_answer_rows(answers)
	existing_log = frappe.db.get_value(
		"EduEdge CBT Sync Log",
		{"attempt": attempt.name, "client_batch_id": client_batch_id},
		[
			"name",
			"received_count",
			"accepted_count",
			"duplicate_count",
			"stale_count",
			"conflict_count",
			"rejected_count",
			"received_on",
		],
		as_dict=True,
	)
	if existing_log:
		return {
			"duplicate_batch": True,
			"sync_log": existing_log,
			"attempt": _attempt_payload(attempt),
		}

	now = now_datetime()
	deadline = get_datetime(attempt.server_deadline)
	grace_end = get_datetime(attempt.sync_grace_ends_on)
	if now > grace_end:
		frappe.throw(_("The pending-sync grace window has ended. Ask the invigilator for help."), frappe.ValidationError)
	late_sync = now > deadline
	counts = {"accepted": 0, "duplicate": 0, "stale": 0, "conflict": 0, "rejected": 0}
	sequences: list[int] = []
	result_rows = []
	for item in rows:
		try:
			result = _sync_one_answer(attempt, item, now=now, late_sync=late_sync)
		except (frappe.ValidationError, frappe.PermissionError, ValueError) as exc:
			counts["rejected"] += 1
			result_rows.append({"question_key": item.get("question_key"), "decision": "Rejected", "reason": str(exc)})
			continue
		decision = result["decision"]
		bucket = {
			"Accepted": "accepted",
			"Accepted With Gap": "accepted",
			"Duplicate": "duplicate",
			"Stale": "stale",
			"Conflict": "conflict",
		}[decision]
		counts[bucket] += 1
		sequences.append(cint(item.get("client_sequence")))
		result_rows.append(result)

	gap_count = sum(1 for row in result_rows if row.get("decision") == "Accepted With Gap")
	pending_count = max(0, cint(client_pending_count), counts["conflict"] + counts["rejected"] + gap_count)
	attempt.last_sync_on = now
	attempt.network_status = network_state if network_state in {"Unknown", "Online", "Offline", "Reconnected"} else "Unknown"
	attempt.last_client_sequence = max([cint(attempt.last_client_sequence), *sequences]) if sequences else cint(attempt.last_client_sequence)
	attempt.pending_answer_count = pending_count
	attempt.answered_count = frappe.db.count(
		"EduEdge CBT Attempt Answer",
		{"attempt": attempt.name, "is_answered": 1},
	)
	if late_sync or pending_count:
		attempt.status = "Pending Sync"
	attempt.flags.from_cbt_service = True
	attempt.save()

	request_payload = {
		"attempt": attempt.name,
		"client_batch_id": client_batch_id,
		"answers": rows,
		"client_pending_count": cint(client_pending_count),
		"network_state": network_state,
	}
	response_payload = {"counts": counts, "answers": result_rows, "pending_answer_count": pending_count}
	log = frappe.get_doc(
		{
			"doctype": "EduEdge CBT Sync Log",
			"attempt": attempt.name,
			"exam": attempt.exam,
			"student": attempt.student,
			"user": attempt.user,
			"school_branch": attempt.school_branch,
			"client_batch_id": client_batch_id,
			"network_state": attempt.network_status,
			"late_sync": late_sync,
			"sequence_from": min(sequences) if sequences else 0,
			"sequence_to": max(sequences) if sequences else 0,
			"received_count": len(rows),
			"accepted_count": counts["accepted"],
			"duplicate_count": counts["duplicate"],
			"stale_count": counts["stale"],
			"conflict_count": counts["conflict"],
			"rejected_count": counts["rejected"],
			"received_on": now,
			"request_hash": stable_hash(request_payload),
			"response_hash": stable_hash(response_payload),
			"remarks": _("Answer sync batch processed."),
		}
	)
	log.flags.from_cbt_service = True
	log.insert()
	return {
		"duplicate_batch": False,
		"sync_log": log.name,
		"counts": counts,
		"answers": result_rows,
		"attempt": _attempt_payload(attempt),
	}


def submit_attempt(
	attempt_name: str,
	client_batch_id: str | None = None,
	answers: str | list[dict] | None = None,
	client_pending_count: int = 0,
	network_state: str = "Online",
) -> dict:
	attempt = _get_attempt(attempt_name)
	if answers is not None:
		sync_answers(
			attempt.name,
			client_batch_id or f"final-{frappe.generate_hash(length=16)}",
			answers,
			client_pending_count=client_pending_count,
			network_state=network_state,
		)
		attempt.reload()
	if attempt.status in FINAL_ATTEMPT_STATUSES:
		return _attempt_payload(attempt)
	if cint(client_pending_count) or cint(attempt.pending_answer_count):
		attempt.status = "Pending Sync"
		attempt.flags.from_cbt_service = True
		attempt.save()
		return _attempt_payload(attempt)

	now = now_datetime()
	attempt.status = "Timed Out" if now > get_datetime(attempt.server_deadline) else "Submitted"
	attempt.submitted_on = now
	attempt.pending_answer_count = 0
	_score_attempt(attempt)
	attempt.result_status = "Provisional"
	attempt.submission_hash = _submission_hash(attempt)
	attempt.flags.from_cbt_service = True
	attempt.save()
	return _attempt_payload(attempt)


def record_integrity_event(attempt_name: str, event_type: str, count: int = 1) -> dict:
	attempt = _get_attempt(attempt_name)
	if attempt.status not in ACTIVE_ATTEMPT_STATUSES:
		return _attempt_payload(attempt)
	count = max(1, min(100, cint(count)))
	if event_type == "tab_switch":
		attempt.tab_switch_count = cint(attempt.tab_switch_count) + count
	elif event_type == "focus_violation":
		attempt.focus_violation_count = cint(attempt.focus_violation_count) + count
	else:
		frappe.throw(_("Unsupported CBT integrity event."), frappe.ValidationError)
	attempt.flags.from_cbt_service = True
	attempt.save()
	return _attempt_payload(attempt)


def get_invigilator_monitor(exam_name: str) -> dict:
	_require_operator()
	exam = _get_exam(exam_name)
	candidate_rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": exam.student_group, "parenttype": "Student Group", "active": 1},
		fields=["student", "student_name", "group_roll_number"],
		order_by="group_roll_number asc, student_name asc",
		page_length=1000,
	)
	attempts = frappe.get_all(
		"EduEdge CBT Attempt",
		filters={"exam": exam.name},
		fields=[
			"name",
			"student",
			"attempt_no",
			"status",
			"started_on",
			"server_deadline",
			"last_sync_on",
			"network_status",
			"answered_count",
			"total_questions",
			"pending_answer_count",
			"tab_switch_count",
			"focus_violation_count",
			"result_status",
		],
		order_by="student asc, attempt_no desc",
		page_length=2000,
	)
	latest_by_student = {}
	for row in attempts:
		latest_by_student.setdefault(row.student, row)
	candidates = []
	for row in candidate_rows:
		attempt = latest_by_student.get(row.student)
		candidates.append(
			{
				"student": row.student,
				"student_name": row.student_name,
				"roll_number": row.group_roll_number,
				"attempt": attempt,
				"status": attempt.status if attempt else "Not Started",
				"pending_sync": bool(attempt and (attempt.status == "Pending Sync" or attempt.pending_answer_count)),
			}
		)
	return {
		"server_time": now_datetime(),
		"exam": _exam_summary(exam),
		"counts": {
			"candidates": len(candidates),
			"not_started": sum(1 for row in candidates if row["status"] == "Not Started"),
			"in_progress": sum(1 for row in candidates if row["status"] == "In Progress"),
			"pending_sync": sum(1 for row in candidates if row["pending_sync"]),
			"submitted": sum(1 for row in candidates if row["status"] in {"Submitted", "Timed Out"}),
		},
		"candidates": candidates,
	}


def approve_attempt_result(attempt_name: str) -> dict:
	_require_manager()
	attempt = _get_attempt(attempt_name, require_owner=False)
	if attempt.status not in {"Submitted", "Timed Out"}:
		frappe.throw(_("Only submitted or timed-out CBT Attempts can be approved."), frappe.ValidationError)
	if cint(attempt.pending_answer_count) or attempt.status == "Pending Sync":
		frappe.throw(_("Resolve all pending answer sync before result approval."), frappe.ValidationError)
	attempt.result_status = "Approved"
	attempt.result_approved_by = frappe.session.user
	attempt.result_approved_on = now_datetime()
	attempt.flags.from_cbt_service = True
	attempt.save()
	return _attempt_payload(attempt, include_result=True)


def _get_attempt(attempt_name: str, *, require_owner: bool = True):
	_require_login()
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if _is_student_user() and attempt.user != frappe.session.user:
		frappe.throw(_("Students can only access their own CBT Attempt."), frappe.PermissionError)
	if not _is_student_user():
		_require_operator()
		assert_branch_access(attempt.school_branch)
	return attempt


def _build_question_snapshot(exam, seed: str) -> list[dict]:
	exam_rows = list(exam.questions)
	if exam.randomize_questions:
		_rng(seed, "questions").shuffle(exam_rows)
	snapshots = []
	for sequence, exam_row in enumerate(exam_rows, start=1):
		question = frappe.get_doc("EduEdge CBT Question", exam_row.question)
		options = [
			{
				"option_key": row.option_key,
				"option_text": row.option_text,
				"display_order": cint(row.display_order),
				"is_correct": bool(row.is_correct),
			}
			for row in question.options
		]
		answer_key = objective_answer_key(question.question_type, options)
		candidate_options = [
			{"option_key": row["option_key"], "option_text": row["option_text"]}
			for row in options
		]
		if exam.randomize_options:
			_rng(seed, f"options:{question.name}").shuffle(candidate_options)
		snapshots.append(
			{
				"snapshot_key": stable_hash({"seed": seed, "question": question.name})[:32],
				"sequence": sequence,
				"source_question": question.name,
				"question_type": question.question_type,
				"marks": flt(exam_row.marks),
				"question_text": question.question_text,
				"options_json": json.dumps(candidate_options, ensure_ascii=False),
				"answer_key_json": json.dumps(answer_key, ensure_ascii=False),
				"source_content_hash": question.content_hash,
			}
		)
	return snapshots


def _rng(seed: str, scope: str) -> random.Random:
	return random.Random(int(stable_hash({"seed": seed, "scope": scope})[:16], 16))


def _parse_answer_rows(value: str | list[dict]) -> list[dict]:
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except Exception as exc:
			frappe.throw(_("Answer sync payload is invalid JSON: {0}").format(exc), frappe.ValidationError)
	if not isinstance(value, list):
		frappe.throw(_("Answer sync payload must be a list."), frappe.ValidationError)
	if len(value) > 500:
		frappe.throw(_("A single answer sync batch cannot exceed 500 rows."), frappe.ValidationError)
	return [row for row in value if isinstance(row, dict)]


def _sync_one_answer(attempt, item: dict, *, now, late_sync: bool) -> dict:
	question_key = str(item.get("question_key") or "").strip()
	if not question_key:
		raise ValueError("Question snapshot key is required.")
	snapshot = next((row for row in attempt.question_snapshot if row.snapshot_key == question_key), None)
	if not snapshot:
		raise ValueError("Question is not part of this CBT Attempt.")
	sequence = cint(item.get("client_sequence"))
	client_saved_on = get_datetime(item.get("client_saved_on")) if item.get("client_saved_on") else None
	if late_sync and (not client_saved_on or client_saved_on > get_datetime(attempt.server_deadline)):
		raise ValueError("Late sync answer was not saved before the server deadline.")
	response = canonical_response(item.get("response"))
	payload_hash = stable_hash(response)
	answer_key = stable_hash({"attempt": attempt.name, "question_key": question_key})
	existing = frappe.db.get_value(
		"EduEdge CBT Attempt Answer",
		{"answer_key": answer_key},
		["name", "client_sequence", "response_hash"],
		as_dict=True,
	)
	decision = classify_sync_update(
		last_sequence=existing.client_sequence if existing else None,
		last_payload_hash=existing.response_hash if existing else None,
		incoming_sequence=sequence,
		incoming_payload_hash=payload_hash,
	)
	if decision not in {"Accepted", "Accepted With Gap"}:
		return {"question_key": question_key, "decision": decision}

	if existing:
		answer = frappe.get_doc("EduEdge CBT Attempt Answer", existing.name)
	else:
		answer = frappe.get_doc(
			{
				"doctype": "EduEdge CBT Attempt Answer",
				"attempt": attempt.name,
				"exam": attempt.exam,
				"student": attempt.student,
				"school_branch": attempt.school_branch,
				"question_key": question_key,
				"source_question": snapshot.source_question,
			}
		)
	answer.response_json = json.dumps(response, sort_keys=True, ensure_ascii=False)
	answer.client_sequence = sequence
	answer.client_saved_on = client_saved_on
	answer.server_received_on = now
	answer.response_hash = payload_hash
	answer.sync_status = decision
	answer.is_final = bool(item.get("is_final"))
	answer.late_sync = late_sync
	answer.remarks = _("Accepted during audited pending-sync grace.") if late_sync else ""
	answer.flags.from_cbt_service = True
	if answer.is_new():
		answer.insert()
	else:
		answer.save()
	return {"question_key": question_key, "decision": decision, "answer": answer.name}


def _score_attempt(attempt) -> None:
	answers = {
		row.question_key: row
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt.name},
			fields=["question_key", "response_json", "is_answered"],
			page_length=2000,
		)
	}
	score = 0.0
	answered = 0
	for snapshot in attempt.question_snapshot:
		answer = answers.get(snapshot.snapshot_key)
		if not answer or not answer.is_answered:
			continue
		answered += 1
		response = frappe.parse_json(answer.response_json) if answer.response_json else None
		answer_key = frappe.parse_json(snapshot.answer_key_json)
		if score_objective_response(snapshot.question_type, answer_key, response):
			score += flt(snapshot.marks)
	attempt.answered_count = answered
	attempt.score = score
	total_marks = sum(flt(row.marks) for row in attempt.question_snapshot)
	attempt.percentage = (score / total_marks * 100) if total_marks else 0


def _submission_hash(attempt) -> str:
	answers = frappe.get_all(
		"EduEdge CBT Attempt Answer",
		filters={"attempt": attempt.name},
		fields=["question_key", "response_hash", "client_sequence", "is_final"],
		order_by="question_key asc",
		page_length=2000,
	)
	return stable_hash(
		{
			"attempt": attempt.name,
			"exam": attempt.exam,
			"student": attempt.student,
			"started_on": str(attempt.started_on),
			"server_deadline": str(attempt.server_deadline),
			"submitted_on": str(attempt.submitted_on),
			"answers": [dict(row) for row in answers],
		}
	)


def _refresh_timeout_state(attempt, *, preserve_pending: bool = False) -> None:
	if attempt.status not in ACTIVE_ATTEMPT_STATUSES:
		return
	now = now_datetime()
	if now <= get_datetime(attempt.server_deadline):
		return
	if preserve_pending or cint(attempt.pending_answer_count) or now <= get_datetime(attempt.sync_grace_ends_on):
		attempt.status = "Pending Sync"
		attempt.flags.from_cbt_service = True
		attempt.save()
		return
	_mark_attempt_timed_out(attempt)


def _mark_attempt_timed_out(attempt) -> None:
	attempt.status = "Timed Out"
	attempt.submitted_on = attempt.submitted_on or now_datetime()
	attempt.pending_answer_count = 0
	_score_attempt(attempt)
	attempt.result_status = "Provisional"
	attempt.submission_hash = _submission_hash(attempt)
	attempt.flags.from_cbt_service = True
	attempt.save()


def _exam_summary(exam) -> dict:
	return {
		"name": exam.name,
		"title": exam.title,
		"school_branch": exam.school_branch,
		"student_group": exam.student_group,
		"course": exam.course,
		"academic_year": exam.academic_year,
		"academic_term": exam.academic_term,
		"status": exam.status,
		"start_datetime": exam.start_datetime,
		"end_datetime": exam.end_datetime,
		"duration_minutes": cint(exam.duration_minutes),
		"sync_grace_minutes": cint(exam.sync_grace_minutes),
		"allow_resume": bool(exam.allow_resume),
		"auto_submit_on_timeout": bool(exam.auto_submit_on_timeout),
		"total_questions": cint(exam.total_questions),
		"total_marks": flt(exam.total_marks),
		"instructions": exam.instructions,
	}


def _attempt_payload(attempt, *, resumed: bool = False, include_result: bool = False) -> dict:
	answers = frappe.get_all(
		"EduEdge CBT Attempt Answer",
		filters={"attempt": attempt.name},
		fields=["question_key", "response_json", "client_sequence", "client_saved_on", "is_final"],
		page_length=2000,
	)
	payload = {
		"name": attempt.name,
		"exam": attempt.exam,
		"student": attempt.student,
		"status": attempt.status,
		"result_status": attempt.result_status,
		"attempt_no": cint(attempt.attempt_no),
		"resumed": resumed,
		"server_time": now_datetime(),
		"started_on": attempt.started_on,
		"server_deadline": attempt.server_deadline,
		"sync_grace_ends_on": attempt.sync_grace_ends_on,
		"last_sync_on": attempt.last_sync_on,
		"last_client_sequence": cint(attempt.last_client_sequence),
		"network_status": attempt.network_status,
		"pending_answer_count": cint(attempt.pending_answer_count),
		"answered_count": cint(attempt.answered_count),
		"total_questions": cint(attempt.total_questions),
		"tab_switch_count": cint(attempt.tab_switch_count),
		"focus_violation_count": cint(attempt.focus_violation_count),
		"questions": [
			{
				"question_key": row.snapshot_key,
				"sequence": cint(row.sequence),
				"question_type": row.question_type,
				"question_text": row.question_text,
				"options": frappe.parse_json(row.options_json) if row.options_json else [],
				"marks": flt(row.marks),
			}
			for row in attempt.question_snapshot
		],
		"answers": {
			row.question_key: {
				"response": frappe.parse_json(row.response_json) if row.response_json else None,
				"client_sequence": cint(row.client_sequence),
				"client_saved_on": row.client_saved_on,
				"is_final": bool(row.is_final),
			}
			for row in answers
		},
	}
	if include_result or attempt.result_status == "Approved":
		payload.update({"score": flt(attempt.score), "percentage": flt(attempt.percentage)})
	return payload
