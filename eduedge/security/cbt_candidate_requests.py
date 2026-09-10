from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint


CANDIDATE_COMMANDS = {
	"eduedge.cbt.attempts.get_attempt_state": "state",
	"eduedge.cbt.attempts.start_attempt": "start",
	"eduedge.cbt.attempts.record_heartbeat": "heartbeat",
	"eduedge.cbt.attempts.sync_answers": "sync",
	"eduedge.cbt.attempts.submit_attempt": "submit",
	"eduedge.cbt.attempt_runtime_guard.get_attempt_state": "state",
	"eduedge.cbt.attempt_runtime_guard.sync_answers": "sync",
	"eduedge.cbt.attempt_runtime_guard.submit_attempt": "submit",
}

RATE_LIMITS = {
	"state": (60, 60),
	"start": (10, 60),
	"heartbeat": (30, 60),
	"sync": (90, 60),
	"submit": (10, 60),
}
MAX_ATTEMPT_NAME_LENGTH = 140
MAX_LAUNCH_TOKEN_LENGTH = 256
MAX_CLIENT_SESSION_ID_LENGTH = 128
MAX_IDEMPOTENCY_KEY_LENGTH = 128
MAX_ANSWER_ROWS = 500
MAX_ANSWER_PAYLOAD_BYTES = 256 * 1024
MAX_TEXT_ANSWER_LENGTH = 10_000
MAX_NUMERIC_ANSWER_LENGTH = 128
MAX_SELECTED_OPTION_IDS = 50
MAX_PENDING_COUNT = 10_000
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


def is_candidate_command(command: str) -> bool:
	return command in CANDIDATE_COMMANDS


def _request_ip() -> str:
	value = getattr(frappe.local, "request_ip", None)
	if value:
		return str(value)
	request = getattr(frappe.local, "request", None)
	return str(getattr(request, "remote_addr", "") or "unknown")


def _validation_error(message: str) -> None:
	frappe.throw(_(message), frappe.ValidationError)


def _bounded_identifier(
	value: Any,
	label: str,
	*,
	maximum: int,
	minimum: int = 1,
	required: bool = True,
) -> str:
	text = str(value or "").strip()
	if not text:
		if required:
			_validation_error(f"{label} is required.")
		return ""
	if len(text) < minimum or len(text) > maximum or not SAFE_IDENTIFIER.fullmatch(text):
		_validation_error(f"{label} has an invalid format or length.")
	return text


def _parse_answers(value: Any) -> list[dict]:
	if isinstance(value, str):
		if len(value.encode("utf-8")) > MAX_ANSWER_PAYLOAD_BYTES:
			_validation_error("Answer sync payload is too large.")
		try:
			value = json.loads(value)
		except json.JSONDecodeError:
			_validation_error("Answers must contain valid JSON.")
	if not isinstance(value, list):
		_validation_error("Answers must be a list.")
	if len(value) > MAX_ANSWER_ROWS:
		_validation_error("Answer sync contains too many rows.")
	try:
		encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
	except (TypeError, ValueError):
		_validation_error("Answer sync payload contains unsupported values.")
	if len(encoded) > MAX_ANSWER_PAYLOAD_BYTES:
		_validation_error("Answer sync payload is too large.")

	for row in value:
		if not isinstance(row, dict):
			_validation_error("Every answer row must be an object.")
		_bounded_identifier(
			row.get("question_snapshot_key"),
			"Question Snapshot Key",
			maximum=MAX_ATTEMPT_NAME_LENGTH,
		)
		revision = cint(row.get("client_revision"))
		if revision < 1 or revision > 2_147_483_647:
			_validation_error("Client Revision is outside the allowed range.")
		client_saved_at = str(row.get("client_saved_at") or "")
		if len(client_saved_at) > 64:
			_validation_error("Client Saved At is too long.")
		answer = row.get("answer") or {}
		if not isinstance(answer, dict):
			_validation_error("Each answer must be an object.")
		selected = answer.get("selected_option_ids") or []
		if not isinstance(selected, list) or len(selected) > MAX_SELECTED_OPTION_IDS:
			_validation_error("Selected answer choices exceed the allowed limit.")
		for option_id in selected:
			_bounded_identifier(
				option_id,
				"Selected Option ID",
				maximum=MAX_ATTEMPT_NAME_LENGTH,
			)
		text = str(answer.get("text") or "")
		if len(text) > MAX_TEXT_ANSWER_LENGTH:
			_validation_error("Written answer exceeds the allowed length.")
		value_text = str(answer.get("value") or "")
		if len(value_text) > MAX_NUMERIC_ANSWER_LENGTH:
			_validation_error("Numeric answer exceeds the allowed length.")
	return value


def _rate_key(action: str, scope: str, identity: str, window_seconds: int) -> str:
	window = int(time.time()) // window_seconds
	digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
	return f"eduedge:cbt-candidate-rate:{action}:{scope}:{window}:{digest}"


def _increment_rate_limit(action: str, scope: str, identity: str, limit: int, window_seconds: int) -> None:
	cache = frappe.cache()
	key = _rate_key(action, scope, identity, window_seconds)
	current = cint(cache.get_value(key) or 0)
	if current >= limit:
		frappe.local.response["http_status_code"] = 429
		frappe.throw(
			_("Too many CBT requests. Please allow the current request to finish before retrying."),
			frappe.PermissionError,
			title=_("Request Limit Reached"),
		)
	cache.set_value(key, current + 1, expires_in_sec=window_seconds + 5)


def _enforce_rate_limit(action: str, attempt_name: str, launch_token: str) -> None:
	limit, window_seconds = RATE_LIMITS[action]
	ip = _request_ip()
	site = str(getattr(frappe.local, "site", "") or "")
	_increment_rate_limit(action, "ip", f"{site}|{ip}", limit * 2, window_seconds)
	_increment_rate_limit(
		action,
		"attempt",
		f"{site}|{ip}|{attempt_name}|{launch_token}",
		limit,
		window_seconds,
	)


def enforce_candidate_request(command: str, args: dict | None = None) -> None:
	"""Validate and throttle every public school-CBT request before dispatch."""
	action = CANDIDATE_COMMANDS.get(command)
	if not action:
		return
	args = args or {}
	attempt_name = _bounded_identifier(
		args.get("attempt_name"),
		"Attempt",
		maximum=MAX_ATTEMPT_NAME_LENGTH,
	)
	launch_token = _bounded_identifier(
		args.get("launch_token"),
		"Launch Token",
		maximum=MAX_LAUNCH_TOKEN_LENGTH,
	)
	client_session_required = action in {"start", "heartbeat", "sync", "submit"}
	_bounded_identifier(
		args.get("client_session_id"),
		"Client Session ID",
		maximum=MAX_CLIENT_SESSION_ID_LENGTH,
		required=client_session_required,
	)
	if action == "sync":
		_bounded_identifier(
			args.get("idempotency_key"),
			"Idempotency Key",
			minimum=8,
			maximum=MAX_IDEMPOTENCY_KEY_LENGTH,
		)
		_parse_answers(args.get("answers"))
		pending = cint(args.get("reported_pending_count"))
		if pending < 0 or pending > MAX_PENDING_COUNT:
			_validation_error("Reported Pending Count is outside the allowed range.")
	if action == "heartbeat":
		pending = cint(args.get("pending_sync_count"))
		if pending < 0 or pending > MAX_PENDING_COUNT:
			_validation_error("Pending Sync Count is outside the allowed range.")
	_enforce_rate_limit(action, attempt_name, launch_token)
