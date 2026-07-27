from __future__ import annotations

from datetime import timedelta
import hmac
import json

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt import attempts as base

SYNC_RECONCILIATION_HOURS = 24
RECONCILIATION_STATUSES = {"In Progress", "Pending Sync", "Auto Submitted", "Timed Out"}


def _parse_answers(answers) -> list[dict]:
	if isinstance(answers, str):
		answers = json.loads(answers)
	if not isinstance(answers, list):
		frappe.throw(_("Answers must be a list."), frappe.ValidationError)
	return answers


def _token_valid(attempt, launch_token: str) -> bool:
	return bool(
		launch_token
		and hmac.compare_digest(
			attempt.launch_token_hash or "",
			base._hash(launch_token),
		)
	)


def _reconciliation_deadline(attempt):
	anchor = attempt.expires_at or attempt.launch_token_expires_at
	if not anchor:
		return None
	return get_datetime(anchor) + timedelta(hours=SYNC_RECONCILIATION_HOURS)


def _load_candidate_attempt(
	attempt_name: str,
	launch_token: str,
	*,
	allow_reconciliation: bool = False,
):
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if not _token_valid(attempt, launch_token):
		frappe.throw(_("Invalid CBT launch token."), frappe.PermissionError)
	if attempt.exam_scope != base.SCHOOL_EXAM:
		frappe.throw(_("Public attempts use the central launch service."), frappe.PermissionError)

	expires_at = get_datetime(attempt.launch_token_expires_at) if attempt.launch_token_expires_at else None
	if expires_at and now_datetime() > expires_at:
		deadline = _reconciliation_deadline(attempt)
		allowed = (
			allow_reconciliation
			and attempt.attempt_status in RECONCILIATION_STATUSES
			and deadline
			and now_datetime() <= deadline
		)
		if not allowed:
			frappe.throw(_("CBT launch token has expired."), frappe.PermissionError)
	return attempt


def _reconciliation_cutoff(attempt):
	if str(attempt.submission_source or "").startswith("Server Timeout"):
		return get_datetime(attempt.expires_at) if attempt.expires_at else None
	if attempt.submitted_at:
		return get_datetime(attempt.submitted_at)
	return get_datetime(attempt.expires_at) if attempt.expires_at else None


def _validate_reconciliation_payload(
	attempt,
	answers: list[dict],
	client_saved_at: str | None,
) -> None:
	cutoff = _reconciliation_cutoff(attempt)
	if not cutoff:
		frappe.throw(_("The attempt has no valid reconciliation cutoff."), frappe.ValidationError)
	for row in answers:
		saved_at = row.get("client_saved_at") or client_saved_at
		if not saved_at or get_datetime(saved_at) > cutoff:
			frappe.throw(
				_("Post-submission sync accepts only answers saved before the server cutoff."),
				frappe.ValidationError,
			)


def _prepared_state(attempt) -> dict:
	return {
		"attempt": attempt.name,
		"candidate_name": attempt.candidate_name,
		"status": "Prepared",
		"server_time": now_datetime(),
		"started_at": None,
		"expires_at": None,
		"seconds_remaining": 0,
		"navigation_policy": attempt.navigation_policy,
		"questions": [],
		"answers": {},
		"reported_pending_sync_count": 0,
		"last_sync_at": None,
	}


def _candidate_state(attempt) -> dict:
	show_questions = attempt.attempt_status == "In Progress"
	return {
		"attempt": attempt.name,
		"candidate_name": attempt.candidate_name,
		"status": attempt.attempt_status,
		"server_time": now_datetime(),
		"started_at": attempt.started_at,
		"expires_at": attempt.expires_at,
		"seconds_remaining": base._remaining(attempt),
		"navigation_policy": attempt.navigation_policy,
		"questions": base._questions(attempt) if show_questions else [],
		"answers": base._answers(attempt.name),
		"reported_pending_sync_count": cint(attempt.reported_pending_sync_count),
		"last_sync_at": attempt.last_sync_at,
		"reconciliation_deadline": _reconciliation_deadline(attempt),
	}


@frappe.whitelist(allow_guest=True)
def get_attempt_state(
	attempt_name: str,
	launch_token: str,
	client_session_id: str | None = None,
) -> dict:
	attempt = _load_candidate_attempt(
		attempt_name,
		launch_token,
		allow_reconciliation=True,
	)
	if client_session_id:
		base._session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0:
		base._finalize_timeout(attempt.name)
		attempt.reload()
	if attempt.attempt_status == "Prepared":
		return _prepared_state(attempt)
	return _candidate_state(attempt)


def _normalise_rows(attempt, answers: list[dict]) -> list[dict]:
	question_map = {
		row.snapshot_key: {
			"type": row.question_type,
			"option_ids": {item["id"] for item in json.loads(row.options_json or "[]")},
		}
		for row in attempt.questions
	}
	normalised = []
	seen = set()
	for row in answers:
		key = str(row.get("question_snapshot_key") or "").strip()
		if key not in question_map or key in seen:
			frappe.throw(_("Answer has an invalid or repeated question key."), frappe.ValidationError)
		seen.add(key)
		revision = cint(row.get("client_revision"))
		if revision < 1:
			frappe.throw(_("Client Revision must be at least 1."), frappe.ValidationError)
		payload = base._normalise(question_map[key], row.get("answer") or {})
		normalised.append(
			{
				"key": key,
				"revision": revision,
				"payload": payload,
				"hash": base._hash(payload),
				"client_saved_at": row.get("client_saved_at"),
			}
		)
	return normalised


def _existing_sync_log(attempt_name: str, idempotency_key: str):
	return frappe.db.get_value(
		"EduEdge CBT Sync Log",
		{"attempt": attempt_name, "idempotency_key": idempotency_key},
		[
			"payload_hash",
			"answer_count",
			"applied_count",
			"duplicate_count",
			"reported_pending_count",
			"sync_status",
		],
		as_dict=True,
	)


def _idempotent_response(attempt, existing_log) -> dict:
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


def _record_conflict(
	attempt,
	client_session_id: str,
	idempotency_key: str,
	request_hash: str,
	answer_count: int,
	reported_pending_count: int,
) -> None:
	base._sync_log(
		{
			"attempt": attempt.name,
			"client_session_id": client_session_id,
			"idempotency_key": idempotency_key,
			"payload_hash": request_hash,
			"server_received_at": now_datetime(),
			"answer_count": answer_count,
			"reported_pending_count": reported_pending_count,
			"sync_status": "Conflict",
			"error_details": "Client revision reused with different content.",
		}
	)


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
	base._lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load_candidate_attempt(
		attempt_name,
		launch_token,
		allow_reconciliation=True,
	)
	base._session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0:
		base._finalize_timeout(attempt.name)
		attempt.reload()

	rows = _parse_answers(answers)
	is_reconciliation = attempt.attempt_status in {"Pending Sync", "Auto Submitted", "Timed Out"}
	if attempt.attempt_status not in {"In Progress", "Pending Sync", "Auto Submitted", "Timed Out"}:
		frappe.throw(_("Answers cannot be synced for this status."), frappe.ValidationError)
	if is_reconciliation:
		_validate_reconciliation_payload(attempt, rows, client_saved_at)

	idempotency_key = str(idempotency_key or "").strip()
	if not idempotency_key:
		frappe.throw(_("Idempotency Key is required."), frappe.ValidationError)

	normalised = _normalise_rows(attempt, rows)
	for index, row in enumerate(normalised):
		row["client_saved_at"] = rows[index].get("client_saved_at") or client_saved_at
	pending = max(0, cint(reported_pending_count))
	request_hash = base._hash(
		{"answers": normalised, "reported_pending_count": pending}
	)
	existing_log = _existing_sync_log(attempt.name, idempotency_key)
	if existing_log:
		if existing_log.payload_hash != request_hash:
			frappe.throw(
				_("Idempotency Key was reused with different content."),
				frappe.DuplicateEntryError,
			)
		return _idempotent_response(attempt, existing_log)

	existing_answers = {
		row.question_snapshot_key: row
		for row in frappe.get_all(
			"EduEdge CBT Attempt Answer",
			filters={"attempt": attempt.name},
			fields=[
				"name",
				"question_snapshot_key",
				"client_revision",
				"server_revision",
				"payload_hash",
			],
		)
	}
	for row in normalised:
		old = existing_answers.get(row["key"])
		if old and cint(old.client_revision) == row["revision"] and old.payload_hash != row["hash"]:
			_record_conflict(
				attempt,
				client_session_id,
				idempotency_key,
				request_hash,
				len(normalised),
				pending,
			)
			return {
				"attempt": attempt.name,
				"status": "Conflict",
				"conflict_question": row["key"],
			}

	applied = 0
	duplicates = 0
	server_time = now_datetime()
	for row in normalised:
		old = existing_answers.get(row["key"])
		if old and cint(old.client_revision) >= row["revision"]:
			duplicates += 1
			continue
		if old:
			answer = frappe.get_doc("EduEdge CBT Attempt Answer", old.name)
			answer.answer_payload_json = base._canonical(row["payload"])
			answer.client_revision = row["revision"]
			answer.server_revision = cint(answer.server_revision) + 1
			answer.client_saved_at = row["client_saved_at"]
			answer.server_saved_at = server_time
			answer.payload_hash = row["hash"]
			with base._flag("in_cbt_answer_sync"):
				answer.save(ignore_permissions=True)
		else:
			with base._flag("in_cbt_answer_sync"):
				frappe.get_doc(
					{
						"doctype": "EduEdge CBT Attempt Answer",
						"attempt": attempt.name,
						"question_snapshot_key": row["key"],
						"answer_payload_json": base._canonical(row["payload"]),
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
		if base._answered(json.loads(row.answer_payload_json or "{}"))
	)
	updates = {
		"last_sync_at": server_time,
		"last_heartbeat_at": server_time,
		"reported_pending_sync_count": pending,
		"answered_count": answered_count,
	}
	if is_reconciliation:
		updates.update(
			{
				"requires_review": 1,
				"review_reasons": base._review_reason(
					attempt.review_reasons,
					"Answers were reconciled after submission or timeout.",
				),
			}
		)
		if attempt.attempt_status in {"Pending Sync", "Auto Submitted"}:
			if str(attempt.submission_source or "").startswith("Server Timeout"):
				updates["attempt_status"] = "Pending Sync" if pending else "Auto Submitted"
			else:
				updates["attempt_status"] = "Pending Sync" if pending else "Submitted"
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		updates,
		update_modified=False,
	)
	base._sync_log(
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
		"status": updates.get("attempt_status", "Applied"),
		"applied_count": applied,
		"duplicate_count": duplicates,
		"answered_count": answered_count,
		"reported_pending_count": pending,
		"server_time": server_time,
	}


@frappe.whitelist(allow_guest=True)
def submit_attempt(
	attempt_name: str,
	launch_token: str,
	client_session_id: str,
	reported_pending_count: int = 0,
) -> dict:
	base._lock("EduEdge CBT Attempt", attempt_name)
	attempt = _load_candidate_attempt(
		attempt_name,
		launch_token,
		allow_reconciliation=True,
	)
	base._session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0:
		base._finalize_timeout(attempt.name)
		attempt.reload()
	if attempt.attempt_status in {"Submitted", "Auto Submitted", "Pending Sync", "Timed Out"}:
		return {
			"attempt": attempt.name,
			"status": attempt.attempt_status,
			"reported_pending_count": cint(attempt.reported_pending_sync_count),
			"server_time": now_datetime(),
		}
	if attempt.attempt_status != "In Progress":
		frappe.throw(_("Attempt cannot be submitted from its current status."), frappe.ValidationError)

	pending = max(0, cint(reported_pending_count))
	status = "Pending Sync" if pending else "Submitted"
	reasons = attempt.review_reasons
	if pending:
		reasons = base._review_reason(
			reasons,
			"Attempt submitted with pending browser answers.",
		)
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
	return {
		"attempt": attempt.name,
		"status": status,
		"reported_pending_count": pending,
		"server_time": now_datetime(),
	}
