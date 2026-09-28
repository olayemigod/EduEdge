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

	def test_reconciliation_mutations_share_absolute_deadline_guard(self):
		guard = (APP / "cbt" / "attempt_runtime_guard.py").read_text()

		for token in (
			"def _assert_reconciliation_window_open(attempt)",
			'attempt.attempt_status not in {"Pending Sync", "Auto Submitted", "Timed Out"}',
			"deadline = base.reconciliation_deadline(attempt)",
			"now_datetime() > deadline",
			"The browser reconciliation window has expired.",
			"def record_heartbeat(",
			"_assert_reconciliation_window_open(attempt)",
		):
			self.assertIn(token, guard)

		sync_block = guard.split("def sync_answers(", 1)[1].split(
			"@frappe.whitelist(allow_guest=True)\ndef record_heartbeat", 1
		)[0]
		self.assertIn("_assert_reconciliation_window_open(attempt)", sync_block)

		submit_block = guard.split("def submit_attempt(", 1)[1]
		self.assertIn("_assert_reconciliation_window_open(attempt)", submit_block)

		hooks = (APP / "hooks.py").read_text()
		candidate = (APP / "public" / "js" / "eduedge_cbt_candidate.js").read_text()
		self.assertIn(
			'"eduedge.cbt.attempts.record_heartbeat": "eduedge.cbt.attempt_runtime_guard.record_heartbeat"',
			hooks,
		)
		self.assertIn(
			'heartbeat: "eduedge.cbt.attempt_runtime_guard.record_heartbeat"',
			candidate,
		)


	def test_heartbeat_flags_and_audits_concurrent_tab_detection(self):
		service = (APP / "cbt" / "attempts.py").read_text()
		for token in (
			'RUNTIME_SECURITY_EVENTS = {',
			'"Concurrent Tab Detected": "Concurrent browser tab detected for this attempt."',
			"def _record_runtime_security_event",
			'"requires_review": 1',
			'"EduEdge CBT Lifecycle Log"',
			'event_type=event',
			'def record_heartbeat(',
			'runtime_event: str | None = None',
			'_record_runtime_security_event(attempt, runtime_event)',
		):
			self.assertIn(token, service)


	def test_sync_conflict_flags_review_and_preserves_pending_evidence(self):
		guard = (APP / "cbt" / "attempt_runtime_guard.py").read_text()
		for token in (
			'"requires_review": 1',
			'"reported_pending_sync_count": pending',
			'"last_heartbeat_at": server_time',
			'cint(answer_count) + max(0, cint(reported_pending_count))',
			'"sync_status": "Conflict"',
			"base.ANSWER_SYNC_CONFLICT_REASON",
			'"answer_sync_conflict": base._answer_sync_conflict_active(attempt)',
		):
			self.assertIn(token, guard)


	def test_sync_conflict_state_survives_reload_and_heartbeat_until_review_resolution(self):
		attempts = (APP / "cbt" / "attempts.py").read_text()
		guard = (APP / "cbt" / "attempt_runtime_guard.py").read_text()
		for token in (
			'ANSWER_SYNC_CONFLICT_REASON = "Answer revision conflict detected during browser synchronisation."',
			"def _answer_sync_conflict_active(attempt)",
			"cint(attempt.requires_review)",
			'"answer_sync_conflict": _answer_sync_conflict_active(attempt)',
		):
			self.assertIn(token, attempts)
		self.assertIn('"answer_sync_conflict": False', guard)
		self.assertIn('"answer_sync_conflict": base._answer_sync_conflict_active(attempt)', guard)


	def test_server_timeout_waits_for_browser_reconciliation_before_scoring(self):
		attempts = (APP / "cbt" / "attempts.py").read_text()
		guard = (APP / "cbt" / "attempt_runtime_guard.py").read_text()
		scoring = (APP / "cbt" / "scoring.py").read_text()

		self.assertIn("SYNC_RECONCILIATION_HOURS = 24", attempts)
		self.assertIn("def reconciliation_deadline(attempt)", attempts)
		finalize = attempts.split("def _finalize_timeout", 1)[1].split(
			"def finalize_expired_attempts", 1
		)[0]
		for token in (
			'status = "Pending Sync"',
			'"Server Timeout Auto-submit"',
			'"Server timeout entered the browser reconciliation window."',
		):
			self.assertIn(token, finalize)
		self.assertNotIn('status = "Auto Submitted"', finalize)

		for token in (
			"deadline = base.reconciliation_deadline(attempt)",
			'attempt.attempt_status == "Pending Sync"',
			'str(attempt.submission_source or "").startswith("Server Timeout")',
			"not client_pending",
			"not cint(attempt.reported_pending_sync_count)",
			'"attempt_status": "Auto Submitted"',
		):
			self.assertIn(token, guard)
		self.assertIn('SCOREABLE_ATTEMPT_STATUSES = {"Submitted", "Auto Submitted"}', scoring)
		self.assertIn("Pending browser answers must be resolved before scoring.", scoring)


	def test_runtime_guard_hides_prestart_and_terminal_questions_and_audits_late_answers(self):
		guard = (APP / "cbt" / "attempt_runtime_guard.py").read_text()
		for token in (
			'"questions": []',
			'"answers": {}',
			'base.reconciliation_deadline(attempt)',
			'Post-submission sync accepts only answers saved before the server cutoff',
			'Answers were reconciled after submission or timeout',
			'attempt.attempt_status == "In Progress" and base._remaining(attempt) <= 0',
			'show_questions = attempt.attempt_status == "In Progress"',
		):
			self.assertIn(token, guard)

	def test_hooks_register_branch_permissions_timeout_and_rpc_guards(self):
		hooks = (APP / "hooks.py").read_text()
		for token in (
			"eduedge.security.feature_gate.run_cbt_expiry_job",
			"eduedge.cbt.attempt_runtime_guard.get_attempt_state",
			"eduedge.cbt.attempt_runtime_guard.sync_answers",
			"eduedge.cbt.attempt_runtime_guard.submit_attempt",
			"EduEdge CBT Attempt\": \"eduedge.cbt.permissions.cbt_attempt_query",
			"EduEdge CBT Attempt Answer\": \"eduedge.cbt.permissions.cbt_attempt_answer_query",
			"EduEdge CBT Attempt Scoring Key\": \"eduedge.cbt.permissions.cbt_attempt_scoring_key_query",
			"EduEdge CBT Sync Log\": \"eduedge.cbt.permissions.cbt_sync_log_query",
			"has_attempt_reference_permission",
		):
			self.assertIn(token, hooks)
		self.assertNotIn('"eduedge.cbt.attempts.finalize_expired_attempts"', hooks)

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
