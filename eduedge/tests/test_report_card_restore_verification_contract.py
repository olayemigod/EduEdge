from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
DOCS = ROOT / "docs"


class TestReportCardRestoreVerificationContract(unittest.TestCase):
	def test_restore_verifier_is_read_only_bounded_and_fail_closed(self):
		service = (APP / "maintenance" / "report_card_restore.py").read_text()
		for token in (
			"def verify_report_card_restore_integrity(",
			"def assert_report_card_restore_integrity(",
			"DEFAULT_BATCH_SIZE = 25",
			"MAX_BATCH_SIZE = 100",
			"DEFAULT_MAX_PROBLEM_ROWS = 100",
			"MAX_PROBLEM_ROWS = 500",
			"frappe.get_all(",
			"limit_page_length=page_size",
			"inspect_report_card_issue_integrity(row.name)",
			'"legacy": legacy',
			'"problems": problems',
			'"problem_rows_truncated": problems > len(problem_rows)',
			"frappe.ValidationError",
		):
			self.assertIn(token, service)
		for forbidden in (
			".insert(",
			".save(",
			"frappe.db.set_value(",
			"frappe.delete_doc(",
			"frappe.db.delete(",
		):
			self.assertNotIn(forbidden, service)

	def test_restore_runbook_requires_matching_private_files_backup(self):
		runbook = (DOCS / "eduedge_report_card_backup_restore_verification.md").read_text()
		for token in (
			"backup --with-files",
			"--with-public-files <files.tar>",
			"--with-private-files <private-files.tar>",
			"same backup run",
			"Do not mix the database backup from one timestamp with private files from another timestamp.",
			"verify_report_card_restore_integrity",
			"assert_report_card_restore_integrity",
			"Do not regenerate, overwrite, delete, or patch an issued Report Card",
			"Results Audit → Issued Report Integrity",
		):
			self.assertIn(token, runbook)

	def test_restore_runbook_distinguishes_legacy_from_corruption(self):
		runbook = (DOCS / "eduedge_report_card_backup_restore_verification.md").read_text()
		self.assertIn("Legacy", runbook)
		self.assertIn("This is a warning, not corruption.", runbook)
		self.assertIn("The gate must fail.", runbook)


if __name__ == "__main__":
	unittest.main()
