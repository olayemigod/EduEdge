from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardV2Contract(unittest.TestCase):
	def test_profiled_report_cards_read_immutable_snapshots(self):
		service = (APP / "education" / "report_cards.py").read_text()
		profiled = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn("get_profiled_publication_student_summaries", service)
		self.assertIn("get_profiled_student_report_card_payload", service)
		self.assertIn("EduEdge Published Result Snapshot", profiled)
		self.assertIn("get_snapshot_payload", profiled)
		self.assertNotIn('set_value("Assessment Result"', profiled)
		self.assertNotIn('db_set("Assessment Result"', profiled)

	def test_historical_profiled_roster_uses_snapshot_not_current_active_membership(self):
		service = (APP / "education" / "report_cards.py").read_text()
		self.assertIn("if publication.result_profile:", service)
		self.assertIn('"EduEdge Published Result Snapshot"', service)
		self.assertIn("Student Group Student", service)

	def test_terminal_and_annual_payloads_normalize_dynamic_components_and_metrics(self):
		profiled = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn("display_components", profiled)
		self.assertIn("display_metrics", profiled)
		self.assertIn("period_map", profiled)
		self.assertIn("annual_percentage", profiled)
		self.assertIn("attendance_school_opened", profiled)
		self.assertIn("academic_term_label", profiled)
		self.assertIn("component_totals", profiled)

	def test_terminal_progression_suggestion_is_not_auto_promoted(self):
		profiled = (APP / "education" / "profiled_report_cards.py").read_text()
		self.assertIn('if mode != "Annual" or not has_courses:', profiled)
		self.assertIn('return "Pending Review"', profiled)

	def test_report_template_renders_dynamic_terminal_and_annual_structures(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn('mode == "Annual"', template)
		self.assertIn("summary.display_components", template)
		self.assertIn("summary.display_metrics", template)
		self.assertIn("period.display_label", template)
		self.assertIn("course.cumulative_score", template)
		self.assertIn("course.annual_percentage", template)
		self.assertIn("School Opened", template)
		self.assertIn("Total Average Mark", template)
		self.assertIn("Grand Total", template)
		self.assertIn("summary.component_totals", template)
		self.assertIn("immutable Published Result Snapshot", template)

	def test_report_card_page_exposes_mode_version_and_snapshot_table(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn("publication.result_mode", vue)
		self.assertIn("publication.publication_version", vue)
		self.assertIn("Published academic snapshot", vue)
		self.assertIn("terminalComponentScore", vue)
		self.assertIn("annualPeriodScore", vue)
		self.assertIn("display_metrics", vue)


if __name__ == "__main__":
	unittest.main()
