from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultVerificationContract(unittest.TestCase):
	def test_issue_has_unique_hidden_verification_token(self):
		import json
		path = APP / "eduedge" / "doctype" / "eduedge_report_card_issue" / "eduedge_report_card_issue.json"
		payload = json.loads(path.read_text())
		fields = {row["fieldname"]: row for row in payload["fields"]}
		field = fields["verification_token"]
		self.assertEqual(field.get("hidden"), 1)
		self.assertEqual(field.get("unique"), 1)
		self.assertEqual(field.get("no_copy"), 1)

	def test_qr_verification_uses_unguessable_issue_token_and_payload_hash(self):
		service = (APP / "education" / "result_verification.py").read_text()
		issues = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn("frappe.generate_hash(length=32)", issues)
		self.assertIn("hmac.compare_digest", service)
		self.assertIn("hashlib.sha256", service)
		self.assertIn("payload_hash", service)
		self.assertIn("verification_token", service)

	def test_public_verification_does_not_expose_marks_comments_or_attendance(self):
		service = (APP / "education" / "result_verification.py").read_text()
		page = (APP / "www" / "eduedge-result-verify.html").read_text()
		for forbidden in ("courses", "total_score", "class_teacher_comment", "principal_comment", "attendance_percent", "student_id"):
			self.assertNotIn(f'"{forbidden}"', service)
		self.assertNotIn(forbidden, page)
		self.assertIn("Marks, comments and attendance are not exposed", page)

	def test_report_template_honors_profile_signatory_stamp_and_verification_controls(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("presentation.show_report_signatory", template)
		self.assertIn("presentation.show_official_stamp", template)
		self.assertIn("presentation.show_verification_qr", template)
		self.assertIn("branding.report_signatory_signature", template)
		self.assertIn("branding.official_stamp_image", template)
		self.assertIn("verification.qr_data_uri", template)

	def test_public_verification_marks_old_or_reopened_issues_without_invalidating_history(self):
		service = (APP / "education" / "result_verification.py").read_text()
		self.assertIn('"Superseded"', service)
		self.assertIn('"Review Reopened"', service)
		self.assertIn('"Current"', service)
		self.assertIn("A newer official issue exists.", service)

	def test_verification_page_is_public_noindex_and_read_only(self):
		page_py = (APP / "www" / "eduedge-result-verify.py").read_text()
		page_html = (APP / "www" / "eduedge-result-verify.html").read_text()
		self.assertIn("verify_issued_report_card", page_py)
		self.assertIn("noindex,nofollow,noarchive", page_html)
		self.assertIn('name="referrer" content="no-referrer"', page_html)
		self.assertIn("frappe.local.no_cache = 1", page_py)
		self.assertNotIn("frappe.whitelist", page_py)


if __name__ == "__main__":
	unittest.main()
