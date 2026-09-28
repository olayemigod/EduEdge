from __future__ import annotations

import hashlib
import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from eduedge.api.report_card_archive_audit import get_report_card_archive_integrity
from eduedge.api.report_cards import _get_published_publication_lineage
from eduedge.education.result_verification import (
	_verify_issue_pdf_archive,
	verify_issued_report_card,
)

from eduedge.maintenance.report_card_restore import (
	assert_report_card_restore_integrity,
	verify_report_card_restore_integrity,
)

from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	get_archived_report_card_pdf,
	get_issued_payload_by_name,
	inspect_report_card_issue_integrity,
	inspect_report_card_pdf_archive,
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

	def test_public_verification_returns_invalid_when_archived_pdf_fails_integrity(self):
		payload_json = json.dumps({"student": {"student_name": "Archive Student"}})
		row = frappe._dict(
			{
				"name": "EDU-RCI-VERIFY",
				"result_publication": "PUB-1",
				"publication_version": 1,
				"report_card_review": "REVIEW-1",
				"issue_version": 1,
				"student": "STU-1",
				"student_name": "Archive Student",
				"school_branch": "BRANCH-1",
				"student_group": "GROUP-1",
				"academic_year": "2026-2027",
				"academic_term": "TERM-1",
				"result_mode": "Terminal",
				"result_profile": "PROFILE-1",
				"verification_token": "token",
				"payload_hash": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
				"payload_json": payload_json,
				"pdf_sha256": "a" * 64,
				"pdf_filename": "Report Card EDU-RCI-VERIFY.pdf",
				"pdf_size_bytes": 100,
				"issued_on": "2026-09-28 10:00:00",
			}
		)
		with (
			patch("frappe.db.get_value", return_value=row),
			patch(
				"eduedge.education.result_verification._verify_issue_pdf_archive",
				return_value=False,
			),
		):
			result = verify_issued_report_card(row.name, "token")
		self.assertFalse(result["valid"])
		self.assertEqual(result["status"], "Invalid")
		self.assertIn("PDF archive integrity", result["status_message"])

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

	def test_archive_inspector_preserves_true_legacy_issue(self):
		archive = frappe._dict(
			{"pdf_sha256": None, "pdf_filename": None, "pdf_size_bytes": None}
		)
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all") as get_all,
		):
			result = inspect_report_card_pdf_archive("EDU-RCI-LEGACY")
		self.assertEqual(result["status"], "Legacy")
		self.assertTrue(result["ok"])
		self.assertTrue(result["legacy"])
		get_all.assert_not_called()

	def test_archive_inspector_reports_missing_file(self):
		archive = frappe._dict(
			{
				"pdf_sha256": "a" * 64,
				"pdf_filename": "Report Card EDU-RCI-MISSING.pdf",
				"pdf_size_bytes": 100,
			}
		)
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all", return_value=[]),
		):
			result = inspect_report_card_pdf_archive("EDU-RCI-MISSING")
		self.assertEqual(result["status"], "Missing File")
		self.assertFalse(result["ok"])

	def test_archive_inspector_distinguishes_size_and_hash_mismatch(self):
		expected = b"%PDF-1.4 official"
		archive = frappe._dict(
			{
				"pdf_sha256": hashlib.sha256(expected).hexdigest(),
				"pdf_filename": "Report Card EDU-RCI-AUDIT.pdf",
				"pdf_size_bytes": len(expected),
			}
		)
		file_row = frappe._dict(
			{
				"name": "FILE-AUDIT",
				"file_name": archive.pdf_filename,
				"file_type": "PDF",
				"owner": "Administrator",
			}
		)
		file_doc = MagicMock()
		with (
			patch("frappe.db.get_value", return_value=archive),
			patch("frappe.get_all", return_value=[file_row]),
			patch("frappe.get_doc", return_value=file_doc),
		):
			file_doc.get_content.return_value = b"short"
			self.assertEqual(
				inspect_report_card_pdf_archive("EDU-RCI-AUDIT")["status"],
				"Size Mismatch",
			)
			file_doc.get_content.return_value = b"X" * len(expected)
			self.assertEqual(
				inspect_report_card_pdf_archive("EDU-RCI-AUDIT")["status"],
				"Hash Mismatch",
			)

	def test_issue_integrity_rejects_corrupt_payload_even_when_pdf_would_be_healthy(self):
		payload_json = json.dumps({"student": {"student_name": "Archive Student"}})
		row = frappe._dict(
			{
				"payload_hash": "0" * 64,
				"payload_json": payload_json,
			}
		)
		with (
			patch("frappe.db.get_value", return_value=row),
			patch("eduedge.education.report_card_issues.inspect_report_card_pdf_archive") as pdf,
		):
			result = inspect_report_card_issue_integrity("EDU-RCI-PAYLOAD-BAD")
		self.assertEqual(result["status"], "Payload Hash Mismatch")
		self.assertFalse(result["ok"])
		self.assertEqual(result["payload_status"], "Hash Mismatch")
		self.assertFalse(result["payload_ok"])
		self.assertEqual(result["pdf_status"], "Not Checked")
		pdf.assert_not_called()

	def test_issue_integrity_reports_healthy_payload_and_pdf_layers(self):
		payload_json = json.dumps({"student": {"student_name": "Archive Student"}})
		row = frappe._dict(
			{
				"payload_hash": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
				"payload_json": payload_json,
			}
		)
		pdf_result = {
			"issue": "EDU-RCI-HEALTHY",
			"status": "Healthy",
			"ok": True,
			"legacy": False,
			"detail": "PDF verified",
			"pdf_fingerprint": "A" * 16,
			"expected_size_bytes": 100,
			"actual_size_bytes": 100,
		}
		with (
			patch("frappe.db.get_value", return_value=row),
			patch(
				"eduedge.education.report_card_issues.inspect_report_card_pdf_archive",
				return_value=pdf_result,
			),
		):
			result = inspect_report_card_issue_integrity("EDU-RCI-HEALTHY")
		self.assertTrue(result["ok"])
		self.assertTrue(result["payload_ok"])
		self.assertTrue(result["pdf_ok"])
		self.assertEqual(result["payload_status"], "Healthy")
		self.assertEqual(result["pdf_status"], "Healthy")

	def test_archive_audit_endpoint_is_permission_aware_and_page_bounded(self):
		rows = [
			frappe._dict(
				{
					"name": f"ISSUE-{index}",
					"result_publication": "PUB-1",
					"publication_version": 1,
					"issue_version": index,
					"student": f"STU-{index}",
					"student_name": f"Student {index}",
					"school_branch": "BRANCH-1",
					"student_group": "GROUP-1",
					"issued_on": "2026-09-28 10:00:00",
					"pdf_sha256": "a" * 64,
					"pdf_filename": f"Report {index}.pdf",
					"pdf_size_bytes": 100,
				}
			)
			for index in (1, 2, 3)
		]

		def inspect(name):
			return {
				"status": "Healthy" if name == "ISSUE-1" else "Missing File",
				"ok": name == "ISSUE-1",
				"legacy": False,
				"detail": "checked",
				"pdf_fingerprint": "A" * 16,
				"expected_size_bytes": 100,
				"actual_size_bytes": 100 if name == "ISSUE-1" else None,
			}

		with (
			patch("eduedge.api.report_card_archive_audit._require_archive_auditor"),
			patch("eduedge.api.report_card_archive_audit._resolve_branch", return_value="BRANCH-1"),
			patch("frappe.get_list", return_value=rows) as get_list,
			patch("eduedge.api.report_card_archive_audit.inspect_report_card_issue_integrity", side_effect=inspect),
			patch("eduedge.api.report_card_archive_audit.get_allowed_school_branches", return_value=[]),
		):
			result = get_report_card_archive_integrity(branch="BRANCH-1", start=0, page_length=2)

		self.assertTrue(result["has_more"])
		self.assertEqual(len(result["rows"]), 2)
		self.assertEqual(result["summary"]["healthy"], 1)
		self.assertEqual(result["summary"]["needs_attention"], 1)
		self.assertEqual(get_list.call_args.kwargs["limit_page_length"], 3)
		self.assertEqual(get_list.call_args.kwargs["filters"]["school_branch"], "BRANCH-1")

	def test_archive_audit_filters_candidates_before_integrity_checks(self):
		rows = [
			frappe._dict(
				{
					"name": "ISSUE-1",
					"result_publication": "PUB-2",
					"publication_version": 2,
					"issue_version": 1,
					"student": "STU-9",
					"student_name": "Student Nine",
					"school_branch": "BRANCH-1",
					"student_group": "GROUP-1",
					"issued_on": "2026-09-28 10:00:00",
					"pdf_sha256": "a" * 64,
					"pdf_filename": "Report 1.pdf",
					"pdf_size_bytes": 100,
				}
			)
		]
		check = {
			"status": "Healthy",
			"ok": True,
			"legacy": False,
			"detail": "checked",
			"payload_status": "Healthy",
			"payload_ok": True,
			"payload_fingerprint": "B" * 16,
			"pdf_status": "Healthy",
			"pdf_ok": True,
			"pdf_fingerprint": "A" * 16,
			"expected_size_bytes": 100,
			"actual_size_bytes": 100,
		}
		with (
			patch("eduedge.api.report_card_archive_audit._require_archive_auditor"),
			patch("eduedge.api.report_card_archive_audit._resolve_branch", return_value="BRANCH-1"),
			patch("frappe.get_list", return_value=rows) as get_list,
			patch(
				"eduedge.api.report_card_archive_audit.inspect_report_card_issue_integrity",
				return_value=check,
			) as inspect,
			patch("eduedge.api.report_card_archive_audit.get_allowed_school_branches", return_value=[]),
			patch("eduedge.api.report_card_archive_audit.now_datetime", return_value="2026-09-28 17:30:00"),
		):
			result = get_report_card_archive_integrity(
				branch="BRANCH-1",
				publication="PUB-2",
				student="STU-9",
				search="Nine",
				start=0,
				page_length=10,
			)

		self.assertEqual(
			get_list.call_args.kwargs["filters"],
			{
				"school_branch": "BRANCH-1",
				"result_publication": "PUB-2",
				"student": "STU-9",
			},
		)
		self.assertEqual(
			get_list.call_args.kwargs["or_filters"],
			[
				["name", "like", "%Nine%"],
				["student", "like", "%Nine%"],
				["student_name", "like", "%Nine%"],
				["result_publication", "like", "%Nine%"],
			],
		)
		inspect.assert_called_once_with("ISSUE-1")
		self.assertEqual(result["filters"]["publication"], "PUB-2")
		self.assertEqual(result["filters"]["student"], "STU-9")
		self.assertEqual(result["filters"]["search"], "Nine")
		self.assertEqual(result["checked_on"], "2026-09-28 17:30:00")

	def test_restore_verifier_scans_all_issues_in_bounded_batches(self):
		pages = [
			[frappe._dict({"name": "ISSUE-1"}), frappe._dict({"name": "ISSUE-2"})],
			[frappe._dict({"name": "ISSUE-3"})],
		]
		checks = {
			"ISSUE-1": {
				"status": "Healthy",
				"ok": True,
				"legacy": False,
				"detail": "verified",
				"payload_status": "Healthy",
				"payload_fingerprint": "A" * 16,
				"pdf_status": "Healthy",
				"pdf_fingerprint": "B" * 16,
				"expected_size_bytes": 100,
				"actual_size_bytes": 100,
			},
			"ISSUE-2": {
				"status": "Legacy",
				"ok": True,
				"legacy": True,
				"detail": "pre-archive",
				"payload_status": "Healthy",
				"payload_fingerprint": "C" * 16,
				"pdf_status": "Legacy",
				"pdf_fingerprint": "",
				"expected_size_bytes": None,
				"actual_size_bytes": None,
			},
			"ISSUE-3": {
				"status": "Missing File",
				"ok": False,
				"legacy": False,
				"detail": "private file missing",
				"payload_status": "Healthy",
				"payload_fingerprint": "D" * 16,
				"pdf_status": "Missing File",
				"pdf_fingerprint": "E" * 16,
				"expected_size_bytes": 100,
				"actual_size_bytes": None,
			},
		}
		with (
			patch("frappe.get_all", side_effect=pages) as get_all,
			patch(
				"eduedge.maintenance.report_card_restore.inspect_report_card_issue_integrity",
				side_effect=lambda name: checks[name],
			) as inspect,
		):
			result = verify_report_card_restore_integrity(batch_size=2, max_problem_rows=10)

		self.assertEqual(result["status"], "FAIL")
		self.assertEqual(result["total_issues"], 3)
		self.assertEqual(result["healthy"], 1)
		self.assertEqual(result["legacy"], 1)
		self.assertEqual(result["problems"], 1)
		self.assertEqual(result["problem_rows"][0]["issue"], "ISSUE-3")
		self.assertFalse(result["problem_rows_truncated"])
		self.assertEqual(inspect.call_count, 3)
		self.assertEqual(get_all.call_args_list[0].kwargs["limit_start"], 0)
		self.assertEqual(get_all.call_args_list[0].kwargs["limit_page_length"], 2)
		self.assertEqual(get_all.call_args_list[1].kwargs["limit_start"], 2)

	def test_restore_verifier_bounds_problem_evidence(self):
		rows = [frappe._dict({"name": f"ISSUE-{index}"}) for index in range(1, 4)]
		check = {
			"status": "Hash Mismatch",
			"ok": False,
			"legacy": False,
			"detail": "bad",
			"payload_status": "Healthy",
			"payload_fingerprint": "A" * 16,
			"pdf_status": "Hash Mismatch",
			"pdf_fingerprint": "B" * 16,
			"expected_size_bytes": 100,
			"actual_size_bytes": 100,
		}
		with (
			patch("frappe.get_all", return_value=rows),
			patch(
				"eduedge.maintenance.report_card_restore.inspect_report_card_issue_integrity",
				return_value=check,
			),
		):
			result = verify_report_card_restore_integrity(
				batch_size=10,
				max_problem_rows=2,
			)
		self.assertEqual(result["problems"], 3)
		self.assertEqual(len(result["problem_rows"]), 2)
		self.assertTrue(result["problem_rows_truncated"])

	def test_restore_assertion_fails_closed_on_integrity_problem(self):
		failed = {
			"status": "FAIL",
			"total_issues": 1,
			"healthy": 0,
			"legacy": 0,
			"problems": 1,
			"problem_rows": [{"issue": "ISSUE-1", "status": "Missing File"}],
			"problem_rows_truncated": False,
			"batch_size": 25,
			"message": "failed",
		}
		with patch(
			"eduedge.maintenance.report_card_restore.verify_report_card_restore_integrity",
			return_value=failed,
		):
			with self.assertRaises(frappe.ValidationError):
				assert_report_card_restore_integrity()

	def test_restore_assertion_allows_legacy_warning_without_problem(self):
		passed = {
			"status": "PASS",
			"total_issues": 1,
			"healthy": 0,
			"legacy": 1,
			"problems": 0,
			"problem_rows": [],
			"problem_rows_truncated": False,
			"batch_size": 25,
			"message": "passed",
		}
		with patch(
			"eduedge.maintenance.report_card_restore.verify_report_card_restore_integrity",
			return_value=passed,
		):
			self.assertEqual(assert_report_card_restore_integrity(), passed)

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
