from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
NAVIGATION = APP / "public" / "js" / "eduedge_ui" / "navigation.js"
ACCESS_CONTROL = APP / "access_control.py"


ASSESSMENT_ROUTES = (
	"/app/eduedge-assessment-operations",
	"/app/eduedge-assessment-plans",
	"/app/eduedge-marks-entry",
	"/app/eduedge-assessment-results",
	"/app/eduedge-result-profiles",
	"/app/eduedge-report-cards",
	"/app/eduedge-result-analytics",
	"/app/eduedge-results-audit",
)


class TestAssessmentNavigationContract(unittest.TestCase):
	def test_assessment_menu_is_complete_and_ordered(self):
		text = NAVIGATION.read_text()
		labels = (
			"Assessment Operations",
			"Assessment Plans",
			"Marks Entry",
			"Assessment Results",
			"Result Profiles",
			"Report Cards",
			"Result Analytics",
			"Results Audit",
		)
		positions = [text.index(f'__("{label}")') for label in labels]
		self.assertEqual(positions, sorted(positions))
		for route in ASSESSMENT_ROUTES:
			self.assertIn(route, text)

	def test_assessment_routes_are_permission_gated(self):
		text = ACCESS_CONTROL.read_text()
		self.assertIn('"assessment_plan": "Assessment Plan"', text)
		self.assertIn('"assessment_result": "Assessment Result"', text)
		self.assertIn('"result_profile": "EduEdge Result Profile"', text)
		self.assertIn('"result_publication_log": "EduEdge Result Publication Log"', text)
		for route in ASSESSMENT_ROUTES:
			self.assertIn(route, text)

	def test_governance_only_result_routes_are_role_restricted(self):
		text = ACCESS_CONTROL.read_text()
		for role in (
			"System Manager",
			"EduEdge Administrator",
			"School Administrator",
			"Academic Administrator",
		):
			self.assertIn(role, text)
		for route in (
			"/app/eduedge-result-profiles",
			"/app/eduedge-result-analytics",
			"/app/eduedge-results-audit",
		):
			self.assertIn(route, text)
		self.assertIn("roles.intersection(RESULT_GOVERNANCE_ROLES)", text)

	def test_sidebar_does_not_fall_back_to_native_frappe_assessment_pages(self):
		text = NAVIGATION.read_text()
		assessment_block = text.split('menuGroup("assessment-results"', 1)[1].split('menuGroup("cbt-delivery"', 1)[0]
		for native_route in (
			'"/app/assessment-plan"',
			'"/app/assessment-result-tool"',
			'"/app/assessment-result"',
			'"/app/assessment-result/view/report"',
			'"/app/eduedge-result-publication-log"',
		):
			self.assertNotIn(native_route, assessment_block)


if __name__ == "__main__":
	unittest.main()
