from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultNotificationContract(unittest.TestCase):
	def test_issue_notifies_student_and_verified_guardian_users(self):
		service = (APP / "education" / "result_notifications.py").read_text()
		self.assertIn('"Student"', service)
		self.assertIn('"Student Guardian"', service)
		self.assertIn('"Guardian"', service)
		self.assertIn('"User"', service)
		self.assertIn('"enabled": 1', service)

	def test_notification_is_privacy_safe_and_links_to_authenticated_portal(self):
		service = (APP / "education" / "result_notifications.py").read_text()
		self.assertIn("A new school result is available", service)
		self.assertIn("An approved report card is available in My Results.", service)
		self.assertIn('"/eduedge-results"', service)
		self.assertNotIn("average_percent", service)
		self.assertNotIn("total_score", service)

	def test_notification_is_idempotent_per_issue_and_user(self):
		service = (APP / "education" / "result_notifications.py").read_text()
		self.assertIn('"Notification Log"', service)
		self.assertIn('"document_name": issue.name', service)
		self.assertIn("if frappe.db.exists(", service)

	def test_notification_failure_does_not_block_report_issue(self):
		service = (APP / "education" / "result_notifications.py").read_text()
		self.assertIn("except Exception:", service)
		self.assertIn("frappe.log_error(", service)

	def test_issue_creation_invokes_notification_after_immutable_issue_insert(self):
		issues = (APP / "education" / "report_card_issues.py").read_text()
		insert_at = issues.index("issue.insert(ignore_permissions=True)")
		notify_at = issues.index("notify_report_card_recipients(issue.name)")
		self.assertLess(insert_at, notify_at)


if __name__ == "__main__":
	unittest.main()
