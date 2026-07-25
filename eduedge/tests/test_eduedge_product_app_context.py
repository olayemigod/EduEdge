from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe

from eduedge.api.product_context import get_product_availability


class TestEduEdgeProductAppContext(unittest.TestCase):
	def app_path(self, *parts: str) -> Path:
		return Path(frappe.get_app_path("eduedge", *parts))

	def test_provider_returns_stable_descriptor_for_authorised_user(self):
		with (
			patch.object(frappe, "session", SimpleNamespace(user="teacher@example.com")),
			patch(
				"eduedge.api.product_context.build_access_manifest",
				return_value={"can_access_eduedge": True},
			),
		):
			product = get_product_availability()
		self.assertEqual(product["key"], "eduedge")
		self.assertEqual(product["label"], "EduEdge")
		self.assertEqual(product["home_route"], "/app/eduedge-home")
		self.assertIn("/app/eduedge*", product["route_patterns"])

	def test_provider_hides_product_without_final_access(self):
		with (
			patch.object(frappe, "session", SimpleNamespace(user="restricted@example.com")),
			patch(
				"eduedge.api.product_context.build_access_manifest",
				return_value={"can_access_eduedge": False},
			),
		):
			self.assertIsNone(get_product_availability())

	def test_guest_never_receives_product_descriptor(self):
		with patch.object(frappe, "session", SimpleNamespace(user="Guest")):
			self.assertIsNone(get_product_availability())

	def test_menu_uses_canonical_runtime_and_stable_product_key(self):
		menu = self.app_path("public", "js", "eduedge_product_menu.bundle.js").read_text()
		self.assertIn('EDUEDGE_PRODUCT_KEY = "eduedge"', menu)
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', menu)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', menu)
		self.assertIn("product_key: EDUEDGE_PRODUCT_KEY", menu)
		self.assertIn('home_route: "/app/eduedge-home"', menu)


if __name__ == "__main__":
	unittest.main()
