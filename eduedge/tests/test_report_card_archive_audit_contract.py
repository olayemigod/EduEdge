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
			"inspect_report_card_pdf_archive(row.name)",
			'"scope_note"',
		):
			self.assertIn(token, api)

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
			"Archive Integrity",
			"get_report_card_archive_integrity",
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
