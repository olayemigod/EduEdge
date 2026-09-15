from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultsPortalContract(unittest.TestCase):
	def test_portal_access_is_relationship_driven(self):
		api = (APP / "api" / "results_portal.py").read_text()
		self.assertIn('"Student"', api)
		self.assertIn('"Guardian"', api)
		self.assertIn('"Student Guardian"', api)
		self.assertIn("You are not linked to this Student.", api)

	def test_portal_only_uses_effective_issued_report_cards(self):
		api = (APP / "api" / "results_portal.py").read_text()
		self.assertIn("EduEdge Report Card Issue", api)
		self.assertIn("get_effective_issued_payload", api)
		self.assertNotIn("Assessment Result", api)
		self.assertNotIn("EduEdge Published Result Snapshot", api)

	def test_guardian_with_multiple_children_is_supported(self):
		api = (APP / "api" / "results_portal.py").read_text()
		self.assertIn("guardian_names", api)
		self.assertIn("student_names", api)
		self.assertIn('student["results"]', api)

	def test_portal_can_open_subject_level_result_detail(self):
		js = (APP / "public" / "js" / "eduedge_results_portal.js").read_text()
		self.assertIn("get_my_result", js)
		self.assertIn("summary.courses", js)
		self.assertIn("display_components", js)
		self.assertIn("course.metrics", js)
		self.assertIn("Class Teacher", js)
		self.assertIn("Principal", js)

	def test_official_pdf_download_reuses_frozen_issue_payload(self):
		api = (APP / "api" / "results_portal.py").read_text()
		self.assertIn("def download_my_result", api)
		self.assertIn("get_effective_issued_payload(publication, student)", api)
		self.assertIn("eduedge/templates/report_card.html", api)
		self.assertIn('frappe.response.type = "pdf"', api)

	def test_web_page_is_authenticated_and_noindex(self):
		page = (APP / "www" / "eduedge-results.py").read_text()
		html = (APP / "www" / "eduedge-results.html").read_text()
		self.assertIn("redirect-to=/eduedge-results", page)
		self.assertIn("frappe.Redirect", page)
		self.assertIn("noindex,nofollow,noarchive", html)
		self.assertIn("eduedge_results_portal.js", html)


if __name__ == "__main__":
	unittest.main()
