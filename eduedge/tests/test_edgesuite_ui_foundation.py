from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
GLOBAL_DESK_BUNDLES = {
	"eduedge_product_menu.bundle.js",
	"eduedge_shell_identity.bundle.js",
	"eduedge_resource_page_loader.bundle.js",
	"eduedge_terminology.bundle.js",
}


class TestEdgeSuiteUIFoundation(unittest.TestCase):
	def test_launcher_opens_edgesuite_home_inside_current_desk_tab(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"route": "/desk/eduedge-home"', hooks)
		self.assertNotIn('"route": "/app/eduedge-home"', hooks)
		self.assertNotIn('"target": "_blank"', hooks)

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
				self.assertIn("runtime?.install", source)
				self.assertIn("EdgeAppShell", source)
				self.assertRegex(source, r"window\.createEduEdge[A-Za-z]+App")
				self.assertNotIn("runtime.createEdgeApp", source)

	def test_product_bundles_create_apps_with_the_product_vue_runtime(self):
		bundle_root = APP / "public" / "js"
		factory = (bundle_root / "eduedge_ui" / "app_factory.js").read_text()
		self.assertIn('import { createApp } from "vue"', factory)
		self.assertIn("runtime.install(app)", factory)
		self.assertIn("runtime?.components?.EdgeAppShell", factory)

		for path in bundle_root.glob("eduedge_*.bundle.js"):
			if path.name in GLOBAL_DESK_BUNDLES:
				continue
			with self.subTest(path=path):
				source = path.read_text()
				self.assertIn('from "./eduedge_ui/app_factory"', source)
				self.assertIn("createEduEdgeApp(", source)
				self.assertRegex(source, r"window\.createEduEdge[A-Za-z]+App")

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
