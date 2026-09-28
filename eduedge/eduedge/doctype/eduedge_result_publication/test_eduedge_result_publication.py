from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEduEdgeResultPublication(FrappeTestCase):
	def _publication(self):
		return frappe.get_doc(
			{
				"doctype": "EduEdge Result Publication",
				"status": "Approved",
			}
		)

	def test_new_publication_cannot_prepopulate_workflow_state(self):
		unsafe_values = (
			{"status": "Published"},
			{"status": "Draft", "approved_by": "Administrator"},
			{
				"status": "Draft",
				"result_profile_config_hash": "injected-hash",
				"result_profile_config_json": "{}",
			},
		)
		for values in unsafe_values:
			with self.subTest(values=values):
				doc = frappe.get_doc(
					{
						"doctype": "EduEdge Result Publication",
						**values,
					}
				)
				doc.set("__islocal", True)
				with self.assertRaises(frappe.ValidationError):
					doc._validate_server_managed_change()

	def test_new_revision_can_receive_source_frozen_profile_config(self):
		doc = frappe.get_doc(
			{
				"doctype": "EduEdge Result Publication",
				"status": "Draft",
				"supersedes_publication": "PUB-OLD",
				"result_profile": "PROFILE-1",
				"result_profile_config_hash": "source-hash",
				"result_profile_config_json": "{}",
			}
		)
		doc.set("__islocal", True)
		doc._validate_server_managed_change()

	def test_direct_server_managed_change_is_blocked(self):
		doc = self._publication()
		with (
			patch.object(doc, "is_new", return_value=False),
			patch.object(
				doc,
				"has_value_changed",
				side_effect=lambda fieldname: fieldname == "status",
			),
		):
			with self.assertRaises(frappe.ValidationError):
				doc._validate_server_managed_change()

	def test_governed_transition_allows_server_managed_change(self):
		doc = self._publication()
		flag = "in_eduedge_result_publication_transition"
		previous = frappe.flags.get(flag)
		frappe.flags[flag] = True
		try:
			with (
				patch.object(doc, "is_new", return_value=False),
				patch.object(doc, "has_value_changed", return_value=True),
			):
				doc._validate_server_managed_change()
		finally:
			if previous is None:
				frappe.flags.pop(flag, None)
			else:
				frappe.flags[flag] = previous
