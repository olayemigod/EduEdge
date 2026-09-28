from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	get_archived_report_card_pdf,
	has_archived_report_card_file_permission,
	resolve_report_card_pdf,
)


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


	def test_incomplete_issued_pdf_metadata_fails_closed(self):
		payload = {"issue_record": {"name": "EDU-RCI-TEST"}}
		archive = frappe._dict(
			{"pdf_sha256": "abc", "pdf_filename": "", "pdf_size_bytes": 123}
		)
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("eduedge.education.report_card_issues.render_report_card_pdf") as render,
		):
			with self.assertRaises(frappe.ValidationError):
				resolve_report_card_pdf(payload)
			render.assert_not_called()

	def test_legacy_issue_without_archive_metadata_keeps_dynamic_fallback(self):
		payload = {"issue_record": {"name": "EDU-RCI-LEGACY"}}
		archive = frappe._dict(
			{"pdf_sha256": None, "pdf_filename": None, "pdf_size_bytes": None}
		)
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch(
				"eduedge.education.report_card_issues.render_report_card_pdf",
				return_value=b"legacy-pdf",
			) as render,
		):
			self.assertEqual(resolve_report_card_pdf(payload), b"legacy-pdf")
			render.assert_called_once_with(payload)

	def test_archived_pdf_retrieval_uses_exact_filename_and_verifies_bytes(self):
		pdf_bytes = b"%PDF-1.4 archived report"
		filename = "Report Card EDU-RCI-TEST.pdf"
		archive = frappe._dict(
			{
				"pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
				"pdf_filename": filename,
				"pdf_size_bytes": len(pdf_bytes),
			}
		)
		file_row = frappe._dict({"name": "FILE-1", "file_name": filename, "file_type": "PDF"})
		file_doc = MagicMock()
		file_doc.get_content.return_value = pdf_bytes
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all", return_value=[file_row]) as get_all,
			patch("frappe.get_doc", return_value=file_doc),
		):
			self.assertEqual(get_archived_report_card_pdf("EDU-RCI-TEST"), pdf_bytes)
			self.assertEqual(
				get_all.call_args.kwargs["filters"]["file_name"],
				filename,
			)

	def test_report_card_issue_file_permissions_block_creation_and_mutation(self):
		file_doc = frappe._dict({"attached_to_doctype": ISSUE_DOCTYPE})
		self.assertFalse(has_archived_report_card_file_permission(file_doc, ptype="create"))
		self.assertFalse(has_archived_report_card_file_permission(file_doc, ptype="write"))
		self.assertFalse(has_archived_report_card_file_permission(file_doc, ptype="delete"))
		self.assertTrue(has_archived_report_card_file_permission(file_doc, ptype="read"))
