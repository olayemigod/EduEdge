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

	def test_browser_workflow_shows_issue_count_and_versions(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn('EdgeStatCard label="Issued"', vue)
		self.assertIn("row.issue.issue_version", vue)
		self.assertIn("selectedStudent.issue.issue_version", vue)


if __name__ == "__main__":
	unittest.main()
