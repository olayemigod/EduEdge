from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicSessionsPageContract(unittest.TestCase):
	def test_page_bundle_and_route_exist(self):
		for relative in (
			"eduedge/page/eduedge_academic_sessions/__init__.py",
			"eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.json",
			"eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.js",
			"public/js/eduedge_academic_sessions.bundle.js",
			"public/js/eduedge_academic_sessions/EduEdgeAcademicSessions.vue",
		):
			self.assertTrue((APP / relative).exists(), relative)

		page = (APP / "eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.json").read_text()
		loader = (APP / "eduedge/page/eduedge_academic_sessions/eduedge_academic_sessions.js").read_text()
		self.assertIn('"name": "eduedge-academic-sessions"', page)
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertIn('frappe.require("eduedge_academic_sessions.bundle.js"', loader)

	def test_navigation_and_access_manifest_expose_sessions_and_terms(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		product_menu = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		access = (APP / "access_control.py").read_text()
		for source in (navigation, product_menu):
			self.assertIn('"/app/eduedge-academic-sessions"', source)
			self.assertIn('const academicTerms = term("academic_term"', source)
		self.assertIn('menuItem(`${academicYears} & ${academicTerms}`', navigation)
		self.assertIn('item(`${academicYears} & ${academicTerms}`', product_menu)
		self.assertIn("permissionFilteredMenu", product_menu)
		self.assertIn("itemAllowed", product_menu)
		self.assertIn('"/app/eduedge-academic-sessions": (', access)
		self.assertIn('("academic_year", "read")', access)
		self.assertIn('("academic_term", "read")', access)

	def test_page_uses_edgesuite_and_cascades_session_to_terms(self):
		component = (APP / "public/js/eduedge_academic_sessions/EduEdgeAcademicSessions.vue").read_text()
		for token in (
			"<EdgeAppShell",
			"<EdgePageLayout>",
			"<EdgeFilterBar",
			"<EdgeDashboardLayout",
			"<EdgeStatusBadge",
			'active-route="/app/eduedge-academic-sessions"',
			'v-model="filters.academic_year"',
			"sessionChanged() { this.load(); }",
			"this.filters.academic_year = response.message?.name",
			"read_only: !isNew",
			"type: \"POST\"",
		):
			self.assertIn(token, component)

	def test_backend_preserves_native_source_of_truth_and_permissions(self):
		api_path = APP / "api/academic_sessions.py"
		api = api_path.read_text()
		ast.parse(api)
		for token in (
			'ACADEMIC_YEAR_DOCTYPE = "Academic Year"',
			'ACADEMIC_TERM_DOCTYPE = "Academic Term"',
			"frappe.get_list(",
			"doc.check_permission(\"write\")",
			'@frappe.whitelist(methods=["POST"])',
			"_validate_existing_terms_inside_session",
			"_validate_term_overlap",
			"Term dates must fall inside the selected Academic Session.",
			"Session identity cannot be changed in quick edit.",
			"Term identity and Session cannot be changed in quick edit.",
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions=True", api)
		self.assertNotIn("delete_doc", api)

	def test_component_has_advanced_form_escape_hatches(self):
		component = (APP / "public/js/eduedge_academic_sessions/EduEdgeAcademicSessions.vue").read_text()
		for token in (
			'frappe.set_route("Form", "Academic Year", name)',
			'frappe.set_route("Form", "Academic Term", name)',
			'window.open("/app/academic-year"',
			'window.open("/app/academic-term"',
			'this.openRoute("/app/eduedge-academic-foundation")',
		):
			self.assertIn(token, component)


if __name__ == "__main__":
	unittest.main()
