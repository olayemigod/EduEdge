from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TestEduEdgeDesktopLauncherContract(unittest.TestCase):
	def read(self, path: str) -> str:
		return (ROOT / path).read_text(encoding="utf-8")

	def test_apps_screen_declares_eduedge_home_as_relative_desk_route(self):
		hooks = self.read("eduedge/hooks.py")

		self.assertIn('"name": "eduedge"', hooks)
		self.assertIn('"title": "EduEdge"', hooks)
		self.assertIn('"route": "/desk/eduedge-home"', hooks)

	def test_desktop_launcher_hardening_is_globally_loaded(self):
		hooks = self.read("eduedge/hooks.py")

		self.assertIn('"eduedge_product_menu_hardening.bundle.js"', hooks)

	def test_legacy_and_apps_desktop_icons_open_home_in_same_tab(self):
		script = self.read("eduedge/public/js/eduedge_product_menu_hardening.bundle.js")

		for contract in (
			'const EDUEDGE_DESKTOP_HOME_ROUTE = "/desk/eduedge-home";',
			'const EDUEDGE_DESKTOP_LABEL = "EduEdge";',
			'a.desktop-icon[data-id="EduEdge"]',
			'anchor.setAttribute("href", EDUEDGE_DESKTOP_HOME_ROUTE)',
			'anchor.removeAttribute("target")',
			'window.location.assign(EDUEDGE_DESKTOP_HOME_ROUTE)',
			'document.addEventListener("click", handleEduEdgeDesktopLauncherClick, true)',
			'window.EduEdgeDesktopLauncher = Object.freeze',
		):
			self.assertIn(contract, script)

		self.assertNotIn('frappe.set_route("eduedge-home")', script)
		self.assertNotIn('window.open(', script)
		self.assertNotIn('target", "_blank"', script)

	def test_modified_clicks_keep_normal_browser_behavior(self):
		script = self.read("eduedge/public/js/eduedge_product_menu_hardening.bundle.js")

		self.assertIn("event.button === 0", script)
		self.assertIn("!event.metaKey", script)
		self.assertIn("!event.ctrlKey", script)
		self.assertIn("!event.shiftKey", script)
		self.assertIn("!event.altKey", script)


if __name__ == "__main__":
	unittest.main()
