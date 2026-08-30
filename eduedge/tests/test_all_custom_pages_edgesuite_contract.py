from __future__ import annotations

from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
PAGE_ROOT = APP / "eduedge" / "page"


class TestAllCustomPagesEdgeSuiteContract(unittest.TestCase):
	def test_every_standard_eduedge_page_uses_shared_resource_center_or_edgesuite_loader(self):
		checked = []
		violations = []
		for page_dir in sorted(path for path in PAGE_ROOT.iterdir() if path.is_dir() and path.name.startswith("eduedge_")):
			json_path = page_dir / f"{page_dir.name}.json"
			js_path = page_dir / f"{page_dir.name}.js"
			if not json_path.exists():
				continue
			metadata = json.loads(json_path.read_text(encoding="utf-8"))
			if metadata.get("standard") != "Yes":
				continue
			checked.append(page_dir.name)
			if not js_path.exists():
				violations.append(f"{page_dir.name}: missing page loader")
				continue
			source = js_path.read_text(encoding="utf-8")
			uses_resource_center = "registerEduEdgeResourcePage" in source
			uses_edgesuite_loader = 'frappe.require("edgesuite_ui.bundle.js"' in source
			if not (uses_resource_center or uses_edgesuite_loader):
				violations.append(f"{page_dir.name}: no EdgeSuite UI loader or shared resource registration")
		self.assertGreaterEqual(len(checked), 35, "Expected the complete EduEdge custom page surface")
		self.assertEqual(violations, [], "\n".join(violations))

	def test_resource_center_pages_share_the_hardened_edgesuite_runtime(self):
		loader = (APP / "public" / "js" / "eduedge_resource_page_loader.bundle.js").read_text(encoding="utf-8")
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertIn("createEduEdgeResourceCenterApp", loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		component = (APP / "public" / "js" / "eduedge_resource_center" / "EduEdgeResourceCenter.vue").read_text(encoding="utf-8")
		for token in ("<EdgeAppShell", "<EdgePageLayout", "<EdgePageHeader", "<EdgeFilterBar"):
			self.assertIn(token, component)

	def test_native_full_forms_remain_explicit_advanced_handoffs_not_custom_shell_replacements(self):
		resource_bundle = (APP / "public" / "js" / "eduedge_resource_center.bundle.js").read_text(encoding="utf-8")
		self.assertIn("FULL_FORM_ROUTES", resource_bundle)
		self.assertIn('admissions: "/app/student-admission"', resource_bundle)
		self.assertIn('students: "/app/student"', resource_bundle)
		self.assertIn('programs: "/app/program"', resource_bundle)


if __name__ == "__main__":
	unittest.main()
