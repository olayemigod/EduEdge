from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardPresentationContract(unittest.TestCase):
	def test_pdf_uses_profile_titles_and_optional_sections(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("presentation.annual_report_title", template)
		self.assertIn("presentation.terminal_report_title", template)
		self.assertIn("presentation.show_student_photo", template)
		self.assertIn("presentation.show_attendance", template)
		self.assertIn("presentation.show_comments", template)
		self.assertIn("presentation.show_progression", template)
		self.assertIn("presentation.show_grading_legend", template)
		self.assertIn("presentation.show_next_period_date", template)

	def test_presentation_settings_come_from_snapshotted_result_profile(self):
		profiled = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn('"profile": profile', profiled)
		snapshot = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn('"profile": config', snapshot)

	def test_annual_pdf_density_adapts_to_dynamic_column_count(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("annual_column_count", template)
		self.assertIn('annual_density = "ultra" if annual_column_count > 18', template)
		self.assertIn("annual-density-{{ annual_density }}", template)
		self.assertIn(".annual-result-table.annual-density-compact", template)
		self.assertIn(".annual-result-table.annual-density-ultra", template)
		self.assertIn("overflow-wrap: anywhere", template)


if __name__ == "__main__":
	unittest.main()
