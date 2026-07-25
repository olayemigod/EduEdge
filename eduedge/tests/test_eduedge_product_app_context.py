from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEduEdgeProductAppContext(unittest.TestCase):
	def test_provider_uses_final_access_manifest_and_stable_descriptor(self):
		source = (APP / "api" / "product_context.py").read_text(encoding="utf-8")
		for expected in (
			"build_access_manifest",
			'frappe.session.user == "Guest"',
			'not manifest.get("can_access_eduedge")',
			'"key": "eduedge"',
			'"label": "EduEdge"',
			'"home_route": "/app/eduedge-home"',
			'"/app/eduedge*"',
		):
			self.assertIn(expected, source)
		self.assertNotIn("installed_apps", source)
		self.assertNotIn("System Manager", source)

	def test_menu_uses_canonical_runtime_and_stable_product_key(self):
		menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(
			encoding="utf-8"
		)
		self.assertIn('EDUEDGE_PRODUCT_KEY = "eduedge"', menu)
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', menu)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', menu)
		self.assertIn("product_key: EDUEDGE_PRODUCT_KEY", menu)
		self.assertIn('home_route: "/app/eduedge-home"', menu)

	def test_home_loader_uses_canonical_runtime_before_product_bundle(self):
		loader = (
			APP / "eduedge" / "page" / "eduedge_home" / "eduedge_home.js"
		).read_text(encoding="utf-8")
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertLess(
			loader.index('frappe.require("edgesuite_ui.bundle.js"'),
			loader.index('frappe.require("eduedge_home.bundle.js"'),
		)


if __name__ == "__main__":
	unittest.main()
