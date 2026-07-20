from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from eduedge.cbt.domain import (
	canonical_response,
	classify_sync_update,
	compute_server_deadline,
	is_within_sync_grace,
	objective_answer_key,
	score_objective_response,
	stable_hash,
	validate_exam_schedule,
	validate_question_contract,
)


class TestCBTDomain(unittest.TestCase):
	def test_single_choice_requires_exactly_one_correct_option(self):
		with self.assertRaisesRegex(ValueError, "exactly one correct"):
			validate_question_contract(
				"Single Choice",
				[
					{"option_key": "A", "option_text": "One", "is_correct": 1},
					{"option_key": "B", "option_text": "Two", "is_correct": 1},
				],
			)

	def test_true_false_requires_two_options(self):
		with self.assertRaisesRegex(ValueError, "exactly two options"):
			validate_question_contract(
				"True/False",
				[
					{"option_key": "T", "option_text": "True", "is_correct": 1},
					{"option_key": "F", "option_text": "False"},
					{"option_key": "U", "option_text": "Unknown"},
				],
			)

	def test_exam_window_cannot_be_shorter_than_duration(self):
		start = datetime(2026, 7, 20, 9, 0)
		with self.assertRaisesRegex(ValueError, "cannot be shorter"):
			validate_exam_schedule(
				start_datetime=start,
				end_datetime=start + timedelta(minutes=30),
				duration_minutes=45,
			)

	def test_server_deadline_respects_exam_close(self):
		start = datetime(2026, 7, 20, 9, 45)
		deadline = compute_server_deadline(
			started_on=start,
			duration_minutes=60,
			exam_end_datetime=datetime(2026, 7, 20, 10, 0),
		)
		self.assertEqual(deadline, datetime(2026, 7, 20, 10, 0))

	def test_sync_classification_is_idempotent_and_conflict_safe(self):
		payload_hash = stable_hash({"question": "Q1", "response": "A"})
		self.assertEqual(
			classify_sync_update(
				last_sequence=4,
				last_payload_hash=payload_hash,
				incoming_sequence=4,
				incoming_payload_hash=payload_hash,
			),
			"Duplicate",
		)
		self.assertEqual(
			classify_sync_update(
				last_sequence=4,
				last_payload_hash=payload_hash,
				incoming_sequence=4,
				incoming_payload_hash=stable_hash({"question": "Q1", "response": "B"}),
			),
			"Conflict",
		)
		self.assertEqual(
			classify_sync_update(
				last_sequence=4,
				last_payload_hash=payload_hash,
				incoming_sequence=6,
				incoming_payload_hash=stable_hash({"question": "Q1", "response": "C"}),
			),
			"Accepted With Gap",
		)

	def test_sync_grace_is_server_time_based(self):
		deadline = datetime(2026, 7, 20, 10, 0)
		self.assertTrue(
			is_within_sync_grace(
				server_now=deadline + timedelta(minutes=9),
				server_deadline=deadline,
				sync_grace_minutes=10,
			)
		)
		self.assertFalse(
			is_within_sync_grace(
				server_now=deadline + timedelta(minutes=11),
				server_deadline=deadline,
				sync_grace_minutes=10,
			)
		)

	def test_multiple_choice_scoring_is_order_independent(self):
		options = [
			{"option_key": "A", "option_text": "One", "is_correct": 1},
			{"option_key": "B", "option_text": "Two"},
			{"option_key": "C", "option_text": "Three", "is_correct": 1},
		]
		answer_key = objective_answer_key("Multiple Choice", options)
		self.assertTrue(score_objective_response("Multiple Choice", answer_key, ["C", "A"]))
		self.assertFalse(score_objective_response("Multiple Choice", answer_key, ["A"]))

	def test_canonical_response_normalizes_whitespace_and_order(self):
		self.assertEqual(canonical_response([" C ", "A", "A"]), ["A", "C"])


if __name__ == "__main__":
	unittest.main()
