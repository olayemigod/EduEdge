from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = ROOT / "eduedge" / "eduedge" / "doctype"


class TestCBTExamTemplateContract(unittest.TestCase):
	def _load_doctype(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_exam_template_has_scope_academic_timing_and_policy_fields(self):
		payload = self._load_doctype(
			"eduedge_cbt_exam_template", "eduedge_cbt_exam_template.json"
		)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in (
			"template_title",
			"template_code",
			"exam_scope",
			"school_branch",
			"version_number",
			"supersedes_template",
			"academic_year",
			"academic_term",
			"program",
			"student_group",
			"course",
			"assessment_group",
			"default_examination_centre",
			"duration_minutes",
			"maximum_attempts",
			"pass_percentage",
			"navigation_policy",
			"auto_submit_on_timeout",
			"allow_resume",
			"randomise_questions",
			"randomise_options",
			"marking_policy",
			"result_release_policy",
			"questions",
			"question_count",
			"total_marks",
			"total_negative_marks",
			"status",
		):
			self.assertIn(fieldname, fields)
		self.assertIn("School Examination", fields["exam_scope"]["options"])
		self.assertIn("EduEdge Public Examination", fields["exam_scope"]["options"])
		self.assertEqual(fields["questions"]["options"], "EduEdge CBT Template Question")
		self.assertIn("mandatory_depends_on", fields["school_branch"])
		self.assertIn("mandatory_depends_on", fields["academic_year"])

	def test_template_question_rows_snapshot_safe_scoring_metadata(self):
		payload = self._load_doctype(
			"eduedge_cbt_template_question", "eduedge_cbt_template_question.json"
		)
		self.assertEqual(payload["istable"], 1)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(
			set(fields),
			{
				"display_order",
				"section_label",
				"question",
				"question_type",
				"topic",
				"mark",
				"negative_mark",
			},
		)
		self.assertEqual(fields["question"]["options"], "EduEdge CBT Question")
		self.assertEqual(fields["mark"]["read_only"], 1)
		self.assertEqual(fields["negative_mark"]["read_only"], 1)

	def test_exam_templates_are_not_directly_available_to_candidates(self):
		payload = self._load_doctype(
			"eduedge_cbt_exam_template", "eduedge_cbt_exam_template.json"
		)
		roles = {permission["role"] for permission in payload["permissions"]}
		self.assertNotIn("Student", roles)
		self.assertNotIn("EduEdge Parent", roles)
		self.assertIn("CBT Invigilator", roles)
		self.assertIn("Teacher", roles)
		self.assertIn("Academic Administrator", roles)
		self.assertIn("EduEdge Super Administrator", roles)
		self.assertIn("EduEdge Public Exam Administrator", roles)

	def test_controller_enforces_approved_questions_scope_and_immutability(self):
		text = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_exam_template"
			/ "eduedge_cbt_exam_template.py"
		).read_text()
		for marker in (
			"Question {0} must be Approved",
			"belongs to a different Question Bank",
			"does not belong to the selected School Branch",
			"does not match the template Subject / Course",
			"Approved exam template content is immutable",
			"Create a new template version instead",
			"Approved or Retired exam templates cannot be deleted",
			"require_public_exam_authoring",
			"ALLOWED_STATUS_TRANSITIONS",
			"_question_fingerprint",
			"can_review_templates",
			"user_has_role_permission",
		):
			self.assertIn(marker, text)
		self.assertNotIn("REVIEW_ROLES", text)

	def test_smart_form_cascades_context_and_uses_server_queries(self):
		text = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_exam_template"
			/ "eduedge_cbt_exam_template.js"
		).read_text()
		self.assertIn("approved_question_query", text)
		self.assertIn("examination_centre_link_query", text)
		self.assertIn("studentGroupFilters", text)
		self.assertIn("clearQuestions", text)
		self.assertIn("school_branch", text)
		self.assertIn("course(frm)", text)
		self.assertIn("academic_year(frm)", text)
		self.assertIn("get_public_exam_access_context", text)
		self.assertIn("capabilities?.author?.allowed", text)

	def test_read_api_is_branch_safe_and_public_scope_is_capability_gated(self):
		text = (ROOT / "eduedge" / "api" / "cbt.py").read_text()
		self.assertIn("get_cbt_operations_context", text)
		self.assertIn("get_public_exam_access_context", text)
		self.assertIn("approved_question_query", text)
		self.assertIn("examination_centre_link_query", text)
		self.assertIn("assert_branch_access", text)
		self.assertIn("require_public_exam_authoring", text)
		self.assertIn("without a selected branch deliberately returns empty", text)
		self.assertIn('"status": "Approved"', text)

	def test_exam_templates_are_registered_for_permission_hooks(self):
		hooks = (ROOT / "eduedge" / "hooks.py").read_text()
		self.assertIn(
			'"EduEdge CBT Exam Template": "eduedge.cbt.permissions.cbt_exam_template_query"',
			hooks,
		)
		self.assertIn(
			'"EduEdge CBT Exam Template": "eduedge.cbt.permissions.has_school_branch_permission"',
			hooks,
		)
		permissions = (ROOT / "eduedge" / "cbt" / "permissions.py").read_text()
		self.assertIn("def cbt_exam_template_query", permissions)
		self.assertIn("school_branch` is not null", permissions)
		self.assertIn("can_author_public_exams", permissions)

	def test_cbt_operations_is_registered_across_navigation_surfaces(self):
		navigation = (ROOT / "eduedge" / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		menu = (ROOT / "eduedge" / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		workspace = json.loads(
			(ROOT / "eduedge" / "eduedge" / "workspace" / "eduedge" / "eduedge.json").read_text()
		)
		self.assertIn("/app/eduedge-cbt-operations", navigation)
		self.assertIn("CBT Operations", menu)
		self.assertIn("eduedge_access_manifest", menu)
		self.assertIn("itemAllowed", menu)
		self.assertNotIn("CBT_ROLES", menu)
		self.assertIn("CBT Operations", workspace["content"])
		shortcut_labels = {shortcut["label"] for shortcut in workspace["shortcuts"]}
		self.assertIn("CBT Operations", shortcut_labels)
		self.assertIn("CBT Exam Templates", shortcut_labels)

	def test_cbt_page_uses_standalone_edgesuite_ui_runtime_and_access_matrix(self):
		page_root = ROOT / "eduedge" / "eduedge" / "page" / "eduedge_cbt_operations"
		page = json.loads((page_root / "eduedge_cbt_operations.json").read_text())
		loader = (page_root / "eduedge_cbt_operations.js").read_text()
		bundle = (ROOT / "eduedge" / "public" / "js" / "eduedge_cbt_operations.bundle.js").read_text()
		component = (
			ROOT
			/ "eduedge"
			/ "public"
			/ "js"
			/ "eduedge_cbt_operations"
			/ "EduEdgeCBTOperations.vue"
		).read_text()
		self.assertEqual(page["name"], "eduedge-cbt-operations")
		self.assertEqual(page["roles"], [])
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertIn("createEduEdgeCBTOperationsApp", loader)
		self.assertIn("createEduEdgeApp", bundle)
		self.assertIn("EdgeAppShell", component)
		self.assertIn("get_cbt_operations_context", component)
		self.assertIn("EduEdge Exams access for this site", component)
		self.assertIn("PUBLIC_CAPABILITY_META", component)


if __name__ == "__main__":
	unittest.main()
