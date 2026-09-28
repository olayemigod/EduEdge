from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionReportIdentityContract(unittest.TestCase):
	def test_institution_supports_report_signatory_and_stamp_identity(self):
		payload = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_institution" / "eduedge_institution.json").read_text()
		)
		fields = {row["fieldname"]: row for row in payload["fields"]}
		for fieldname in (
			"report_signatory_name",
			"report_signatory_title",
			"report_signatory_signature",
			"official_stamp_image",
		):
			self.assertIn(fieldname, fields)

	def test_result_profile_controls_signatory_stamp_and_verification_qr(self):
		payload = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json").read_text()
		)
		fields = {row["fieldname"]: row for row in payload["fields"]}
		for fieldname in ("show_report_signatory", "show_official_stamp", "show_verification_qr"):
			self.assertIn(fieldname, fields)

	def test_report_identity_and_presentation_are_snapshotted(self):
		profile = (APP / "education" / "result_profile.py").read_text()
		branding = (APP / "services" / "institution_branding.py").read_text()
		self.assertIn('"show_report_signatory": bool(doc.show_report_signatory)', profile)
		self.assertIn('"show_official_stamp": bool(doc.show_official_stamp)', profile)
		self.assertIn('"show_verification_qr": bool(doc.show_verification_qr)', profile)
		self.assertIn('"report_signatory_signature"', branding)
		self.assertIn('"official_stamp_image"', branding)

	def test_report_cards_use_and_freeze_institution_terminology(self):
		branding = (APP / "services" / "institution_branding.py").read_text()
		issues = (APP / "education" / "report_card_issues.py").read_text()
		api = (APP / "api" / "report_cards.py").read_text()
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("def get_report_identity", branding)
		self.assertIn('"terminology": context.get("terms") or {}', branding)
		self.assertIn('payload["terminology"] = identity["terminology"]', issues)
		self.assertIn("get_report_identity", api)
		self.assertIn("{% set student_group_label", template)
		self.assertIn("{% set course_label", template)
		self.assertIn("{% set courses_label", template)
		self.assertIn("{% set academic_year_label", template)
		self.assertIn("{% set academic_term_label", template)
		self.assertIn("{{ student_group_label }}", template)
		self.assertIn("{{ course_label }}", template)
		self.assertIn("{{ courses_label }}", template)


if __name__ == "__main__":
	unittest.main()
