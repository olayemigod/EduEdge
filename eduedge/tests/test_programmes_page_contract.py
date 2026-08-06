from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProgrammesPageContract(unittest.TestCase):
	def test_programmes_api_is_bounded_permission_aware_and_institution_scoped(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		for token in (
			"MAX_PAGE_LENGTH = 50", "MAX_DEPARTMENT_OPTIONS = 100",
			'frappe.has_permission("Program", "read")', "_assert_institution_access",
			"_assert_department_context", "page_length=page_length + 1",
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
		self.assertIn('doc.check_permission("write")', api)
		self.assertIn("doc.save()", api)
		self.assertNotIn('doc.set("courses"', api)
		self.assertNotIn("db_set(", api)

	def test_department_options_and_save_are_scoped_to_institution(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		self.assertIn("def _assert_department_context", api)
		self.assertIn("_validate_department(department, institution)", api)
		self.assertIn('filters[INSTITUTION_FIELD] = institution', api)
		self.assertIn("draftDepartments", component)
		self.assertIn("draftInstitutionChanged", component)
		self.assertIn('this.draft.department = ""', component)

	def test_programmes_page_uses_dedicated_edgesuite_runtime(self):
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		loader = (APP / "eduedge" / "page" / "eduedge_programs" / "eduedge_programs.js").read_text(encoding="utf-8")
		bundle = (APP / "public" / "js" / "eduedge_programmes.bundle.js").read_text(encoding="utf-8")
		self.assertIn("<EdgeAppShell", component)
		self.assertIn("Catalogue filters", component)
		self.assertIn('`${coursePlural} Rows`', component)
		self.assertIn('`Active ${offeringPlural}`', component)
		self.assertIn("createEduEdgeProgrammesApp", bundle)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_programmes.bundle.js"))
		self.assertNotIn("registerEduEdgeResourcePage", loader)

	def test_programme_form_cascades_department_by_institution_and_preserves_full_form(self):
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		self.assertIn("draftDepartments", component)
		self.assertIn("draftInstitutionChanged", component)
		self.assertIn('this.draft.department = ""', component)
		self.assertIn('frappe.set_route("Form", "Program", name)', component)
		self.assertIn("editorExample", component)
		for example in (
			"Primary Section → Primary 1",
			"Junior Secondary School → JSS 1",
			"Department of Crop Science → BSc Agriculture",
			"Technical Training → Electrical Installation",
		):
			self.assertIn(example, component)
		self.assertNotIn("eduedge_academic_section", component)

	def test_class_curriculum_read_is_native_permission_aware_and_institution_scoped(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		for token in (
			"def _programme_curriculum_payload",
			"def get_programme_curriculum",
			'doc.get("courses")',
			'"configured_courses"',
			'"available_courses"',
			'"active_offerings"',
			'frappe.get_list(\n\t\t"Course"',
			'available_filters[INSTITUTION_FIELD] = institution',
			'doc.check_permission(permission_type)',
		):
			self.assertIn(token, api)
		self.assertNotIn("ignore_permissions", api)

	def test_class_curriculum_addition_is_additive_and_same_institution_only(self):
		api = (APP / "api" / "programmes.py").read_text(encoding="utf-8")
		for token in (
			"def add_programme_curriculum_courses",
			'methods=["POST"]',
			'require_eduedge_access(feature_key="academics", action="add_programme_curriculum_courses")',
			'_programme_doc(programme, "write")',
			'course_doc.check_permission("read")',
			"Subject / Course {0} belongs to another Institution",
			'doc.append("courses", {"course": course, "required": 1})',
			'"can_remove_courses": False',
			"Subject removal requires a separate impact review",
		):
			self.assertIn(token, api)
		self.assertNotIn("delete_doc", api)
		self.assertNotIn("frappe.db.delete", api)

	def test_programmes_page_exposes_visible_class_curriculum_workspace(self):
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		for token in (
			"Class Curriculum",
			"openCurriculumForRow",
			"loadCurriculum",
			"get_programme_curriculum",
			"configured_courses",
			"available_courses",
			"Add Institution",
			"addCurriculumCourses",
			"add_programme_curriculum_courses",
			"Instructor Assignment additions will also appear here",
			"Active Class / Programme Intakes",
			"openDeliveryCurriculum",
			"/app/eduedge-curriculum",
		):
			self.assertIn(token, component)
		self.assertIn('type: "POST"', component)
		self.assertIn('v-if="draft.name" ref="curriculumPanel"', component)

	def test_ci_checks_programmes_entry_scripts(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
		self.assertIn("node --check eduedge/public/js/eduedge_programmes.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_programs/eduedge_programs.js", workflow)


if __name__ == "__main__":
	unittest.main()
