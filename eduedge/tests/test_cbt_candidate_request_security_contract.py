from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCBTCandidateRequestSecurityContract(unittest.TestCase):
	def test_every_public_candidate_endpoint_is_covered(self):
		security = (APP / "security/cbt_candidate_requests.py").read_text()
		for command in (
			"eduedge.cbt.attempts.get_attempt_state",
			"eduedge.cbt.attempts.start_attempt",
			"eduedge.cbt.attempts.record_heartbeat",
			"eduedge.cbt.attempts.sync_answers",
			"eduedge.cbt.attempts.submit_attempt",
			"eduedge.cbt.attempt_runtime_guard.get_attempt_state",
			"eduedge.cbt.attempt_runtime_guard.sync_answers",
			"eduedge.cbt.attempt_runtime_guard.submit_attempt",
		):
			self.assertIn(f'"{command}"', security)

	def test_offline_sync_has_bounded_but_practical_limits(self):
		security = (APP / "security/cbt_candidate_requests.py").read_text()
		for expected in (
			"MAX_ANSWER_ROWS = 500",
			"MAX_ANSWER_PAYLOAD_BYTES = 256 * 1024",
			"MAX_TEXT_ANSWER_LENGTH = 10_000",
			"MAX_NUMERIC_ANSWER_LENGTH = 128",
			"MAX_SELECTED_OPTION_IDS = 50",
			"MAX_IDEMPOTENCY_KEY_LENGTH = 128",
			"MAX_PENDING_COUNT = 10_000",
			"Client Revision is outside the allowed range.",
			"Written answer exceeds the allowed length.",
			"Answer sync payload is too large.",
		):
			self.assertIn(expected, security)

	def test_candidate_rate_limits_are_ip_and_attempt_scoped(self):
		security = (APP / "security/cbt_candidate_requests.py").read_text()
		for expected in (
			'"state": (60, 60)',
			'"start": (10, 60)',
			'"heartbeat": (30, 60)',
			'"sync": (90, 60)',
			'"submit": (10, 60)',
			'_increment_rate_limit(action, "ip"',
			'"attempt"',
			'frappe.local.response["http_status_code"] = 429',
			"expires_in_sec=window_seconds + 5",
		):
			self.assertIn(expected, security)

	def test_request_hook_forces_candidate_tokens_into_post_body(self):
		guard = (APP / "security/request_method.py").read_text()
		for expected in (
			"is_candidate_command(command)",
			'if method != "POST"',
			"_reject_non_post()",
			"enforce_candidate_request(command",
			"Candidate launch tokens are accepted only in POST bodies",
		):
			self.assertIn(expected, guard)


if __name__ == "__main__":
	unittest.main()
