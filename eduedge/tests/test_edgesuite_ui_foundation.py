from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEdgeSuiteUIFoundation(unittest.TestCase):
	def test_launcher_opens_edgesuite_home(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"route": "/app/eduedge-home"', hooks)

	def test_every_product_page_loader_loads_edgesuite_first(self):
		page_root = APP / "eduedge" / "page"
		for path in page_root.glob("*/*.js"):
			with self.subTest(path=path):
				source = path.read_text()
				bundle_match = re.search(r'frappe\.require\("(eduedge_[^"]+\.bundle\.js)"', source)
				if not bundle_match:
					continue
				bundle_name = bundle_match.group(1)
				self.assertIn("edgeui.bundle.js", source)
				self.assertLess(source.index("edgeui.bundle.js"), source.index(bundle_name))
				self.assertIn("window.EdgeSuiteUI", source)
				self.assertIn("createEdgeApp", source)
				self.assertIn("EdgeAppShell", source)

	def test_root_product_pages_use_edge_app_shell(self):
		vue_root = APP / "public" / "js"
		for path in vue_root.glob("eduedge_*/*.vue"):
			with self.subTest(path=path):
				source = path.read_text()
				self.assertIn("<EdgeAppShell", source)
				self.assertNotIn('from "edgesuite_ui', source)
				self.assertNotIn("from 'edgesuite_ui", source)

	def test_home_exposes_branch_context_and_product_navigation(self):
		home = (APP / "public" / "js" / "eduedge_home" / "EduEdgeHome.vue").read_text()
		self.assertIn("current_branch", home)
		self.assertIn("allowed_branches", home)
		self.assertIn("switch_school_branch", home)
		self.assertIn("EDUEDGE_MENU_ITEMS", home)


if __name__ == "__main__":
	unittest.main()
