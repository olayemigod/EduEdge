from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

OBJECTIVE_QUESTION_TYPES = {"Single Choice", "Multiple Choice", "True/False"}
SYNC_DECISIONS = {"Accepted", "Accepted With Gap", "Duplicate", "Stale", "Conflict"}


def stable_hash(value: Any) -> str:
	"""Return a deterministic SHA-256 hash for JSON-compatible CBT payloads."""
	payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_response(value: Any) -> Any:
	"""Normalize answer payloads before hashing, comparison, and storage."""
	if value is None:
		return None
	if isinstance(value, str):
		return value.strip()
	if isinstance(value, list):
		return sorted({str(item).strip() for item in value if str(item).strip()})
	if isinstance(value, dict):
		return {
			str(key).strip(): canonical_response(item)
			for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
			if str(key).strip()
		}
	if isinstance(value, (bool, int, float)):
		return value
	return str(value).strip()


def validate_question_contract(question_type: str, options: list[dict] | None) -> list[dict]:
	"""Validate and normalize objective-question options.

	The function deliberately supports only objective question types in CBT V1.
	Subjective marking requires a separate moderated workflow and is out of scope.
	"""
	question_type = str(question_type or "").strip()
	if question_type not in OBJECTIVE_QUESTION_TYPES:
		raise ValueError(f"Unsupported CBT question type: {question_type or 'blank'}")

	rows = []
	seen_keys: set[str] = set()
	for index, row in enumerate(options or [], start=1):
		if not isinstance(row, dict):
			raise ValueError("Every CBT option must be an object.")
		key = str(row.get("option_key") or "").strip().upper()
		text = str(row.get("option_text") or "").strip()
		if not key:
			raise ValueError("Every CBT option requires an option key.")
		if key in seen_keys:
			raise ValueError(f"Duplicate CBT option key: {key}")
		if not text:
			raise ValueError(f"CBT option {key} requires option text.")
		seen_keys.add(key)
		rows.append(
			{
				"option_key": key,
				"option_text": text,
				"is_correct": bool(row.get("is_correct")),
				"display_order": int(row.get("display_order") or index),
			}
		)

	if len(rows) < 2:
		raise ValueError("An objective CBT question requires at least two options.")

	correct_count = sum(1 for row in rows if row["is_correct"])
	if question_type in {"Single Choice", "True/False"} and correct_count != 1:
		raise ValueError(f"{question_type} requires exactly one correct option.")
	if question_type == "Multiple Choice" and correct_count < 1:
		raise ValueError("Multiple Choice requires at least one correct option.")
	if question_type == "True/False" and len(rows) != 2:
		raise ValueError("True/False requires exactly two options.")

	return sorted(rows, key=lambda row: (row["display_order"], row["option_key"]))


def validate_exam_schedule(
	*,
	start_datetime: datetime,
	end_datetime: datetime,
	duration_minutes: int,
) -> None:
	if not start_datetime or not end_datetime:
		raise ValueError("CBT start and end date/time are required.")
	if end_datetime <= start_datetime:
		raise ValueError("CBT end date/time must be after the start date/time.")
	if int(duration_minutes or 0) <= 0:
		raise ValueError("CBT duration must be greater than zero minutes.")
	window_minutes = (end_datetime - start_datetime).total_seconds() / 60
	if window_minutes < int(duration_minutes):
		raise ValueError("The CBT availability window cannot be shorter than its duration.")


def compute_server_deadline(
	*,
	started_on: datetime,
	duration_minutes: int,
	exam_end_datetime: datetime,
) -> datetime:
	if not started_on or not exam_end_datetime:
		raise ValueError("Started time and exam end time are required.")
	if int(duration_minutes or 0) <= 0:
		raise ValueError("CBT duration must be greater than zero minutes.")
	return min(started_on + timedelta(minutes=int(duration_minutes)), exam_end_datetime)


def is_within_sync_grace(
	*,
	server_now: datetime,
	server_deadline: datetime,
	sync_grace_minutes: int,
) -> bool:
	if server_now <= server_deadline:
		return True
	return server_now <= server_deadline + timedelta(minutes=max(0, int(sync_grace_minutes or 0)))


def classify_sync_update(
	*,
	last_sequence: int | None,
	last_payload_hash: str | None,
	incoming_sequence: int,
	incoming_payload_hash: str,
) -> str:
	"""Classify an answer update without mutating state.

	Equal sequence + equal payload is idempotent. Equal sequence + changed payload is
	a conflict and must never overwrite the accepted answer silently.
	"""
	incoming_sequence = int(incoming_sequence)
	if incoming_sequence < 0:
		raise ValueError("Client answer sequence cannot be negative.")
	last_sequence = -1 if last_sequence is None else int(last_sequence)
	last_payload_hash = str(last_payload_hash or "")
	incoming_payload_hash = str(incoming_payload_hash or "")
	if not incoming_payload_hash:
		raise ValueError("Incoming CBT answer payload hash is required.")
	if incoming_sequence < last_sequence:
		return "Stale"
	if incoming_sequence == last_sequence:
		return "Duplicate" if incoming_payload_hash == last_payload_hash else "Conflict"
	if incoming_sequence > last_sequence + 1:
		return "Accepted With Gap"
	return "Accepted"


def objective_answer_key(question_type: str, options: list[dict]) -> Any:
	rows = validate_question_contract(question_type, options)
	keys = [row["option_key"] for row in rows if row["is_correct"]]
	return keys[0] if question_type in {"Single Choice", "True/False"} else sorted(keys)


def score_objective_response(question_type: str, answer_key: Any, response: Any) -> bool:
	question_type = str(question_type or "").strip()
	if question_type not in OBJECTIVE_QUESTION_TYPES:
		raise ValueError(f"Unsupported CBT question type: {question_type or 'blank'}")
	return canonical_response(answer_key) == canonical_response(response)
