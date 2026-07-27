from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt import attempts as base


def _parse_answers(answers) -> list[dict]:
	if isinstance(answers, str):
		answers = json.loads(answers)
	if not isinstance(answers, list):
		frappe.throw(_("Answers must be a list."), frappe.ValidationError)
	return answers


def _validate_timeout_payload(attempt, answers: list[dict], client_saved_at: str | None) -> None:
	deadline = get_datetime(attempt.expires_at)
	for row in answers:
		saved_at = row.get("client_saved_at") or client_saved_at
		if not saved_at or get_datetime(saved_at) > deadline:
			frappe.throw(
				_("Post-timeout sync accepts only answers saved before the server deadline."),
				frappe.ValidationError,
			)


@frappe.whitelist(allow_guest=True)
def get_attempt_state(
	attempt_name: str,
	launch_token: str,
	client_session_id: str | None = None,
) -> dict:
	attempt = base._load(attempt_name, launch_token)
	if client_session_id:
		base._session(attempt, client_session_id)
	if attempt.attempt_status == "Prepared":
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
	return base.get_attempt_state(attempt_name, launch_token, client_session_id)


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
	attempt = base._load(attempt_name, launch_token)
	base._session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0:
		base._finalize_timeout(attempt.name)
		attempt.reload()

	rows = _parse_answers(answers)
	timeout_reconciliation = (
		attempt.attempt_status in {"Pending Sync", "Auto Submitted"}
		and str(attempt.submission_source or "").startswith("Server Timeout")
	)
	if timeout_reconciliation:
		_validate_timeout_payload(attempt, rows, client_saved_at)

	original_status = attempt.attempt_status
	original_source = attempt.submission_source
	if original_status == "Auto Submitted" and timeout_reconciliation:
		frappe.db.set_value(
			"EduEdge CBT Attempt",
			attempt.name,
			"attempt_status",
			"Pending Sync",
			update_modified=False,
		)

	result = base.sync_answers(
		attempt_name,
		launch_token,
		client_session_id,
		idempotency_key,
		rows,
		client_saved_at,
		reported_pending_count,
	)
	if timeout_reconciliation and result.get("status") == "Applied":
		pending = max(0, cint(result.get("reported_pending_count")))
		updates = {
			"attempt_status": "Pending Sync" if pending else "Auto Submitted",
			"submission_source": original_source or "Server Timeout Auto-submit",
			"requires_review": 1,
			"review_reasons": base._review_reason(
				attempt.review_reasons,
				"Answers were reconciled after the server timeout.",
			),
		}
		frappe.db.set_value(
			"EduEdge CBT Attempt",
			attempt.name,
			updates,
			update_modified=False,
		)
		result["status"] = updates["attempt_status"]
	return result


@frappe.whitelist(allow_guest=True)
def submit_attempt(
	attempt_name: str,
	launch_token: str,
	client_session_id: str,
	reported_pending_count: int = 0,
) -> dict:
	base._lock("EduEdge CBT Attempt", attempt_name)
	attempt = base._load(attempt_name, launch_token)
	base._session(attempt, client_session_id)
	if attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0:
		base._finalize_timeout(attempt.name)
		attempt.reload()
		return {
			"attempt": attempt.name,
			"status": attempt.attempt_status,
			"reported_pending_count": cint(attempt.reported_pending_sync_count),
			"server_time": now_datetime(),
		}
	return base.submit_attempt(
		attempt_name,
		launch_token,
		client_session_id,
		reported_pending_count,
	)
