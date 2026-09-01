from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
ROUTE_PATTERN = re.compile(r'"(/app/eduedge-[a-z0-9-]+)"')


class TestReleaseNavigationParityContract(unittest.TestCase):
	def test_every_sidebar_business_route_exists_in_access_manifest_and_product_menu(self):
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		menu_block = navigation.split("export function buildEduEdgeMenuItems()", 1)[1].split(
			"export const EDUEDGE_MENU_ITEMS", 1
		)[0]
		sidebar_routes = set(ROUTE_PATTERN.findall(menu_block))
		self.assertGreaterEqual(len(sidebar_routes), 35, "Expected the complete EduEdge business navigation surface")

		access = (APP / "access_control.py").read_text(encoding="utf-8")
		product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
		product_menu_hardening = (
			APP / "public" / "js" / "eduedge_product_menu_hardening.bundle.js"
		).read_text(encoding="utf-8")
		product_surface = f"{product_menu}\n{product_menu_hardening}"

		missing_access = sorted(route for route in sidebar_routes if f'"{route}"' not in access)
		missing_product = sorted(route for route in sidebar_routes if f'"{route}"' not in product_surface)
		self.assertEqual(missing_access, [], f"Sidebar routes missing from access manifest: {missing_access}")
		self.assertEqual(missing_product, [], f"Sidebar routes missing from EdgeSuite product menu: {missing_product}")

	def test_school_calendar_has_one_permission_authority_and_both_navigation_surfaces(self):
		route = "/app/eduedge-school-calendar"
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		hardening = (APP / "public" / "js" / "eduedge_product_menu_hardening.bundle.js").read_text(encoding="utf-8")
		self.assertIn(route, navigation)
		self.assertIn(route, access)
		self.assertIn(route, hardening)
		self.assertIn("eduedge_access_manifest", hardening)
		self.assertNotIn("frappe.get_roles", hardening)

	def test_global_menu_hardening_is_not_mistaken_for_a_page_vue_bundle(self):
		foundation_test = (APP / "tests" / "test_edgesuite_ui_foundation.py").read_text(encoding="utf-8")
		self.assertIn('"eduedge_product_menu_hardening.bundle.js"', foundation_test)
		self.assertIn("GLOBAL_DESK_BUNDLES", foundation_test)


if __name__ == "__main__":
	unittest.main()
