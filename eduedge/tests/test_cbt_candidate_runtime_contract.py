from __future__ import annotations

from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
PUBLIC_JS = APP / "public" / "js"
WWW = APP / "www"


class TestCBTCandidateRuntimeContract(unittest.TestCase):
	def test_candidate_web_route_is_non_indexed_and_loads_runtime_assets(self):
		template = (WWW / "eduedge-cbt-attempt.html").read_text()
		controller = (WWW / "eduedge-cbt-attempt.py").read_text()
		for token in (
			'noindex,nofollow,noarchive',
			'no-referrer',
			'eduedge_cbt_candidate.css',
			'eduedge_cbt_runtime_storage.js',
			'eduedge_cbt_candidate.js',
			'eduedge_cbt_candidate_serialization.js',
		):
			self.assertIn(token, template)
		self.assertIn("no_cache = 1", controller)
		self.assertIn("context.no_breadcrumbs = True", controller)

	def test_launch_token_uses_fragment_and_is_not_persisted_in_local_storage(self):
		launch = (APP / "cbt" / "candidate_launch.py").read_text()
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		self.assertIn("#attempt={attempt}&token={token}", launch)
		self.assertIn("stores only its secure token hash", launch)
		self.assertIn("window.sessionStorage.setItem(tokenKey, token)", candidate)
		self.assertNotIn("window.localStorage.setItem(tokenKey, token)", candidate)
		self.assertIn('clean.searchParams.delete("token")', candidate)
		self.assertIn('clean.hash = ""', candidate)

	def test_indexeddb_queue_persists_answers_batches_and_submission_intent(self):
		storage = (PUBLIC_JS / "eduedge_cbt_runtime_storage.js").read_text()
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		for token in (
			'const DB_NAME = "eduedge-cbt-runtime"',
			'const ANSWERS = "answers"',
			'const BATCHES = "batches"',
			'async pendingAnswers()',
			'async putActiveBatch(batch)',
			'async markBatchSynced(batch)',
		):
			self.assertIn(token, storage)
		for token in (
			'cached_attempt_state',
			'timer_deadline_epoch',
			'submission_requested',
			'idempotency_key',
			'reported_pending_count',
		):
			self.assertIn(token, candidate)

	def test_candidate_runtime_handles_network_timer_refresh_and_pending_sync(self):
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		for token in (
			'window.addEventListener("online"',
			'window.addEventListener("offline"',
			'document.addEventListener("visibilitychange"',
			'window.addEventListener("beforeunload"',
			'You are offline. Existing questions and browser-saved answers are available',
			'Time has ended. Answers saved before the deadline are locked',
			'Submission saved in this browser',
			'All answers synced',
			'API.sync',
			'API.heartbeat',
			'API.submit',
		):
			self.assertIn(token, candidate)

	def test_candidate_runtime_enforces_one_active_tab_per_attempt(self):
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		for token in (
			'TAB_LEASE_REFRESH_MS = 4000',
			'TAB_LEASE_TTL_MS = 15000',
			'CONCURRENT_TAB_EVENT = "Concurrent Tab Detected"',
			'eduedge:cbt:tab-instance:',
			'eduedge:cbt:active-tab:',
			'window.sessionStorage.setItem(key, value)',
			'async acquireTabLease()',
			'refreshTabLease()',
			'window.addEventListener("storage"',
			'async handleTabConflict()',
			'runtime_event: eventName',
			'Continue in the original tab',
		):
			self.assertIn(token, candidate)
		self.assertIn("if (!(await this.acquireTabLease())) return", candidate)


	def test_sync_conflict_pauses_automatic_retry_and_locks_candidate(self):
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		for token in (
			"this.syncConflict = false",
			"if (this.syncConflict) return false",
			"if (this.syncConflict) return;",
			"this.enterSyncConflict(result.conflict_question || \"\")",
			"enterSyncConflict(questionKey = \"\")",
			"window.clearInterval(this.periodicSyncInterval)",
			"Synchronisation paused — invigilator review required",
			"Submission is blocked until the answer synchronisation conflict is reviewed",
			'badge.textContent = this.syncConflict',
			"if (!this.syncConflict) await this.refreshState()",
		):
			self.assertIn(token, candidate)


	def test_runtime_security_event_is_heartbeat_only(self):
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		submit_block = candidate.split("async completeQueuedSubmission()", 1)[1].split(
			"async refreshState()", 1
		)[0]
		heartbeat_block = candidate.split('async heartbeat(runtimeEvent = "")', 1)[1].split(
			"async handleLocalTimeout()", 1
		)[0]
		self.assertNotIn("runtime_event", submit_block)
		self.assertIn("runtime_event: runtimeEvent || undefined", heartbeat_block)


	def test_candidate_payload_never_requests_or_renders_scoring_keys(self):
		candidate = (PUBLIC_JS / "eduedge_cbt_candidate.js").read_text()
		for forbidden in (
			"correct_option_ids_json",
			"answer_key",
			"marking_guide",
			"is_correct",
		):
			self.assertNotIn(forbidden, candidate)
		self.assertIn("sanitizeRichText", candidate)
		self.assertIn("BASIC_RICH_TEXT_TAGS", candidate)

	def test_rapid_saves_are_serialised_per_question(self):
		serialisation = (
			PUBLIC_JS / "eduedge_cbt_candidate_serialization.js"
		).read_text()
		for token in (
			"questionQueues = new Map()",
			"serialisedSaveAnswer",
			"previous.catch",
			"originalSaveAnswer(questionKey, answer)",
		):
			self.assertIn(token, serialisation)

	def test_candidate_assignment_exposes_authorised_launch_action(self):
		form = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_candidate_assignment"
			/ "eduedge_cbt_candidate_assignment.js"
		).read_text()
		for token in (
			"Prepare Candidate Attempt",
			"prepare_candidate_launch",
			"Copy Candidate Link",
			"Open Candidate Page",
			'frm.doc.assignment_status === "Released"',
		):
			self.assertIn(token, form)


if __name__ == "__main__":
	unittest.main()
