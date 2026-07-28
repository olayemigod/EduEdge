from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationReadinessContract(unittest.TestCase):
	def test_foundation_api_returns_calendar_periods_progression_and_readiness(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		for token in (
			"MAX_PERIOD_ROWS",
			"_attach_calendar_periods",
			'"current_period"',
			'"has_calendar_gap_today"',
			"_build_progression",
			"_walk_progression_chain",
			"_build_readiness",
			'"can_write_calendar"',
		):
			self.assertIn(token, api)

	def test_calendar_readiness_keeps_intentional_gaps_visible(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertIn('"code": "calendar_gap"', api)
		self.assertIn("outside every configured Academic Period", api)
		self.assertIn('"code": "calendar_without_periods"', api)
		self.assertNotIn("current_academic_term", api)

	def test_progression_readiness_reports_disabled_or_missing_targets(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertIn("Next level is missing or disabled.", api)
		self.assertIn('"code": "progression_gap"', api)
		self.assertIn("progression link(s) point to missing or disabled Levels", api)

	def test_foundation_page_exposes_readiness_progression_and_calendar_surfaces(self):
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_academic_foundation"
			/ "EduEdgeAcademicFoundation.vue"
		).read_text(encoding="utf-8")
		for token in (
			"<EdgeDashboardLayout",
			"Foundation Readiness",
			"Progression pathway",
			"Academic calendars",
			"current_period",
			"has_calendar_gap_today",
			"selectedProgression",
			"selectedReadiness",
		):
			self.assertIn(token, component)

	def test_calendar_mutations_remain_on_the_validated_native_form(self):
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_academic_foundation"
			/ "EduEdgeAcademicFoundation.vue"
		).read_text(encoding="utf-8")
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertIn('frappe.new_doc("EduEdge Institution Academic Calendar"', component)
		self.assertIn('frappe.set_route("Form", "EduEdge Institution Academic Calendar"', component)
		self.assertNotIn("save_academic_calendar", api)
		self.assertNotIn("frappe.db.set_value", api)

	def test_section_and_level_descriptions_round_trip_through_the_page_api(self):
		api = (APP / "api" / "academic_foundation.py").read_text(encoding="utf-8")
		self.assertGreaterEqual(api.count('"description"'), 4)


if __name__ == "__main__":
	unittest.main()
