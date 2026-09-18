from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
NAVIGATION = APP / "public" / "js" / "eduedge_ui" / "navigation.js"
PRODUCT_MENU = APP / "public" / "js" / "eduedge_product_menu.bundle.js"
RESOURCE_CENTER = APP / "api" / "resource_center.py"
MARKS_ENTRY = APP / "public" / "js" / "eduedge_marks_entry" / "EduEdgeMarksEntry.vue"
RESULT_ANALYTICS = APP / "public" / "js" / "eduedge_result_analytics" / "EduEdgeResultAnalytics.vue"


RESOURCE_PAGES = {
	"eduedge_assessment_plans": ("eduedge-assessment-plans", "assessment_plans"),
	"eduedge_assessment_results": ("eduedge-assessment-results", "assessment_results"),
	"eduedge_result_profiles": ("eduedge-result-profiles", "result_profiles"),
	"eduedge_results_audit": ("eduedge-results-audit", "result_audit"),
}


class TestAssessmentEdgeSuitePagesContract(unittest.TestCase):
	def test_four_record_pages_use_shared_edgesuite_resource_center(self):
		for directory, (page_name, resource_key) in RESOURCE_PAGES.items():
			page_dir = APP / "eduedge" / "page" / directory
			self.assertTrue((page_dir / "__init__.py").exists())
			js = (page_dir / f"{directory}.js").read_text()
			json_text = (page_dir / f"{directory}.json").read_text()
			self.assertIn("registerEduEdgeResourcePage", js)
			self.assertIn(f'pageName: "{page_name}"', js)
			self.assertIn(f'resourceKey: "{resource_key}"', js)
			self.assertIn(f'"name": "{page_name}"', json_text)

	def test_marks_entry_and_analytics_are_edgesuite_vue_pages(self):
		for component in (MARKS_ENTRY, RESULT_ANALYTICS):
			text = component.read_text()
			for required in (
				"EdgeAppShell",
				"EdgePageLayout",
				"EdgePageHeader",
				"EdgeFilterBar",
				"EdgeDashboardLayout",
				"EdgeStatCard",
			):
				self.assertIn(required, text)
			style = text.split("<style scoped>", 1)[1].split("</style>", 1)[0]
			self.assertNotRegex(style, re.compile(r"#[0-9a-fA-F]{3,8}\\b"))
			self.assertNotIn("!important", style)

	def test_assessment_resource_contracts_exist(self):
		text = RESOURCE_CENTER.read_text()
		for key in ("assessment_plans", "assessment_results", "result_profiles", "result_audit"):
			self.assertIn(f'"{key}": {{', text)
		self.assertIn('"create_route": "/app/eduedge-marks-entry"', text)
		self.assertIn('"read_only": True', text)

	def test_navigation_and_product_menu_use_only_eduedge_routes_for_six_pages(self):
		edge_routes = (
			"/app/eduedge-assessment-plans",
			"/app/eduedge-marks-entry",
			"/app/eduedge-assessment-results",
			"/app/eduedge-result-profiles",
			"/app/eduedge-result-analytics",
			"/app/eduedge-results-audit",
		)
		for path in (NAVIGATION, PRODUCT_MENU):
			text = path.read_text()
			for route in edge_routes:
				self.assertIn(route, text)

	def test_marks_entry_uses_explicit_save_not_keystroke_network_calls(self):
		text = MARKS_ENTRY.read_text()
		self.assertIn("Save Row", text)
		self.assertIn("@input=\"markDirty(row)\"", text)
		self.assertIn("save_marks_entry", text)
		self.assertNotIn('@input="saveRow(row)"', text)


if __name__ == "__main__":
	unittest.main()
