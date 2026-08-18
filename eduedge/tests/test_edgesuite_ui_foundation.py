from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
GLOBAL_DESK_BUNDLES = {
	"eduedge_product_menu.bundle.js",
	"eduedge_profile_identity.bundle.js",
	"eduedge_shell_identity.bundle.js",
	"eduedge_resource_page_loader.bundle.js",
	"eduedge_terminology.bundle.js",
	"eduedge_question_rich_text.bundle.js",
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
				self.assertIn("edgesuite_ui.bundle.js", source)
				self.assertNotIn('frappe.require("edgeui.bundle.js"', source)
				self.assertLess(source.index("edgesuite_ui.bundle.js"), source.index(bundle_name))
				self.assertRegex(source, r"window\.createEduEdge[A-Za-z]+App")
				self.assertNotIn("runtime.createEdgeApp", source)

	def test_runtime_resolver_checks_both_supported_namespaces(self):
		factory = (APP / "public" / "js" / "eduedge_ui" / "app_factory.js").read_text()
		self.assertIn("export function resolveEdgeSuiteRuntime", factory)
		self.assertIn("[window.EdgeSuiteUI, window.EdgeUI].find", factory)
		self.assertIn('typeof candidate?.install === "function"', factory)
		self.assertIn("componentNames.every", factory)
		self.assertIn('resolveEdgeSuiteRuntime(["EdgeAppShell"])', factory)
		self.assertNotIn("window.EdgeSuiteUI || window.EdgeUI", factory)

	def test_current_qa_pages_defer_definitive_runtime_validation_to_factory(self):
		loader_paths = (
			"eduedge_academic_foundation/eduedge_academic_foundation.js",
			"eduedge_academic_operations/eduedge_academic_operations.js",
			"eduedge_programs/eduedge_programs.js",
			"eduedge_program_offerings/eduedge_program_offerings.js",
			"eduedge_my_profile/eduedge_my_profile.js",
			"eduedge_institution_profile/eduedge_institution_profile.js",
		)
		for relative_path in loader_paths:
			with self.subTest(path=relative_path):
				source = (APP / "eduedge" / "page" / relative_path).read_text()
				self.assertNotIn("window.EdgeSuiteUI || window.EdgeUI", source)
				self.assertNotIn("runtime?.install", source)
				self.assertIn("edgesuite_ui.bundle.js", source)
				self.assertRegex(source, r"window\.createEduEdge[A-Za-z]+App")

	def test_product_bundles_create_apps_with_the_product_vue_runtime(self):
		bundle_root = APP / "public" / "js"
		factory = (bundle_root / "eduedge_ui" / "app_factory.js").read_text()
		self.assertRegex(factory, r'import \{[^}]*createApp[^}]*\} from "vue"')
		self.assertIn("runtime.install(app)", factory)
		self.assertIn("resolveEdgeSuiteRuntime", factory)

		for path in bundle_root.glob("eduedge_*.bundle.js"):
			if path.name in GLOBAL_DESK_BUNDLES:
				continue
			with self.subTest(path=path):
				source = path.read_text()
				self.assertIn('from "./eduedge_ui/app_factory"', source)
				self.assertIn("createEduEdgeApp(", source)
				self.assertRegex(source, r"window\.createEduEdge[A-Za-z]+App")

	def test_root_product_pages_use_edge_app_shell(self):
		bundle_root = APP / "public" / "js"
		for bundle in bundle_root.glob("eduedge_*.bundle.js"):
			if bundle.name in GLOBAL_DESK_BUNDLES:
				continue
			bundle_source = bundle.read_text()
			match = re.search(r'import\s+\w+\s+from\s+"(\./[^\"]+\.vue)"', bundle_source)
			if not match:
				continue
			path = bundle_root / match.group(1).removeprefix("./")
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
