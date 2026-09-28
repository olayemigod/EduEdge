from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from eduedge.api.report_cards import _get_published_publication_lineage
from eduedge.education.result_verification import _verify_issue_pdf_archive

from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	get_archived_report_card_pdf,
	get_issued_payload_by_name,
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

	def _publication_row(self, name, version, supersedes=None, **overrides):
		values = {
			"name": name,
			"title": name,
			"school_branch": "BRANCH-1",
			"student_group": "GROUP-1",
			"academic_year": "2026-2027",
			"academic_term": "TERM-1",
			"assessment_group": None,
			"result_profile": "PROFILE-1",
			"result_mode": "Terminal",
			"publication_version": version,
			"supersedes_publication": supersedes,
			"status": "Published",
			"report_card_ready": 1,
			"published_on": f"2026-09-{10 + version:02d} 10:00:00",
		}
		values.update(overrides)
		return frappe._dict(values)

	def test_publication_lineage_follows_only_explicit_supersession_chain(self):
		v1 = self._publication_row("PUB-1", 1)
		v2 = self._publication_row("PUB-2", 2, "PUB-1")
		v3 = self._publication_row("PUB-3", 3, "PUB-2")
		rows = {row.name: row for row in (v1, v2, v3)}

		def get_children(_doctype, filters=None, **kwargs):
			parent = (filters or {}).get("supersedes_publication")
			return {
				"PUB-1": [v2],
				"PUB-2": [v3],
				"PUB-3": [],
			}.get(parent, [])

		with (
			patch("eduedge.api.report_cards.get_published_publication", return_value=v2),
			patch("frappe.db.get_value", side_effect=lambda _dt, name, *_args, **_kwargs: rows.get(name)),
			patch("frappe.get_all", side_effect=get_children) as get_all,
		):
			lineage = _get_published_publication_lineage("PUB-2")

		self.assertEqual([row.name for row in lineage], ["PUB-1", "PUB-2", "PUB-3"])
		for call in get_all.call_args_list:
			filters = call.kwargs["filters"]
			self.assertIn("supersedes_publication", filters)
			self.assertEqual(filters["status"], "Published")
			self.assertEqual(filters["report_card_ready"], 1)

	def test_publication_lineage_rejects_multiple_published_successors(self):
		v1 = self._publication_row("PUB-1", 1)
		v2a = self._publication_row("PUB-2A", 2, "PUB-1")
		v2b = self._publication_row("PUB-2B", 2, "PUB-1")
		with (
			patch("eduedge.api.report_cards.get_published_publication", return_value=v1),
			patch("frappe.db.get_value", return_value=v1),
			patch("frappe.get_all", return_value=[v2a, v2b]),
		):
			with self.assertRaises(frappe.ValidationError):
				_get_published_publication_lineage("PUB-1")

	def test_publication_lineage_rejects_scope_drift(self):
		v1 = self._publication_row("PUB-1", 1)
		v2 = self._publication_row("PUB-2", 2, "PUB-1", student_group="GROUP-OTHER")
		with (
			patch("eduedge.api.report_cards.get_published_publication", return_value=v1),
			patch("frappe.db.get_value", return_value=v1),
			patch("frappe.get_all", return_value=[v2]),
		):
			with self.assertRaises(frappe.ValidationError):
				_get_published_publication_lineage("PUB-1")

	def test_exact_issue_payload_loads_independently_of_current_review_state(self):
		payload = {"student": {"student_name": "Archive Student"}, "issue": {"issue_version": 1}}
		payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
		row = frappe._dict(
			{
				"name": "EDU-RCI-TEST",
				"issue_version": 1,
				"payload_hash": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
				"payload_json": payload_json,
				"verification_token": "token",
				"pdf_sha256": "a" * 64,
				"pdf_filename": "Report Card EDU-RCI-TEST.pdf",
				"pdf_size_bytes": 100,
			}
		)
		with patch("frappe.db.get_value", return_value=row), patch(
			"eduedge.education.report_card_issues.build_issue_verification",
			return_value={"issue": row.name},
		):
			loaded = get_issued_payload_by_name(row.name)
		self.assertEqual(loaded["issue_record"]["name"], row.name)
		self.assertEqual(loaded["issue_record"]["issue_version"], 1)
		self.assertEqual(loaded["student"]["student_name"], "Archive Student")

	def test_exact_issue_payload_hash_tampering_fails_closed(self):
		row = frappe._dict(
			{
				"name": "EDU-RCI-TAMPERED",
				"issue_version": 1,
				"payload_hash": "0" * 64,
				"payload_json": '{"student":{"student_name":"Tampered"}}',
				"verification_token": "token",
				"pdf_sha256": None,
				"pdf_filename": None,
				"pdf_size_bytes": None,
			}
		)
		with patch("frappe.db.get_value", return_value=row):
			with self.assertRaises(frappe.ValidationError):
				get_issued_payload_by_name(row.name)

	def test_public_verification_preserves_true_legacy_issue_without_pdf_archive(self):
		row = frappe._dict(
			{
				"name": "EDU-RCI-LEGACY",
				"pdf_sha256": None,
				"pdf_filename": None,
				"pdf_size_bytes": None,
			}
		)
		with patch("eduedge.education.report_card_issues.get_archived_report_card_pdf") as archive:
			self.assertTrue(_verify_issue_pdf_archive(row))
			archive.assert_not_called()

	def test_public_verification_rejects_partial_pdf_archive_metadata(self):
		row = frappe._dict(
			{
				"name": "EDU-RCI-PARTIAL",
				"pdf_sha256": "a" * 64,
				"pdf_filename": "",
				"pdf_size_bytes": 100,
			}
		)
		with patch("eduedge.education.report_card_issues.get_archived_report_card_pdf") as archive:
			self.assertFalse(_verify_issue_pdf_archive(row))
			archive.assert_not_called()

	def test_public_verification_requires_archived_pdf_integrity(self):
		row = frappe._dict(
			{
				"name": "EDU-RCI-ARCHIVED",
				"pdf_sha256": "a" * 64,
				"pdf_filename": "Report Card EDU-RCI-ARCHIVED.pdf",
				"pdf_size_bytes": 100,
			}
		)
		with patch(
			"eduedge.education.report_card_issues.get_archived_report_card_pdf",
			return_value=b"%PDF-1.4",
		) as archive:
			self.assertTrue(_verify_issue_pdf_archive(row))
			archive.assert_called_once_with(row.name)
		with patch(
			"eduedge.education.report_card_issues.get_archived_report_card_pdf",
			side_effect=frappe.ValidationError("tampered"),
		):
			self.assertFalse(_verify_issue_pdf_archive(row))

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
		file_row = frappe._dict({"name": "FILE-1", "file_name": filename, "file_type": "PDF", "owner": "Administrator"})
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

	def test_archived_pdf_non_system_owner_fails_closed(self):
		pdf_bytes = b"%PDF-1.4 official"
		archive = frappe._dict(
			{
				"pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
				"pdf_filename": "Report Card EDU-RCI-TEST.pdf",
				"pdf_size_bytes": len(pdf_bytes),
			}
		)
		file_row = frappe._dict(
			{
				"name": "FILE-1",
				"file_name": archive.pdf_filename,
				"file_type": "PDF",
				"owner": "issuer@example.com",
			}
		)
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all", return_value=[file_row]),
		):
			with self.assertRaises(frappe.ValidationError):
				get_archived_report_card_pdf("EDU-RCI-TEST")

	def test_archived_pdf_tampering_fails_closed(self):
		expected_bytes = b"%PDF-1.4 official"
		archive = frappe._dict(
			{
				"pdf_sha256": hashlib.sha256(expected_bytes).hexdigest(),
				"pdf_filename": "Report Card EDU-RCI-TEST.pdf",
				"pdf_size_bytes": len(expected_bytes),
			}
		)
		file_row = frappe._dict(
			{
				"name": "FILE-1",
				"file_name": archive.pdf_filename,
				"file_type": "PDF",
				"owner": "Administrator",
			}
		)
		file_doc = MagicMock()
		file_doc.get_content.return_value = b"%PDF-1.4 tampered"
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all", return_value=[file_row]),
			patch("frappe.get_doc", return_value=file_doc),
		):
			with self.assertRaises(frappe.ValidationError):
				get_archived_report_card_pdf("EDU-RCI-TEST")

	def test_report_card_issue_file_permissions_follow_issue_access(self):
		file_doc = frappe._dict(
			{
				"attached_to_doctype": ISSUE_DOCTYPE,
				"attached_to_name": "EDU-RCI-TEST",
			}
		)
		for ptype in ("create", "write", "delete", "share"):
			with self.subTest(ptype=ptype):
				self.assertFalse(has_archived_report_card_file_permission(file_doc, ptype=ptype))
		with patch("frappe.has_permission", return_value=True) as has_permission:
			self.assertTrue(has_archived_report_card_file_permission(file_doc, ptype="read", user="reader@example.com"))
			has_permission.assert_called_once_with(
				ISSUE_DOCTYPE,
				ptype="read",
				doc="EDU-RCI-TEST",
				user="reader@example.com",
				print_logs=False,
			)
		with patch("frappe.has_permission", return_value=False):
			self.assertFalse(has_archived_report_card_file_permission(file_doc, ptype="read", user="blocked@example.com"))
