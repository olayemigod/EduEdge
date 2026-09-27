from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEduEdgeReportCardReview(FrappeTestCase):
	def _review(self, status: str = "Draft"):
		return frappe.get_doc(
			{
				"doctype": "EduEdge Report Card Review",
				"progression_status": status,
				"progression_recommendation": "Promote",
			}
		)

	def test_new_review_must_start_draft_without_audit_state(self):
		unsafe_values = (
			{"progression_status": "Recommended"},
			{"progression_status": "Approved"},
			{"progression_status": "Draft", "recommended_by": "Administrator"},
			{"progression_status": "Draft", "approved_by": "Administrator"},
		)
		for values in unsafe_values:
			with self.subTest(values=values):
				doc = frappe.get_doc(
					{
						"doctype": "EduEdge Report Card Review",
						"progression_recommendation": "Promote",
						**values,
					}
				)
				doc.set("__islocal", True)
				with self.assertRaises(frappe.ValidationError):
					doc._validate_workflow_state()

	def test_direct_workflow_audit_change_is_blocked(self):
		doc = self._review("Draft")
		with (
			patch.object(doc, "is_new", return_value=False),
			patch.object(
				doc,
				"has_value_changed",
				side_effect=lambda fieldname: fieldname == "recommended_by",
			),
		):
			with self.assertRaises(frappe.ValidationError):
				doc._validate_workflow_state()

	def test_recommended_review_content_requires_reopen(self):
		doc = self._review("Recommended")
		with (
			patch.object(doc, "is_new", return_value=False),
			patch.object(
				doc,
				"has_value_changed",
				side_effect=lambda fieldname: fieldname == "class_teacher_comment",
			),
			patch("frappe.db.get_value", return_value="Recommended"),
		):
			with self.assertRaises(frappe.ValidationError):
				doc._validate_workflow_state()

	def test_approved_review_recommendation_requires_reopen(self):
		doc = self._review("Approved")
		with (
			patch.object(doc, "is_new", return_value=False),
			patch.object(
				doc,
				"has_value_changed",
				side_effect=lambda fieldname: fieldname == "progression_recommendation",
			),
			patch("frappe.db.get_value", return_value="Approved"),
		):
			with self.assertRaises(frappe.ValidationError):
				doc._validate_workflow_state()

	def test_draft_review_content_remains_editable(self):
		doc = self._review("Draft")
		with (
			patch.object(doc, "is_new", return_value=False),
			patch.object(
				doc,
				"has_value_changed",
				side_effect=lambda fieldname: fieldname == "class_teacher_comment",
			),
			patch("frappe.db.get_value", return_value="Draft"),
		):
			doc._validate_workflow_state()

	def test_governed_transition_allows_workflow_changes(self):
		doc = self._review("Approved")
		flag = "in_eduedge_report_card_transition"
		previous = frappe.flags.get(flag)
		frappe.flags[flag] = True
		try:
			with (
				patch.object(doc, "is_new", return_value=False),
				patch.object(doc, "has_value_changed", return_value=True),
			):
				doc._validate_workflow_state()
		finally:
			if previous is None:
				frappe.flags.pop(flag, None)
			else:
				frappe.flags[flag] = previous
