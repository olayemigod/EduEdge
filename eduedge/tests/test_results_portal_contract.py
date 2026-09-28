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

	def test_portal_can_open_current_terminal_and_annual_result_detail(self):
		js = (APP / "public" / "js" / "eduedge_results_portal.js").read_text()
		for token in (
			"get_my_result",
			"summary.courses",
			"course.display_components",
			"period.display_components",
			"component.display_value",
			"course.metrics",
			"summary.result_status_legend",
			"Result Status",
			"Class Teacher",
			"Principal",
		):
			self.assertIn(token, js)

	def test_official_pdf_download_uses_verified_archived_pdf_resolver(self):
		api = (APP / "api" / "results_portal.py").read_text()
		self.assertIn("def download_my_result", api)
		self.assertIn("get_effective_issued_payload(publication, student)", api)
		self.assertIn("resolve_report_card_pdf(payload)", api)
		self.assertIn('frappe.response.type = "pdf"', api)
		self.assertNotIn("get_pdf(", api)
		self.assertNotIn("frappe.render_template(", api)
		self.assertNotIn('frappe.get_single("EduEdge Settings")', api)

	def test_web_page_is_authenticated_and_noindex(self):
		page = (APP / "www" / "eduedge-results.py").read_text()
		html = (APP / "www" / "eduedge-results.html").read_text()
		self.assertIn("redirect-to=/eduedge-results", page)
		self.assertIn("frappe.Redirect", page)
		self.assertIn("noindex,nofollow,noarchive", html)
		self.assertIn("eduedge_results_portal.js", html)


if __name__ == "__main__":
	unittest.main()
