from __future__ import annotations

import json
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTAttemptEngineContract(unittest.TestCase):
	def _meta(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_attempt_has_server_timing_policy_snapshot_and_pending_sync_state(self):
		meta = self._meta("eduedge_cbt_attempt", "eduedge_cbt_attempt.json")
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"candidate_assignment",
			"attempt_number",
			"attempt_status",
			"started_at",
			"expires_at",
			"launch_token_hash",
			"randomisation_seed",
			"duration_minutes",
			"allow_resume",
			"device_change_policy",
			"attempt_review_policy",
			"questions",
			"reported_pending_sync_count",
			"last_heartbeat_at",
			"last_sync_at",
			"requires_review",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["questions"]["options"], "EduEdge CBT Attempt Question Snapshot")
		self.assertTrue(fields["launch_token_hash"].get("hidden"))
		self.assertTrue(fields["attempt_status"].get("read_only"))

	def test_candidate_snapshot_never_contains_correct_answer_flags(self):
		meta = self._meta(
			"eduedge_cbt_attempt_question_snapshot",
			"eduedge_cbt_attempt_question_snapshot.json",
		)
		fieldnames = {field["fieldname"] for field in meta["fields"]}
		self.assertIn("options_json", fieldnames)
		self.assertNotIn("is_correct", fieldnames)
		self.assertNotIn("answer_key", fieldnames)
		self.assertNotIn("marking_guide", fieldnames)

	def test_scoring_keys_are_separate_and_not_visible_to_candidate_roles(self):
		meta = self._meta(
			"eduedge_cbt_attempt_scoring_key",
			"eduedge_cbt_attempt_scoring_key.json",
		)
		fieldnames = {field["fieldname"] for field in meta["fields"]}
		self.assertIn("correct_option_ids_json", fieldnames)
		self.assertIn("answer_key", fieldnames)
		roles = {row["role"] for row in meta["permissions"]}
		self.assertNotIn("Student", roles)
		self.assertNotIn("EduEdge Parent", roles)
		self.assertNotIn("CBT Invigilator", roles)

	def test_answers_and_sync_logs_are_service_controlled(self):
		answer_controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_attempt_answer"
			/ "eduedge_cbt_attempt_answer.py"
		).read_text()
		sync_controller = (
			DOCTYPE_ROOT / "eduedge_cbt_sync_log" / "eduedge_cbt_sync_log.py"
		).read_text()
		self.assertIn("in_cbt_answer_sync", answer_controller)
		self.assertIn("idempotent answer-sync service", answer_controller)
		self.assertIn("append-only", sync_controller)
		self.assertIn("cannot be deleted", sync_controller)

	def test_attempt_service_enforces_integrity_and_offline_resilience(self):
		service = (APP / "cbt" / "attempts.py").read_text()
		for token in (
			"Public examinations require the central signed-launch service",
			"Candidate already has an active attempt",
			"Maximum Attempts has been reached",
			"launch_token_hash",
			"randomisation_seed",
			"hmac.compare_digest",
			"Client Revision must be at least 1",
			"Idempotency Key was reused with different content",
			"reported_pending_sync_count",
			"Pending Sync Resolved",
			"Server Timeout Auto-submit",
			"finalize_expired_attempts",
		):
			self.assertIn(token, service)
		self.assertNotIn('"is_correct":', service)

	def test_hooks_register_branch_permissions_and_server_timeout_job(self):
		hooks = (APP / "hooks.py").read_text()
		for token in (
			"eduedge.cbt.attempts.finalize_expired_attempts",
			"EduEdge CBT Attempt\": \"eduedge.cbt.permissions.cbt_attempt_query",
			"EduEdge CBT Attempt Answer\": \"eduedge.cbt.permissions.cbt_attempt_answer_query",
			"EduEdge CBT Attempt Scoring Key\": \"eduedge.cbt.permissions.cbt_attempt_scoring_key_query",
			"EduEdge CBT Sync Log\": \"eduedge.cbt.permissions.cbt_sync_log_query",
			"has_attempt_reference_permission",
		):
			self.assertIn(token, hooks)

	def test_general_settings_still_do_not_own_attempt_runtime_policy(self):
		settings = (
			DOCTYPE_ROOT / "eduedge_settings" / "eduedge_settings.json"
		).read_text()
		for token in (
			"client_session_id",
			"launch_token_hash",
			"reported_pending_sync_count",
			"device_change_policy",
			"attempt_review_policy",
		):
			self.assertNotIn(token, settings)


if __name__ == "__main__":
	unittest.main()
