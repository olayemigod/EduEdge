from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardIssueOperationsContract(unittest.TestCase):
	def test_report_card_context_counts_issued_students(self):
		api = (APP / "api" / "report_cards.py").read_text()
		self.assertIn('"issued": sum(1 for row in students if row.get("issue"))', api)

	def test_profiled_and_legacy_student_lists_surface_latest_issue(self):
		profiled = (APP / "education" / "profiled_report_cards.py").read_text()
		legacy = (APP / "education" / "report_cards.py").read_text()
		self.assertIn('"EduEdge Report Card Issue"', profiled)
		self.assertIn('summary["issue"] = dict(issue) if issue else None', profiled)
		self.assertIn("legacy_issues = frappe.get_all(", legacy)
		self.assertIn('summary["issue"] = dict(issue) if issue else None', legacy)

	def test_historical_issue_versions_can_be_downloaded_exactly(self):
		api = (APP / "api" / "report_cards.py").read_text()
		service = (APP / "education" / "report_card_issues.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		for token in (
			"def get_issued_payload_by_name(issue_name: str",
			'hmac.compare_digest(actual_hash, str(row.payload_hash or ""))',
			'"name": row.name',
			'"issue_version": int(row.issue_version or 1)',
			'"pdf_sha256": row.get("pdf_sha256")',
		):
			self.assertIn(token, service)
		for token in (
			"def download_report_card_issue(issue: str) -> None:",
			"_require_operator()",
			"get_published_publication(row.result_publication)",
			"assert_branch_access(publication.school_branch)",
			"can_view_report_card_scope(publication)",
			"get_issued_payload_by_name(row.name)",
			"resolve_report_card_pdf(payload)",
		):
			self.assertIn(token, api)
		for token in (
			"Download PDF",
			"downloadIssue(row)",
			"/api/method/eduedge.api.report_cards.download_report_card_issue",
		):
			self.assertIn(token, vue)

	def test_report_card_history_uses_explicit_publication_lineage(self):
		api = (APP / "api" / "report_cards.py").read_text()
		lineage = (APP / "education" / "result_publication_lineage.py").read_text()
		service = (APP / "education" / "report_card_issues.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()

		for token in (
			"def get_published_publication_lineage(publication: str) -> list:",
			'"supersedes_publication": current.name',
			'"status": "Published"',
			'"report_card_ready": 1',
			"Result Publication lineage contains a cycle.",
			"Result Publication lineage version sequence is invalid.",
			"Result Publication lineage scope is inconsistent.",
			"Result Publication lineage has multiple published successors.",
		):
			self.assertIn(token, lineage)

		for token in (
			"def _get_published_publication_lineage(publication: str) -> list:",
			"return get_published_publication_lineage(publication)",
			"get_report_card_issue_history_for_publications(publication_names, student)",
			'"current_publication": current_publication.name',
			"Report Card Issue publication lineage is inconsistent.",
			'"lineage_status"] = "Superseded Publication"',
		):
			self.assertIn(token, api)

		self.assertIn("def get_report_card_issue_history_for_publications(", service)
		self.assertIn('"result_publication": ["in", publication_names]', service)
		self.assertIn('"result_publication",', service)
		self.assertNotIn('frappe.get_all(\n\t\t"EduEdge Result Publication",\n\t\tfilters=filters,', api)

		for token in (
			"row.lineage_status",
			"row.is_selected_publication",
			"row.is_selected",
		):
			self.assertIn(token, vue)

	def test_browser_workflow_shows_issue_count_and_versions(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn('EdgeStatCard label="Issued"', vue)
		self.assertIn("row.issue.issue_version", vue)
		self.assertIn("selectedStudent.issue.issue_version", vue)


if __name__ == "__main__":
	unittest.main()
