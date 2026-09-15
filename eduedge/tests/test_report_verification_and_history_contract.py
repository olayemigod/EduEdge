from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportVerificationAndHistoryContract(unittest.TestCase):
	def test_issued_report_card_has_random_immutable_verification_token(self):
		path = APP / "eduedge" / "doctype" / "eduedge_report_card_issue" / "eduedge_report_card_issue.json"
		payload = json.loads(path.read_text())
		fields = {row["fieldname"]: row for row in payload["fields"]}
		self.assertIn("verification_token", fields)
		self.assertTrue(fields["verification_token"].get("read_only"))
		self.assertTrue(fields["verification_token"].get("unique"))
		issues = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn('"verification_token": frappe.generate_hash(length=32)', issues)

	def test_public_verification_is_token_and_hash_checked_without_marks(self):
		service = (APP / "education" / "result_verification.py").read_text()
		self.assertIn("hmac.compare_digest", service)
		self.assertIn("hashlib.sha256", service)
		self.assertIn("get_qr_code", service)
		self.assertIn("Superseded", service)
		self.assertIn("Review Reopened", service)
		self.assertNotIn('"overall_percentage"', service)
		self.assertNotIn('"total_score"', service)

	def test_public_verification_page_is_noindex_and_privacy_safe(self):
		page = (APP / "www" / "eduedge-result-verify.html").read_text()
		self.assertIn("noindex,nofollow,noarchive", page)
		self.assertIn("does not expose marks", page)
		self.assertNotIn("Continuous Assessment", page)
		self.assertNotIn("Principal Comment", page)

	def test_report_card_pdf_honors_frozen_signatory_stamp_and_qr_controls(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("presentation.show_report_signatory", template)
		self.assertIn("presentation.show_official_stamp", template)
		self.assertIn("presentation.show_verification_qr", template)
		self.assertIn("branding.report_signatory_signature", template)
		self.assertIn("branding.official_stamp_image", template)
		self.assertIn("verification.qr_data_uri", template)

	def test_report_card_operations_exposes_issue_and_publication_history(self):
		api = (APP / "api" / "report_cards.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn("def get_report_card_history", api)
		self.assertIn("get_report_card_issue_history", api)
		self.assertIn("Publication and issue history", vue)
		self.assertIn("loadHistory", vue)
		self.assertIn("fingerprint", vue)


if __name__ == "__main__":
	unittest.main()
