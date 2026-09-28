from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from eduedge.api.results_portal import _assert_portal_student, download_my_result


class TestResultsPortalRuntime(FrappeTestCase):
	def test_unrelated_student_is_denied(self):
		with patch(
			"eduedge.api.results_portal._portal_students",
			return_value=[{"name": "STU-1", "student_name": "Student One"}],
		):
			with self.assertRaises(frappe.PermissionError):
				_assert_portal_student("guardian@example.com", "STU-2")

	def test_linked_student_is_accepted(self):
		expected = {"name": "STU-1", "student_name": "Student One"}
		with patch("eduedge.api.results_portal._portal_students", return_value=[expected]):
			self.assertEqual(
				_assert_portal_student("guardian@example.com", "STU-1"),
				expected,
			)

	def test_download_uses_verified_archive_resolver(self):
		payload = {"issue_record": {"issue_version": 2}}
		with (
			patch("eduedge.api.results_portal._require_login", return_value="guardian@example.com"),
			patch("eduedge.api.results_portal._assert_portal_student") as assert_student,
			patch(
				"eduedge.api.results_portal.get_effective_issued_payload",
				return_value=payload,
			),
			patch(
				"eduedge.api.results_portal.resolve_report_card_pdf",
				return_value=b"%PDF archived",
			) as resolve_pdf,
		):
			download_my_result("PUB-1", "STU-1")
			assert_student.assert_called_once_with("guardian@example.com", "STU-1")
			resolve_pdf.assert_called_once_with(payload)
			self.assertEqual(frappe.response.filecontent, b"%PDF archived")
			self.assertEqual(frappe.response.type, "pdf")
			self.assertEqual(frappe.response.filename, "Report Card STU-1 v2.pdf")

	def test_download_fails_when_issue_is_not_effective(self):
		with (
			patch("eduedge.api.results_portal._require_login", return_value="student@example.com"),
			patch("eduedge.api.results_portal._assert_portal_student"),
			patch(
				"eduedge.api.results_portal.get_effective_issued_payload",
				return_value=None,
			),
			patch("eduedge.api.results_portal.resolve_report_card_pdf") as resolve_pdf,
		):
			with self.assertRaises(frappe.PermissionError):
				download_my_result("PUB-1", "STU-1")
			resolve_pdf.assert_not_called()
