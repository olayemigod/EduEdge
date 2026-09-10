from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
TEMPLATE_META = APP / "eduedge/doctype/eduedge_cbt_exam_template/eduedge_cbt_exam_template.json"


class TestExamTemplateReuseScopeContract(unittest.TestCase):
	def test_metadata_models_reuse_subject_and_content_dimensions(self):
		metadata = json.loads(TEMPLATE_META.read_text(encoding="utf-8"))
		fields = {row["fieldname"]: row for row in metadata["fields"]}

		self.assertEqual(
			set(fields["template_reuse_scope"]["options"].splitlines()),
			{"Universal", "Institution-wide", "Branch-wide"},
		)
		self.assertEqual(
			set(fields["subject_applicability"]["options"].splitlines()),
			{"Any Subject", "Specific Subject"},
		)
		self.assertEqual(
			set(fields["template_mode"]["options"].splitlines()),
			{"Policy Blueprint", "Fixed Question Set"},
		)
		for purpose in (
			"Continuous Assessment",
			"Midterm Examination",
			"End-of-Term Examination",
			"Mock Examination",
			"Entrance Examination",
			"Practice / Revision",
		):
			self.assertIn(purpose, fields["exam_purpose"]["options"])

		self.assertIn("Specific Subject", fields["course"]["mandatory_depends_on"])
		self.assertIn("Branch-wide", fields["school_branch"]["mandatory_depends_on"])
		self.assertNotIn("mandatory_depends_on", fields["academic_year"])
		self.assertIn("Fixed Question Set", fields["questions"]["depends_on"])

	def test_controller_allows_blueprints_and_constrains_fixed_school_sets(self):
		source = (
			APP / "eduedge/doctype/eduedge_cbt_exam_template/eduedge_cbt_exam_template.py"
		).read_text(encoding="utf-8")
		for expected in (
			'REUSE_UNIVERSAL = "Universal"',
			'REUSE_INSTITUTION = "Institution-wide"',
			'REUSE_BRANCH = "Branch-wide"',
			'SUBJECT_ANY = "Any Subject"',
			'SUBJECT_SPECIFIC = "Specific Subject"',
			'MODE_BLUEPRINT = "Policy Blueprint"',
			'MODE_FIXED = "Fixed Question Set"',
			"Company is required for a Universal school template",
			"School Fixed Question Sets must be Branch-wide",
			"A Policy Blueprint cannot carry fixed questions",
			"Questions are selected when the exam is prepared from the blueprint",
		):
			self.assertIn(expected, source)

	def test_schedule_binds_actual_branch_and_subject_for_reusable_templates(self):
		source = (
			APP / "eduedge/doctype/eduedge_cbt_exam_schedule/eduedge_cbt_exam_schedule.py"
		).read_text(encoding="utf-8")
		for expected in (
			"_validate_template_applicability(template)",
			"template.template_reuse_scope == REUSE_BRANCH",
			"template.subject_applicability == SUBJECT_SPECIFIC",
			"This Institution-wide Template cannot be used outside its Institution",
			"This Universal Template cannot be used outside its Company",
			"Select the actual Subject / Course for this Schedule",
			"for fieldname in SNAPSHOT_FIELDS",
		):
			self.assertIn(expected, source)

	def test_permission_hooks_include_universal_institution_and_branch_scopes(self):
		source = (APP / "cbt/permissions.py").read_text(encoding="utf-8")
		for expected in (
			"def _exam_template_condition",
			"template_reuse_scope",
			"REUSE_UNIVERSAL",
			"REUSE_INSTITUTION",
			"REUSE_BRANCH",
			"company_values",
			"institution_values",
			"branch_values",
			"_has_exam_template_scope_permission",
		):
			self.assertIn(expected, source)

	def test_edgesuite_list_uses_permission_safe_counts_and_safe_payload(self):
		list_api = (APP / "api/exam_templates_list.py").read_text(encoding="utf-8")
		core_api = (APP / "api/exam_templates.py").read_text(encoding="utf-8")
		for expected in (
			"_permission_safe_status_counts",
			"frappe.get_list(",
			'fields=["status"]',
			"limit_page_length=0",
			"get_applicable_exam_templates",
			"MAX_APPLICABLE_RESULTS",
			"template_reuse_scope",
			"subject_applicability",
			"exam_purpose",
			"template_mode",
		):
			self.assertIn(expected, list_api + core_api)
		self.assertNotIn("frappe.db.count", list_api)
		self.assertNotIn("count(name) as count", list_api)
		self.assertNotIn('group_by="status"', list_api)
		self.assertNotIn('"answer_key"', list_api)
		self.assertNotIn('"marking_guide"', list_api)

	def test_edgesuite_pages_and_builder_expose_reusable_template_workflow(self):
		list_root = APP / "eduedge/page/eduedge_exam_templates"
		builder_root = APP / "eduedge/page/eduedge_exam_template_builder"
		for root, page_name in (
			(list_root, "eduedge-exam-templates"),
			(builder_root, "eduedge-exam-template-builder"),
		):
			for filename in ("__init__.py", f"{page_name.replace('-', '_')}.json", f"{page_name.replace('-', '_')}.js"):
				self.assertTrue((root / filename).exists(), str(root / filename))
			page = json.loads((root / f"{page_name.replace('-', '_')}.json").read_text(encoding="utf-8"))
			self.assertEqual(page["name"], page_name)
			self.assertEqual(page["roles"], [])

		list_component = (
			APP / "public/js/eduedge_exam_templates/EduEdgeExamTemplates.vue"
		).read_text(encoding="utf-8")
		builder_component = (
			APP / "public/js/eduedge_exam_template_builder/EduEdgeExamTemplateBuilder.vue"
		).read_text(encoding="utf-8")
		for expected in (
			"<EdgeAppShell",
			"Reuse Scope",
			"Subject Applicability",
			"Exam Purpose",
			"Content Mode",
			"scope_label",
		):
			self.assertIn(expected, list_component)
		for expected in (
			"Reusable template identity",
			"Universal",
			"Institution-wide",
			"Branch-wide",
			"Policy Blueprint",
			"Fixed Question Set",
			"No fixed questions required",
			"Academic defaults",
			"Open Technical Record",
			"Create New Version",
		):
			self.assertIn(expected, builder_component)

	def test_navigation_redirects_native_template_routes_to_edgesuite(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		adapter = (APP / "public/js/eduedge_cbt_operations.bundle.js").read_text(encoding="utf-8")
		for route in ("/app/eduedge-exam-templates", "/app/eduedge-exam-template-builder"):
			self.assertIn(route, navigation)
			self.assertIn(route, access)
		self.assertIn('route === "/app/eduedge-cbt-exam-template"', adapter)
		self.assertIn("TEMPLATE_NATIVE_PREFIX", adapter)
		self.assertIn("eduedge-exam-template-builder?template=", adapter)

	def test_backfill_and_ci_are_registered(self):
		patches = (APP / "patches.txt").read_text(encoding="utf-8")
		patch = (APP / "patches/v0_8/backfill_exam_template_reuse_scope.py").read_text(encoding="utf-8")
		workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
		self.assertIn("backfill_exam_template_reuse_scope", patches)
		for expected in (
			"REUSE_BRANCH",
			"REUSE_UNIVERSAL",
			"MODE_FIXED",
			"MODE_BLUEPRINT",
			"update_modified=False",
		):
			self.assertIn(expected, patch)
		for command in (
			"node --check eduedge/public/js/eduedge_exam_templates.bundle.js",
			"node --check eduedge/public/js/eduedge_exam_template_builder.bundle.js",
			"node --check eduedge/eduedge/page/eduedge_exam_templates/eduedge_exam_templates.js",
			"node --check eduedge/eduedge/page/eduedge_exam_template_builder/eduedge_exam_template_builder.js",
		):
			self.assertIn(command, workflow)


if __name__ == "__main__":
	unittest.main()
