from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfilePresentationContract(unittest.TestCase):
	def test_report_presentation_is_profile_configured_not_template_hardcoded(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in (
			"terminal_report_title",
			"annual_report_title",
			"show_student_photo",
			"show_attendance",
			"show_comments",
			"show_progression",
			"show_grading_legend",
			"show_next_period_date",
		):
			self.assertIn(fieldname, fields)

	def test_hidden_attendance_is_not_rendered_in_pdf_summary(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertGreaterEqual(
			template.count("presentation.show_attendance != false"),
			2,
		)
		self.assertIn('<span>{{ _("Attendance") }}</span>', template)

	def test_presentation_settings_are_snapshotted_with_profile_config(self):
		service = (APP / "education" / "result_profile.py").read_text()
		self.assertIn('"presentation": {', service)
		self.assertIn('"terminal_report_title": doc.terminal_report_title', service)
		self.assertIn('"annual_report_title": doc.annual_report_title', service)
		self.assertIn('"show_attendance": bool(doc.show_attendance)', service)


if __name__ == "__main__":
	unittest.main()
