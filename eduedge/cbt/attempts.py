from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import hashlib
import hmac
import json
import random
import secrets

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

SCHOOL_EXAM = "School Examination"
OBJECTIVE_TYPES = {"Single Choice", "Multiple Choice", "True/False", "Yes/No"}
SINGLE_OPTION_TYPES = {"Single Choice", "True/False", "Yes/No"}
ACTIVE_STATUSES = {"Prepared", "In Progress", "Pending Sync"}
ADMIN_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


@contextmanager
def _flag(name: str):
	previous = getattr(frappe.flags, name, False)
	setattr(frappe.flags, name, True)
	try:
		yield
	finally:
		setattr(frappe.flags, name, previous)


def _canonical(value) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value) -> str:
	if not isinstance(value, str):
		value = _canonical(value)
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _lock(doctype: str, name: str) -> None:
	frappe.db.sql(f"select name from `tab{doctype}` where name=%s for update", (name,))


def _label(position: int) -> str:
	return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[position - 1] if position <= 26 else f"A{position}"


def _review_reason(existing: str | None, reason: str) -> str:
	rows = [row.strip() for row in str(existing or "").splitlines() if row.strip()]
	if reason not in rows:
		rows.append(reason)
	return "\n".join(rows)


def _assert_manager(assignment) -> None:
	if frappe.session.user == "Guest" or not frappe.has_permission(
		"EduEdge CBT Candidate Assignment", ptype="write", doc=assignment
	):
		frappe.throw(_("You are not permitted to prepare this CBT attempt."), frappe.PermissionError)


def _build_snapshots(template, seed: str):
	rows = sorted(template.questions, key=lambda row: (cint(row.display_order) or cint(row.idx), cint(row.idx)))
	if cint(template.randomise_questions):
		random.Random(seed).shuffle(rows)
	visible, keys, total = [], [], 0.0
	for position, template_row in enumerate(rows, start=1):
		question = frappe.get_doc("EduEdge CBT Question", template_row.question)
		if question.status not in {"Approved", "Retired"}:
			frappe.throw(_("A template question is no longer approved."), frappe.ValidationError)
		snapshot_key = _hash(f"{seed}|{question.name}|{position}")[:24]
		options = sorted(question.options, key=lambda row: (cint(row.display_order) or cint(row.idx), cint(row.idx)))
		if cint(template.randomise_options) and question.question_type in OBJECTIVE_TYPES:
			random.Random(f"{seed}|{question.name}").shuffle(options)
		candidate_options, correct_ids = [], []
		for option_position, option in enumerate(options, start=1):
			option_id = _hash(
				f"{seed}|{question.name}|{option.option_key or option.idx}|{option_position}"
			)[:24]
			candidate_options.append(
				{"id": option_id, "label": _label(option_position), "text": option.option_text}
			)
			if cint(option.is_correct):
				correct_ids.append(option_id)
		mark = flt(template_row.mark)
		negative_mark = 0.0 if template.marking_policy == "Disable Negative Marking" else flt(template_row.negative_mark)
		total += mark
		visible.append(
			{
				"snapshot_key": snapshot_key,
				"display_order": position,
				"section_label": template_row.section_label,
				"source_question": question.name,
				"question_code": question.question_code,
				"question_type": question.question_type,
				"topic": question.topic,
				"question_text": question.question_text,
				"options_json": _canonical(candidate_options),
				"mark": mark,
				"negative_mark": negative_mark,
			}
		)
		keys.append(
			{
				"question_snapshot_key": snapshot_key,
				"question_type": question.question_type,
				"correct_option_ids_json": _canonical(correct_ids),
				"answer_key": question.answer_key,
				"marking_guide": question.marking_guide,
				"mark": mark,
				"negative_mark": negative_mark,
			}
		)
	return visible, keys, total


@frappe.whitelist()
def prepare_attempt(candidate_assignment: str) -> dict:
	assignment = frappe.get_doc("EduEdge CBT Candidate Assignment", candidate_assignment)
	_assert_manager(assignment)
	if assignment.exam_scope != SCHOOL_EXAM:
		frappe.throw(
			_(
				"Public examinations require the central signed-launch service. "
				"Protected public questions and keys are not copied into tenant sites."
			),
			frappe.PermissionError,
		)
	if assignment.assignment_status != "Released":
		frappe.throw(_("Candidate must be Released before attempt preparation."), frappe.ValidationError)
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", assignment.exam_schedule)
	template = frappe.get_doc("EduEdge CBT Exam Template", assignment.exam_template)
	if schedule.status != "Active" or template.status != "Approved":
		frappe.throw(_("The schedule must be Active and the template Approved."), frappe.ValidationError)
	_lock("EduEdge CBT Candidate Assignment", assignment.name)
	if frappe.db.exists(
		"EduEdge CBT Attempt",
		{"candidate_assignment": assignment.name, "attempt_status": ["in", sorted(ACTIVE_STATUSES)]},
	):
		frappe.throw(_("Candidate already has an active attempt."), frappe.DuplicateEntryError)
	attempt_count = frappe.db.count(
		"EduEdge CBT Attempt",
		{"candidate_assignment": assignment.name, "attempt_status": ["!=", "Cancelled"]},
	)
	if attempt_count >= cint(template.maximum_attempts):
		frappe.throw(_("Maximum Attempts has been reached."), frappe.ValidationError)
	token, seed = secrets.token_urlsafe(32), secrets.token_hex(16)
	questions, scoring_keys, total_marks = _build_snapshots(template, seed)
	if not questions:
		frappe.throw(_("Approved template has no questions."), frappe.ValidationError)
	attempt = frappe.get_doc(
		{
			"doctype": "EduEdge CBT Attempt",
			"candidate_assignment": assignment.name,
			"attempt_number": attempt_count + 1,
			"exam_schedule": assignment.exam_schedule,
			"exam_template": assignment.exam_template,
			"exam_scope": assignment.exam_scope,
			"school_branch": assignment.school_branch,
			"course": assignment.course,
			"candidate_type": assignment.candidate_type,
			"student": assignment.student,
			"candidate_name": assignment.candidate_name,
			"attempt_status": "Prepared",
			"prepared_at": now_datetime(),
			"launch_token_hash": _hash(token),
			"launch_token_expires_at": assignment.access_end,
			"randomisation_seed": seed,
			"duration_minutes": cint(template.duration_minutes),
			"approved_extra_time_minutes": cint(assignment.approved_extra_time_minutes),
			"maximum_attempts": cint(template.maximum_attempts),
			"navigation_policy": template.navigation_policy,
			"auto_submit_on_timeout": cint(template.auto_submit_on_timeout),
			"allow_resume": cint(template.allow_resume),
			"randomise_questions": cint(template.randomise_questions),
			"randomise_options": cint(template.randomise_options),
			"marking_policy": template.marking_policy,
			"result_release_policy": template.result_release_policy,
			"device_change_policy": template.device_change_policy,
			"attempt_review_policy": template.attempt_review_policy,
			"questions": questions,
			"question_count": len(questions),
			"total_marks": total_marks,
			"requires_review": 1 if template.attempt_review_policy == "Review All Attempts" else 0,
			"review_reasons": "Template requires review of all attempts."
			if template.attempt_review_policy == "Review All Attempts"
			else "",
		}
	)
	with _flag("in_cbt_attempt_service"):
		attempt.insert(ignore_permissions=True)
	for values in scoring_keys:
		with _flag("in_cbt_attempt_service"):
			frappe.get_doc(
				{"doctype": "EduEdge CBT Attempt Scoring Key", "attempt": attempt.name, **values}
			).insert(ignore_permissions=True)
	return {
		"attempt": attempt.name,
		"attempt_number": attempt.attempt_number,
		"launch_token": token,
		"launch_token_expires_at": attempt.launch_token_expires_at,
		"question_count": attempt.question_count,
		"server_time": now_datetime(),
	}


def _load(attempt_name: str, token: str):
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if not token or not hmac.compare_digest(attempt.launch_token_hash or "", _hash(token)):
		frappe.throw(_("Invalid CBT launch token."), frappe.PermissionError)
	if attempt.launch_token_expires_at and now_datetime() > get_datetime(attempt.launch_token_expires_at):
		frappe.throw(_("CBT launch token has expired."), frappe.PermissionError)
	if attempt.exam_scope != SCHOOL_EXAM:
		frappe.throw(_("Public attempts use the central launch service."), frappe.PermissionError)
	return attempt


def _device_approved(attempt, client_session_id: str) -> bool:
	log = frappe.db.get_value(
		"EduEdge CBT Intervention Log",
		{
			"candidate_assignment": attempt.candidate_assignment,
			"attempt_reference": attempt.name,
			"intervention_type": "Device Change",
			"outcome": "Applied",
			"new_value": client_session_id,
		},
		["acted_by"],
		order_by="acted_on desc",
		as_dict=True,
	)
	if not log:
		return False
	if attempt.device_change_policy == "Administrator Approval Required":
		return bool(set(frappe.get_roles(log.acted_by)).intersection(ADMIN_ROLES))
	return True


def _session(attempt, client_session_id: str) -> None:
	client_session_id = str(client_session_id or "").strip()
	if not client_session_id:
		frappe.throw(_("Client Session ID is required."), frappe.ValidationError)
	if not attempt.client_session_id:
		frappe.db.set_value(
			"EduEdge CBT Attempt", attempt.name, "client_session_id", client_session_id, update_modified=False
		)
		attempt.client_session_id = client_session_id
		return
	if attempt.client_session_id == client_session_id:
		return
	if attempt.device_change_policy == "Not Allowed":
		frappe.throw(_("Device change is not allowed."), frappe.PermissionError)
	if attempt.device_change_policy == "Allowed Before First Answer Only" and not cint(attempt.answered_count):
		frappe.db.set_value(
			"EduEdge CBT Attempt", attempt.name, "client_session_id", client_session_id, update_modified=False
		)
		attempt.client_session_id = client_session_id
		return
	if not _device_approved(attempt, client_session_id):
		frappe.throw(_("Approved Device Change intervention is required."), frappe.PermissionError)
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		{
			"client_session_id": client_session_id,
			"requires_review": 1,
			"review_reasons": _review_reason(attempt.review_reasons, "Approved device change."),
		},
		update_modified=False,
	)
	attempt.client_session_id = client_session_id


def _remaining(attempt) -> int:
	if not attempt.expires_at:
		return 0
	return max(0, int((get_datetime(attempt.expires_at) - now_datetime()).total_seconds()))


@frappe.whitelist(allow_guest=True)
def start_attempt(attempt_name: str, launch_token: str, client_session_id: str) -> dict:
	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load(attempt_name, launch_token)
	_session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress":
		if not cint(attempt.allow_resume):
			frappe.throw(_("Resume is disabled."), frappe.PermissionError)
		return get_attempt_state(attempt_name, launch_token, client_session_id)
	if attempt.attempt_status != "Prepared":
		frappe.throw(_("Attempt cannot be started from its current status."), frappe.ValidationError)
	assignment = frappe.get_doc("EduEdge CBT Candidate Assignment", attempt.candidate_assignment)
	if assignment.assignment_status != "Released":
		frappe.throw(_("Candidate is not Released."), frappe.PermissionError)
	current = now_datetime()
	if current < get_datetime(assignment.access_start) or current > get_datetime(assignment.access_end):
		frappe.throw(_("Candidate is outside the examination access window."), frappe.PermissionError)
	expires_at = min(
		current + timedelta(minutes=cint(attempt.duration_minutes) + cint(attempt.approved_extra_time_minutes)),
		get_datetime(assignment.access_end),
	)
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		{"attempt_status": "In Progress", "started_at": current, "expires_at": expires_at, "last_heartbeat_at": current},
		update_modified=False,
	)
	return get_attempt_state(attempt_name, launch_token, client_session_id)


def _questions(attempt) -> list[dict]:
	return [
		{
			"snapshot_key": row.snapshot_key,
			"display_order": cint(row.display_order),
			"section_label": row.section_label,
			"question_code": row.question_code,
			"question_type": row.question_type,
			"topic": row.topic,
			"question_text": row.question_text,
			"options": json.loads(row.options_json or "[]"),
			"mark": flt(row.mark),
		}
		for row in sorted(attempt.questions, key=lambda row: (cint(row.display_order), cint(row.idx)))
	]


def _answers(attempt_name: str) -> dict:
	return {
		row.question_snapshot_key: {
			"answer": json.loads(row.answer_payload_json or "{}"),
			"client_revision": cint(row.client_revision),
			"server_revision": cint(row.server_revision),
			"client_saved_at": row.client_saved_at,
			"server_saved_at": row.server_saved_at,
		}
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt_name},
			fields=[
				"question_snapshot_key",
				"answer_payload_json",
				"client_revision",
				"server_revision",
				"client_saved_at",
				"server_saved_at",
			],
		)
	}


@frappe.whitelist(allow_guest=True)
def get_attempt_state(attempt_name: str, launch_token: str, client_session_id: str | None = None) -> dict:
	attempt = _load(attempt_name, launch_token)
	if client_session_id:
		_session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and _remaining(attempt) <= 0:
		_finalize_timeout(attempt.name)
		attempt.reload()
	return {
		"attempt": attempt.name,
		"candidate_name": attempt.candidate_name,
		"status": attempt.attempt_status,
		"server_time": now_datetime(),
		"started_at": attempt.started_at,
		"expires_at": attempt.expires_at,
		"seconds_remaining": _remaining(attempt),
		"navigation_policy": attempt.navigation_policy,
		"questions": _questions(attempt),
		"answers": _answers(attempt.name),
		"reported_pending_sync_count": cint(attempt.reported_pending_sync_count),
		"last_sync_at": attempt.last_sync_at,
	}


def _normalise(question, payload) -> dict:
	if not isinstance(payload, dict):
		frappe.throw(_("Answer payload must be an object."), frappe.ValidationError)
	if question["type"] in OBJECTIVE_TYPES:
		selected = payload.get("selected_option_ids") or []
		if not isinstance(selected, list):
			frappe.throw(_("Selected option IDs must be a list."), frappe.ValidationError)
		selected = sorted(set(str(value).strip() for value in selected if str(value).strip()))
		if question["type"] in SINGLE_OPTION_TYPES and len(selected) > 1:
			frappe.throw(_("Question accepts one option only."), frappe.ValidationError)
		if any(value not in question["option_ids"] for value in selected):
			frappe.throw(_("Answer contains an invalid option."), frappe.ValidationError)
		return {"selected_option_ids": selected}
	if question["type"] in {"Short Answer", "Essay"}:
		return {"text": str(payload.get("text") or "")}
	if question["type"] == "Numeric":
		value = payload.get("value")
		if value in (None, ""):
			return {"value": ""}
		try:
			float(value)
		except (TypeError, ValueError):
			frappe.throw(_("Numeric answer is invalid."), frappe.ValidationError)
		return {"value": str(value)}
	frappe.throw(_("Unsupported question type."), frappe.ValidationError)


def _answered(payload: dict) -> bool:
	return bool(
		payload.get("selected_option_ids")
		or str(payload.get("text") or "").strip()
		or payload.get("value") not in ("", None)
	)


def _sync_log(values: dict) -> None:
	with _flag("in_cbt_answer_sync"):
		frappe.get_doc({"doctype": "EduEdge CBT Sync Log", **values}).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def sync_answers(
	attempt_name: str,
	launch_token: str,
	client_session_id: str,
	idempotency_key: str,
	answers,
	client_saved_at: str | None = None,
	reported_pending_count: int = 0,
) -> dict:
	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load(attempt_name, launch_token)
	_session(attempt, client_session_id)
	if attempt.attempt_status not in {"In Progress", "Pending Sync"}:
		frappe.throw(_("Answers cannot be synced for this status."), frappe.ValidationError)
	if isinstance(answers, str):
		answers = json.loads(answers)
	if not isinstance(answers, list):
		frappe.throw(_("Answers must be a list."), frappe.ValidationError)
	idempotency_key = str(idempotency_key or "").strip()
	if not idempotency_key:
		frappe.throw(_("Idempotency Key is required."), frappe.ValidationError)
	qmap = {
		row.snapshot_key: {
			"type": row.question_type,
			"option_ids": {item["id"] for item in json.loads(row.options_json or "[]")},
		}
		for row in attempt.questions
	}
	normalised, seen = [], set()
	for row in answers:
		key = str(row.get("question_snapshot_key") or "").strip()
		if key not in qmap or key in seen:
			frappe.throw(_("Answer has an invalid or repeated question key."), frappe.ValidationError)
		seen.add(key)
		revision = cint(row.get("client_revision"))
		if revision < 1:
			frappe.throw(_("Client Revision must be at least 1."), frappe.ValidationError)
		payload = _normalise(qmap[key], row.get("answer") or {})
		normalised.append(
			{
				"key": key,
				"revision": revision,
				"payload": payload,
				"hash": _hash(payload),
				"client_saved_at": row.get("client_saved_at") or client_saved_at,
			}
		)
	request_hash = _hash(
		{"answers": normalised, "reported_pending_count": max(0, cint(reported_pending_count))}
	)
	existing_log = frappe.db.get_value(
		"EduEdge CBT Sync Log",
		{"attempt": attempt.name, "idempotency_key": idempotency_key},
		["payload_hash", "answer_count", "applied_count", "duplicate_count", "reported_pending_count", "sync_status"],
		as_dict=True,
	)
	if existing_log:
		if existing_log.payload_hash != request_hash:
			frappe.throw(_("Idempotency Key was reused with different content."), frappe.DuplicateEntryError)
		return {
			"attempt": attempt.name,
			"idempotent_replay": True,
			"status": existing_log.sync_status,
			"answer_count": cint(existing_log.answer_count),
			"applied_count": cint(existing_log.applied_count),
			"duplicate_count": cint(existing_log.duplicate_count),
			"reported_pending_count": cint(existing_log.reported_pending_count),
			"server_time": now_datetime(),
		}
	existing = {
		row.question_snapshot_key: row
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt.name},
			fields=["name", "question_snapshot_key", "client_revision", "server_revision", "payload_hash"],
		)
	}
	for row in normalised:
		old = existing.get(row["key"])
		if old and cint(old.client_revision) == row["revision"] and old.payload_hash != row["hash"]:
			_sync_log(
				{
					"attempt": attempt.name,
					"client_session_id": client_session_id,
					"idempotency_key": idempotency_key,
					"payload_hash": request_hash,
					"server_received_at": now_datetime(),
					"answer_count": len(normalised),
					"reported_pending_count": max(0, cint(reported_pending_count)),
					"sync_status": "Conflict",
					"error_details": "Client revision reused with different content.",
				}
			)
			return {"attempt": attempt.name, "status": "Conflict", "conflict_question": row["key"]}
	applied = duplicates = 0
	server_time = now_datetime()
	for row in normalised:
		old = existing.get(row["key"])
		if old and cint(old.client_revision) >= row["revision"]:
			duplicates += 1
			continue
		if old:
			answer = frappe.get_doc("EduEdge CBT Attempt Answer", old.name)
			answer.answer_payload_json = _canonical(row["payload"])
			answer.client_revision = row["revision"]
			answer.server_revision = cint(answer.server_revision) + 1
			answer.client_saved_at = row["client_saved_at"]
			answer.server_saved_at = server_time
			answer.payload_hash = row["hash"]
			with _flag("in_cbt_answer_sync"):
				answer.save(ignore_permissions=True)
		else:
			with _flag("in_cbt_answer_sync"):
				frappe.get_doc(
					{
						"doctype": "EduEdge CBT Attempt Answer",
						"attempt": attempt.name,
						"question_snapshot_key": row["key"],
						"answer_payload_json": _canonical(row["payload"]),
						"client_revision": row["revision"],
						"server_revision": 1,
						"client_saved_at": row["client_saved_at"],
						"server_saved_at": server_time,
						"payload_hash": row["hash"],
					}
				).insert(ignore_permissions=True)
		applied += 1
	answered_count = sum(
		1
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt.name},
			fields=["answer_payload_json"],
		)
		if _answered(json.loads(row.answer_payload_json or "{}"))
	)
	pending = max(0, cint(reported_pending_count))
	updates = {
		"last_sync_at": server_time,
		"last_heartbeat_at": server_time,
		"reported_pending_sync_count": pending,
		"answered_count": answered_count,
	}
	if attempt.attempt_status == "Pending Sync" and not pending:
		updates.update({"attempt_status": "Submitted", "submission_source": "Pending Sync Resolved"})
	frappe.db.set_value("EduEdge CBT Attempt", attempt.name, updates, update_modified=False)
	_sync_log(
		{
			"attempt": attempt.name,
			"client_session_id": client_session_id,
			"idempotency_key": idempotency_key,
			"payload_hash": request_hash,
			"client_saved_at": client_saved_at,
			"server_received_at": server_time,
			"answer_count": len(normalised),
			"applied_count": applied,
			"duplicate_count": duplicates,
			"reported_pending_count": pending,
			"sync_status": "Applied",
		}
	)
	return {
		"attempt": attempt.name,
		"status": "Applied",
		"applied_count": applied,
		"duplicate_count": duplicates,
		"answered_count": answered_count,
		"reported_pending_count": pending,
		"server_time": server_time,
	}


@frappe.whitelist(allow_guest=True)
def record_heartbeat(
	attempt_name: str,
	launch_token: str,
	client_session_id: str,
	reported_pending_count: int = 0,
) -> dict:
	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load(attempt_name, launch_token)
	_session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and _remaining(attempt) <= 0:
		_finalize_timeout(attempt.name)
		attempt.reload()
	current = now_datetime()
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		{"last_heartbeat_at": current, "reported_pending_sync_count": max(0, cint(reported_pending_count))},
		update_modified=False,
	)
	return {"attempt": attempt.name, "status": attempt.attempt_status, "server_time": current, "seconds_remaining": _remaining(attempt)}


@frappe.whitelist(allow_guest=True)
def submit_attempt(
	attempt_name: str,
	launch_token: str,
	client_session_id: str,
	reported_pending_count: int = 0,
) -> dict:
	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load(attempt_name, launch_token)
	_session(attempt, client_session_id)
	if attempt.attempt_status in {"Submitted", "Auto Submitted", "Pending Sync"}:
		return {"attempt": attempt.name, "status": attempt.attempt_status, "server_time": now_datetime()}
	if attempt.attempt_status != "In Progress":
		frappe.throw(_("Attempt cannot be submitted from its current status."), frappe.ValidationError)
	pending = max(0, cint(reported_pending_count))
	status = "Pending Sync" if pending else "Submitted"
	reasons = attempt.review_reasons
	if pending:
		reasons = _review_reason(reasons, "Attempt submitted with pending browser answers.")
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		{
			"attempt_status": status,
			"submitted_at": now_datetime(),
			"submission_source": "Candidate Submission",
			"reported_pending_sync_count": pending,
			"requires_review": 1 if pending else cint(attempt.requires_review),
			"review_reasons": reasons,
		},
		update_modified=False,
	)
	return {"attempt": attempt.name, "status": status, "reported_pending_count": pending, "server_time": now_datetime()}


def _finalize_timeout(attempt_name: str) -> None:
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if attempt.attempt_status != "In Progress":
		return
	pending = cint(attempt.reported_pending_sync_count)
	if cint(attempt.auto_submit_on_timeout):
		status = "Pending Sync" if pending else "Auto Submitted"
		source = "Server Timeout Auto-submit"
	else:
		status, source = "Timed Out", "Server Timeout"
	reasons = attempt.review_reasons
	if status == "Pending Sync":
		reasons = _review_reason(reasons, "Timeout reached with pending browser answers.")
	if status == "Timed Out":
		reasons = _review_reason(reasons, "Attempt timed out without automatic submission.")
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		{
			"attempt_status": status,
			"submitted_at": now_datetime() if status != "Timed Out" else None,
			"submission_source": source,
			"requires_review": 1 if status in {"Pending Sync", "Timed Out"} else cint(attempt.requires_review),
			"review_reasons": reasons,
		},
		update_modified=False,
	)


def finalize_expired_attempts() -> None:
	for row in frappe.get_all(
		"EduEdge CBT Attempt",
		filters={"attempt_status": "In Progress", "expires_at": ["<=", now_datetime()]},
		fields=["name"],
		limit_page_length=500,
	):
		_finalize_timeout(row.name)
