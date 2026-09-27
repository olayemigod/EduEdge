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

	def test_issued_payload_freezes_pdf_render_settings(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		main_api = (APP / "api" / "report_cards.py").read_text()
		profiled_api = (APP / "api" / "report_cards_profiled.py").read_text()
		self.assertIn("def _freeze_issue_render_settings", service)
		self.assertIn('payload["render_settings"] = _current_report_card_render_settings(payload)', service)
		self.assertIn("def resolve_report_card_render_settings", service)
		self.assertIn('(payload.get("branding") or {}).get("report_card_letter_head")', service)
		self.assertIn('"letterhead": letterhead', service)
		self.assertIn('"show_marks": bool(settings.report_card_show_marks)', service)
		self.assertIn("resolve_report_card_render_settings(payload)", main_api)
		self.assertIn('render_settings["letterhead"]', main_api)
		self.assertIn('render_settings["show_marks"]', main_api)
		self.assertIn("resolve_report_card_render_settings(payload)", profiled_api)
		self.assertIn('render_settings["letterhead"]', profiled_api)
		self.assertIn('render_settings["show_marks"]', profiled_api)

	def test_legacy_issued_payloads_fall_back_to_current_render_settings(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn('if payload.get("issue") or payload.get("issue_record")', service)
		self.assertIn("if isinstance(frozen, dict)", service)
		self.assertIn("return _current_report_card_render_settings(payload)", service)

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

	def test_issued_template_prefers_runtime_issue_record_for_fingerprint(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("{% set issued = issue_record or issue %}", template)
		self.assertNotIn("{% set issued = issue or issue_record %}", template)
		self.assertIn("issued.payload_hash", template)
		self.assertIn("issued.issue_version", template)

	def test_official_footer_mentions_immutable_issue_version(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("Issued report-card version", template)
		self.assertIn("prior issued versions remain unchanged", template)


if __name__ == "__main__":
	unittest.main()
