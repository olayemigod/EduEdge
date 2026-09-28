from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardArchiveAuditContract(unittest.TestCase):
	def test_archive_audit_is_permission_aware_and_page_bounded(self):
		api = (APP / "api" / "report_card_archive_audit.py").read_text()
		for token in (
			"ARCHIVE_AUDITOR_ROLES",
			'frappe.has_permission(ISSUE_DOCTYPE, "read")',
			"assert_branch_access(resolved)",
			"frappe.get_list(",
			"limit_page_length=page_size + 1",
			"MAX_ARCHIVE_AUDIT_PAGE_LENGTH = 25",
			"inspect_report_card_issue_integrity(row.name)",
			'"scope_note"',
		):
			self.assertIn(token, api)

	def test_issue_integrity_checks_payload_before_pdf_archive(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		for token in (
			"def inspect_report_card_issue_integrity(issue_name: str) -> dict:",
			'["payload_hash", "payload_json"]',
			'hashlib.sha256(payload_json.encode("utf-8")).hexdigest()',
			'hmac.compare_digest(actual_payload_hash, expected_payload_hash)',
			'status": "Payload Hash Mismatch"',
			'status": "Unreadable Payload"',
			'status": "Invalid Payload"',
			"inspect_report_card_pdf_archive(issue_name)",
			'"payload_status": "Healthy"',
			'"pdf_status": pdf.get("status") or "Unknown"',
		):
			self.assertIn(token, service)

	def test_integrity_evidence_filters_and_csv_are_bounded_and_privacy_safe(self):
		api = (APP / "api" / "report_card_archive_audit.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_resource_center" / "EduEdgeResourceCenter.vue").read_text()
		for token in (
			"publication: str | None = None",
			"student: str | None = None",
			"search: str | None = None",
			'filters["result_publication"] = resolved_publication',
			'filters["student"] = resolved_student',
			"or_filters=or_filters",
			'"checked_on": str(now_datetime())',
			'"checked_by": frappe.session.user',
		):
			self.assertIn(token, api)
		for token in (
			"Export checked page",
			"exportArchiveEvidence()",
			"csvEvidenceCell(value)",
			"/^[=+\\-@]/",
			"this.archiveAudit.rows.map",
			"new Blob(",
			"\\uFEFF",
			"eduedge-issued-report-integrity-",
			"archiveAudit.checked_on",
			"archiveAudit.checked_by",
		):
			self.assertIn(token, vue)
		for forbidden in (
			"payload_json",
			"/private/files",
			"file_url",
			"_content",
		):
			self.assertNotIn(forbidden, vue)
	def test_archive_inspection_reuses_exact_private_file_contract(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		for token in (
			"def inspect_report_card_pdf_archive(issue_name: str",
			'"attached_to_doctype": ISSUE_DOCTYPE',
			'"attached_to_name": issue_name',
			'"is_private": 1',
			'"file_name": filename',
			'file_row.owner != "Administrator"',
			'hashlib.sha256(pdf_bytes).hexdigest()',
			'hmac.compare_digest(actual_hash, expected_hash)',
			'status": "Legacy"',
			'status": "Missing File"',
			'status": "Size Mismatch"',
			'status": "Hash Mismatch"',
			'status": "Healthy"',
		):
			self.assertIn(token, service)

	def test_results_audit_surfaces_archive_integrity_without_replacing_workflow_log(self):
		vue = (APP / "public" / "js" / "eduedge_resource_center" / "EduEdgeResourceCenter.vue").read_text()
		for token in (
			'resourceKey === \'result_audit\'',
			"Issued Report Integrity",
			"get_report_card_archive_integrity",
			"row.payload_status",
			"row.pdf_status",
			"archiveAudit.summary.healthy",
			"archiveAudit.summary.needs_attention",
			"archiveAudit.summary.legacy",
			"downloadArchiveIssue(row)",
			"openArchiveIssue(row)",
		):
			self.assertIn(token, vue)
		self.assertIn("Permission-aware records", vue)


if __name__ == "__main__":
	unittest.main()
