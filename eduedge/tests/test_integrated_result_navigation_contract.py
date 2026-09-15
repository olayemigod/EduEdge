from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestIntegratedResultNavigationContract(unittest.TestCase):
	def test_result_surfaces_are_exposed_in_sidebar_and_product_menu(self):
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		for route in (
			"/app/eduedge-report-cards",
			"/app/eduedge-result-broadsheet",
			"/app/eduedge-result-intelligence",
		):
			self.assertIn(route, navigation)
			self.assertIn(route, product_menu)

	def test_result_surfaces_remain_server_permission_gated(self):
		access = (APP / "access_control.py").read_text()
		self.assertIn('"/app/eduedge-report-cards"', access)
		self.assertIn('"/app/eduedge-result-broadsheet"', access)
		self.assertIn('"/app/eduedge-result-intelligence"', access)

	def test_smart_mark_entry_is_wired_without_replacing_native_result_truth(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"Assessment Result Tool": "public/js/education/assessment_result_tool.js"', hooks)
		self.assertIn("eduedge_mark_entry.css", hooks)
		api = (APP / "api" / "mark_entry.py").read_text()
		self.assertIn("get_assessment_result_doc", api)
		self.assertNotIn("EduEdge Mark", api)


if __name__ == "__main__":
	unittest.main()
