from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammesPageContract(unittest.TestCase):
	def test_programmes_api_is_bounded_permission_aware_and_institution_scoped(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		for token in (
			"MAX_PAGE_LENGTH = 50",
			"MAX_DEPARTMENT_OPTIONS = 30",
			'frappe.has_permission("Program", "read")',
			"_assert_institution_access",
			"_assert_section_context",
			"page_length=page_length + 1",
			'fields=[{"COUNT": "name", "as": "record_count"}]',
		):
			self.assertIn(token, api)

	def test_programmes_api_reports_course_and_active_offering_counts(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		self.assertIn('"Program Course"', api)
		self.assertIn('"EduEdge Program Offering"', api)
		self.assertIn('"course_count"', api)
		self.assertIn('"active_offering_count"', api)
		self.assertIn('"is_active": 1', api)

	def test_programme_quick_save_does_not_rebuild_course_rows(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		self.assertIn('require_eduedge_access(feature_key="academics", action="save_programme")', api)
		self.assertIn("doc.check_permission(\"write\")", api)
		self.assertIn("doc.save()", api)
		self.assertNotIn("doc.set(\"courses\"", api)
		self.assertNotIn("db_set(", api)

	def test_programmes_page_uses_dedicated_edgesuite_runtime(self):
		component = (
			APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue"
		).read_text(encoding="utf-8")
		loader = (
			APP / "eduedge" / "page" / "eduedge_programs" / "eduedge_programs.js"
		).read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_programmes.bundle.js").read_text(encoding="utf-8")
		self.assertIn("<EdgeAppShell", component)
		self.assertIn("Catalogue filters", component)
		self.assertIn("Course Rows", component)
		self.assertIn("Active Offerings", component)
		self.assertIn("createEduEdgeProgrammesApp", bundle)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_programmes.bundle.js"))
		self.assertNotIn("registerEduEdgeResourcePage", loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)

	def test_programme_form_cascades_section_by_institution_and_preserves_full_form(self):
		component = (
			APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue"
		).read_text(encoding="utf-8")
		self.assertIn("draftSections", component)
		self.assertIn("draftInstitutionChanged", component)
		self.assertIn("this.draft.eduedge_academic_section = \"\"", component)
		self.assertIn('frappe.set_route("Form", "Program", name)', component)
		self.assertIn("Course rows, portal settings, and advanced fields remain", component)

	def test_ci_checks_programmes_entry_scripts(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn("node --check eduedge/public/js/eduedge_programmes.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_programs/eduedge_programs.js", workflow)


if __name__ == "__main__":
	unittest.main()
