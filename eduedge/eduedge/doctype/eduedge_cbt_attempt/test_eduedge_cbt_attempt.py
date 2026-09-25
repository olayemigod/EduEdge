from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from eduedge.cbt import attempt_runtime_guard
from eduedge.cbt import attempts as attempt_service


class TestEduEdgeCBTAttemptTimeoutReconciliation(FrappeTestCase):
	def _make_timed_out_attempt(self, *, pending: int = 0):
		now = now_datetime()
		token = frappe.generate_hash(length=32)
		attempt = frappe.get_doc(
			{
				"doctype": "EduEdge CBT Attempt",
				"candidate_assignment": f"TEST-CBT-ASSIGN-{frappe.generate_hash(length=10)}",
				"attempt_number": 1,
				"exam_scope": attempt_service.SCHOOL_EXAM,
				"candidate_name": "CBT Timeout Reconciliation Test",
				"attempt_status": "In Progress",
				"started_at": now - timedelta(minutes=31),
				"expires_at": now - timedelta(minutes=1),
				"client_session_id": "test-timeout-session",
				"launch_token_hash": attempt_service._hash(token),
				"launch_token_expires_at": now + timedelta(hours=1),
				"auto_submit_on_timeout": 1,
				"reported_pending_sync_count": pending,
				"requires_review": 0,
			}
		)
		attempt.flags.ignore_links = True
		with attempt_service._flag("in_cbt_attempt_service"):
			attempt.insert(ignore_permissions=True)
		return attempt, token

	def test_server_timeout_waits_for_bound_browser_zero_pending_confirmation(self):
		attempt, token = self._make_timed_out_attempt(pending=0)

		attempt_service._finalize_timeout(attempt.name)
		attempt.reload()
		self.assertEqual(attempt.attempt_status, "Pending Sync")
		self.assertEqual(attempt.submission_source, "Server Timeout Auto-submit")
		self.assertEqual(attempt.reported_pending_sync_count, 0)
		self.assertFalse(attempt.requires_review)
		self.assertGreater(
			attempt_service.reconciliation_deadline(attempt),
			now_datetime(),
		)

		result = attempt_runtime_guard.submit_attempt(
			attempt.name,
			token,
			"test-timeout-session",
			reported_pending_count=0,
		)
		attempt.reload()
		self.assertEqual(result["status"], "Auto Submitted")
		self.assertEqual(attempt.attempt_status, "Auto Submitted")
		self.assertEqual(attempt.reported_pending_sync_count, 0)

	def test_submit_confirmation_cannot_erase_server_known_pending_answers(self):
		attempt, token = self._make_timed_out_attempt(pending=2)

		attempt_service._finalize_timeout(attempt.name)
		attempt.reload()
		self.assertEqual(attempt.attempt_status, "Pending Sync")
		self.assertEqual(attempt.reported_pending_sync_count, 2)

		result = attempt_runtime_guard.submit_attempt(
			attempt.name,
			token,
			"test-timeout-session",
			reported_pending_count=0,
		)
		attempt.reload()
		self.assertEqual(result["status"], "Pending Sync")
		self.assertEqual(attempt.attempt_status, "Pending Sync")
		self.assertEqual(attempt.reported_pending_sync_count, 2)
