from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestIssuedReportCardPresentationContract(unittest.TestCase):
	def test_issued_payload_freezes_institution_identity(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn("get_report_identity", service)
		self.assertIn("def _freeze_institution_identity", service)
		self.assertIn('payload["institution"] = identity["institution"]', service)
		self.assertIn('payload["branding"] = identity["branding"]', service)
		self.assertIn('payload["terminology"] = identity["terminology"]', service)

	def test_profiled_api_does_not_replace_frozen_branding(self):
		api = (APP / "api" / "report_cards_profiled.py").read_text()
		self.assertIn('(payload.get("issue") or payload.get("issue_record"))', api)
		self.assertIn('and payload.get("branding")', api)
		self.assertIn('and payload.get("terminology")', api)
		self.assertIn("return payload", api)

	def test_unapproved_report_card_preview_is_visibly_draft(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("DRAFT / UNISSUED REPORT CARD", template)
		self.assertIn("OFFICIAL ISSUED REPORT CARD", template)
		self.assertIn("issued.issue_version", template)

	def test_official_footer_mentions_immutable_issue_version(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("Issued report-card version", template)
		self.assertIn("prior issued versions remain unchanged", template)


if __name__ == "__main__":
	unittest.main()
