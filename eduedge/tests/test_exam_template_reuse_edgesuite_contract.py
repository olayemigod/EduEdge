from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestExamTemplateReuseEdgeSuiteContract(unittest.TestCase):
	def test_edgesuite_template_pages_are_registered_and_permission_neutral(self):
		for page_name, title in (
			("eduedge_exam_templates", "Exam Templates"),
			("eduedge_exam_template_builder", "Exam Template Builder"),
		):
			page_root = APP / "eduedge" / "page" / page_name
			self.assertTrue((page_root / "__init__.py").exists())
			page = json.loads((page_root / f"{page_name}.json").read_text())
			self.assertEqual(page["title"], title)
			self.assertEqual(page["roles"], [])
			loader = (page_root / f"{page_name}.js").read_text()
			self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
			self.assertIn("EdgeAppShell", loader)
			self.assertIn("EdgeLinkField", loader)

	def test_template_library_exposes_reuse_scope_subject_and_purpose_filters(self):
		component = (
			APP / "public" / "js" / "eduedge_exam_templates" / "EduEdgeExamTemplates.vue"
		).read_text()
		for marker in (
			"Universal, Institution-wide, Branch-wide",
			"Reuse Scope",
			"Subject Applicability",
			"Exam Purpose",
			"Content Mode",
			"state.options.template_modes",
			"row.template_mode",
			"get_exam_templates",
			"requestSequence",
			"pagination.has_previous",
			"pagination.has_next",
			"/app/eduedge-exam-template-builder",
		):
			self.assertIn(marker, component)
		self.assertNotIn("answer_key", component)
		self.assertNotIn("marking_guide", component)

	def test_builder_supports_blueprints_and_fixed_subject_sets_without_duplication(self):
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_exam_template_builder"
			/ "EduEdgeExamTemplateBuilder.vue"
		).read_text()
		for marker in (
			"Reusable template identity",
			"Template Reuse Scope",
			"Universal",
			"Institution-wide",
			"Branch-wide",
			"Exam Purpose",
			"Template Content Mode",
			"Policy Blueprint",
			"Fixed Question Set",
			"Subject Applicability",
			"Any Subject",
			"Specific Subject",
			"actual exam schedule selects",
			"isBlueprint",
			"isFixedSet",
			"Only Approved questions",
			"save_template",
			"perform_template_action",
			"create_template_version",
		):
			self.assertIn(marker, component)
		self.assertIn('v-if="isBlueprint"', component)
		self.assertIn('<section v-else class="eduedge-template-builder-panel">', component)
		self.assertIn("if (!this.isFixedSet", component)

	def test_template_api_is_scope_safe_and_returns_applicable_approved_templates(self):
		api = (APP / "api" / "exam_templates.py").read_text()
		for marker in (
			"def get_exam_templates",
			"def get_applicable_exam_templates",
			"def get_template_builder_context",
			"def save_template",
			"def perform_template_action",
			"def create_template_version",
			"def search_template_options",
			"REUSE_UNIVERSAL",
			"REUSE_INSTITUTION",
			"REUSE_BRANCH",
			"SUBJECT_ANY",
			"SUBJECT_SPECIFIC",
			"MODE_BLUEPRINT",
			"MODE_FIXED",
			'"status": "Approved"',
			"row.template_reuse_scope == REUSE_INSTITUTION",
			"row.template_reuse_scope == REUSE_BRANCH",
			"row.subject_applicability == SUBJECT_SPECIFIC",
			"require_eduedge_access",
			"TimestampMismatchError",
		):
			self.assertIn(marker, api)

		# Question text may be searched server-side while selecting an approved
		# question, but it must not be returned by the template list payload.
		list_query_start = api.index("rows = frappe.get_list(\n\t\tTEMPLATE_DOCTYPE")
		list_query_end = api.index("\n\tall_institutions =", list_query_start)
		list_query = api[list_query_start:list_query_end]
		for forbidden in ('"answer_key"', '"marking_guide"', '"question_text"'):
			self.assertNotIn(forbidden, list_query)
		for forbidden in ('"answer_key"', '"marking_guide"', "ignore_permissions=True"):
			self.assertNotIn(forbidden, api)

	def test_schedule_resolves_reusable_template_against_actual_branch_and_subject(self):
		schedule = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.py"
		).read_text()
		for marker in (
			"_validate_template_applicability",
			"template.template_reuse_scope == REUSE_BRANCH",
			"template.template_reuse_scope == REUSE_INSTITUTION",
			"template.template_reuse_scope == REUSE_UNIVERSAL",
			"template.subject_applicability == SUBJECT_SPECIFIC",
			"template.subject_applicability == SUBJECT_ANY",
			"Select the actual Subject / Course for this schedule",
			"This Universal template cannot be used outside its Company",
			"This Institution-wide template cannot be used outside its Institution",
			"This Branch-wide template cannot be used by another Branch",
			"SNAPSHOT_FIELDS",
		):
			self.assertIn(marker, schedule)

	def test_permission_query_expands_visibility_without_cross_company_leakage(self):
		permissions = (APP / "cbt" / "permissions.py").read_text()
		for marker in (
			"def _exam_template_condition",
			"def _has_exam_template_scope_permission",
			"REUSE_UNIVERSAL",
			"REUSE_INSTITUTION",
			"REUSE_BRANCH",
			"doc.get(\"company\") in",
			"doc.get(\"institution\") in",
			"doc.get(\"school_branch\") in",
			"`company` in",
			"`institution` in",
			"`school_branch` in",
		):
			self.assertIn(marker, permissions)

	def test_legacy_templates_are_backfilled_without_reclassifying_existing_question_sets(self):
		patch = (APP / "patches" / "v0_8" / "backfill_exam_template_reuse_scope.py").read_text()
		patches = (APP / "patches.txt").read_text()
		for marker in (
			"MODE_FIXED if row.course else MODE_BLUEPRINT",
			"SUBJECT_SPECIFIC if row.course else SUBJECT_ANY",
			'values["template_reuse_scope"] = REUSE_BRANCH',
			'values["template_reuse_scope"] = REUSE_UNIVERSAL',
			"update_modified=False",
		):
			self.assertIn(marker, patch)
		self.assertIn("backfill_exam_template_reuse_scope", patches)

	def test_navigation_cbt_handoff_and_ci_use_edgesuite_template_routes(self):
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		access = (APP / "access_control.py").read_text()
		cbt_bundle = (APP / "public" / "js" / "eduedge_cbt_operations.bundle.js").read_text()
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
		for route in ("/app/eduedge-exam-templates", "/app/eduedge-exam-template-builder"):
			self.assertIn(route, navigation)
			self.assertIn(route, access)
		self.assertIn('route === "/app/eduedge-cbt-exam-template"', cbt_bundle)
		self.assertIn('return "/app/eduedge-exam-templates"', cbt_bundle)
		self.assertIn("eduedge-exam-template-builder?template=", cbt_bundle)
		for entry in (
			"eduedge_exam_templates.bundle.js",
			"eduedge_exam_template_builder.bundle.js",
			"eduedge_exam_templates/eduedge_exam_templates.js",
			"eduedge_exam_template_builder/eduedge_exam_template_builder.js",
		):
			self.assertIn(entry, workflow)


if __name__ == "__main__":
	unittest.main()
