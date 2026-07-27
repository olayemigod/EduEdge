from __future__ import annotations

from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]


class TestCBTInvigilationContract(unittest.TestCase):
	def test_invigilation_api_exposes_status_not_answer_content(self):
		service = (APP / "cbt" / "invigilation.py").read_text()
		for token in (
			"STALE_HEARTBEAT_SECONDS = 90",
			"get_invigilation_schedules",
			"get_invigilation_context",
			"reported_pending_sync_count",
			"heartbeat_age_seconds",
			"seconds_remaining",
			"result_readiness",
		):
			self.assertIn(token, service)
		for forbidden in (
			"answer_payload_json",
			"correct_option_ids_json",
			"answer_key",
			"marking_guide",
		):
			self.assertNotIn(forbidden, service)

	def test_result_gate_blocks_pending_review_incomplete_and_unscored_attempts(self):
		service = (APP / "cbt" / "result_readiness.py").read_text()
		for token in (
			"MISSING_ATTEMPTS",
			"OPEN_ATTEMPTS",
			"PENDING_SYNC",
			"REVIEW_REQUIRED",
			"NOT_READY_FOR_PROCESSING",
			"NOT_SCORED",
			"assert_result_processing_ready",
			"assert_result_approval_ready",
			"CBT result approval is blocked",
		):
			self.assertIn(token, service)
		self.assertIn('RESULT_APPROVAL_STATUSES = {"Scored"}', service)

	def test_invigilation_page_uses_edgesuite_auto_refresh_and_actionable_blockers(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_cbt_invigilation"
			/ "eduedge_cbt_invigilation.js"
		).read_text()
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_cbt_invigilation"
			/ "EduEdgeCBTInvigilation.vue"
		).read_text()
		for token in (
			"edgesuite_ui.bundle.js",
			"eduedge_cbt_invigilation.bundle.js",
			"createEduEdgeCBTInvigilationApp",
		):
			self.assertIn(token, loader)
		for token in (
			"REFRESH_INTERVAL_MS = 15000",
			"get_invigilation_schedules",
			"get_invigilation_context",
			"Result processing is blocked",
			"Pending Sync",
			"Connection Stale",
			"candidate.answered_count",
		):
			self.assertIn(token, component)
		for forbidden in (
			"answer_payload_json",
			"correct_option_ids_json",
			"answer_key",
			"marking_guide",
		):
			self.assertNotIn(forbidden, component)

	def test_access_manifest_and_menus_register_invigilation_route(self):
		access = (APP / "access_control.py").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		for token in (
			'"cbt_schedule": "EduEdge CBT Exam Schedule"',
			'"cbt_candidate_assignment": "EduEdge CBT Candidate Assignment"',
			'"cbt_attempt": "EduEdge CBT Attempt"',
			'"/app/eduedge-cbt-invigilation"',
		):
			self.assertIn(token, access)
		self.assertIn('route: "/app/eduedge-cbt-invigilation"', navigation)
		self.assertIn('route: "/app/eduedge-cbt-invigilation"', product_menu)
		self.assertIn('resource: "cbt_attempt"', product_menu)


if __name__ == "__main__":
	unittest.main()
