from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportVerificationContract(unittest.TestCase):
	def test_issue_has_unique_opaque_verification_code(self):
		meta = (APP / "eduedge" / "doctype" / "eduedge_report_card_issue" / "eduedge_report_card_issue.json").read_text()
		issues = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn('"verification_code"', meta)
		self.assertIn('"unique": 1', meta)
		self.assertIn("secrets.token_urlsafe", issues)
		self.assertIn("generate_verification_code()", issues)

	def test_public_verification_checks_hash_current_issue_and_review_status(self):
		api = (APP / "api" / "report_verification.py").read_text()
		self.assertIn("hashlib.sha256", api)
		self.assertIn("Integrity Check Failed", api)
		self.assertIn("progression_status", api)
		self.assertIn("Superseded", api)
		self.assertIn("Under Review", api)
		self.assertIn("Current", api)

	def test_public_verification_does_not_return_marks_comments_or_attendance(self):
		api = (APP / "api" / "report_verification.py").read_text()
		return_block = api.split('return {\n\t\t"found": True,', 1)[-1]
		self.assertNotIn("total_score", return_block)
		self.assertNotIn("average_percent", return_block)
		self.assertNotIn("class_teacher_comment", return_block)
		self.assertNotIn("principal_comment", return_block)
		self.assertNotIn("attendance", return_block)

	def test_official_payload_gets_verification_url_and_qr(self):
		issues = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn("build_verification_url", issues)
		self.assertIn("build_verification_qr_data_uri", issues)
		self.assertIn("verification_qr_data_uri", issues)
		self.assertIn("pyqrcode", issues)

	def test_public_page_is_noindex_and_supports_code_lookup(self):
		page = (APP / "www" / "verify-result.html").read_text()
		self.assertIn("noindex,nofollow,noarchive", page)
		self.assertIn('name="code"', page)
		self.assertIn("Verify Result", page)

	def test_existing_issues_are_backfilled_without_mutating_payload_hash(self):
		patch = (APP / "patches" / "v1_0" / "backfill_report_card_verification_codes.py").read_text()
		self.assertIn("generate_verification_code", patch)
		self.assertIn('"verification_code"', patch)
		self.assertNotIn("payload_json", patch)
		self.assertNotIn("payload_hash", patch)


if __name__ == "__main__":
	unittest.main()
