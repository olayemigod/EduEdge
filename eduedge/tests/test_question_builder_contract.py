import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE_ROOT = ROOT / "eduedge" / "eduedge" / "page" / "eduedge_question_builder"
VUE_PATH = ROOT / "eduedge" / "public" / "js" / "eduedge_question_builder" / "EduEdgeQuestionBuilder.vue"


class TestQuestionBuilderContract(unittest.TestCase):
	def test_page_shell_is_permission_neutral_and_uses_edgesuite_runtime(self):
		metadata = json.loads((PAGE_ROOT / "eduedge_question_builder.json").read_text())
		self.assertEqual(metadata["roles"], [])

		access = (ROOT / "eduedge" / "access_control.py").read_text()
		self.assertIn('"/app/eduedge-question-builder"', access)
		self.assertIn('(“cbt_question”, “read”)'.replace('“', '"').replace('”', '"'), access)
		self.assertIn('(“cbt_question”, “create”)'.replace('“', '"').replace('”', '"'), access)
		self.assertIn('(“cbt_question”, “write”)'.replace('“', '"').replace('”', '"'), access)

		loader = (PAGE_ROOT / "eduedge_question_builder.js").read_text()
		self.assertIn('frappe.require("edgesuite_ui.bundle.js"', loader)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertIn('"eduedge_question_builder.bundle.css"', loader)
		self.assertIn('"eduedge_question_builder.bundle.js"', loader)
		self.assertIn("window.createEduEdgeQuestionBuilderApp", loader)
		self.assertIn('data-edge-product="eduedge"', loader)
		self.assertIn("resolveQuestionName", loader)
		self.assertIn("wrapper.vue_app.unmount()", loader)

	def test_bundle_exports_question_builder(self):
		bundle = (ROOT / "eduedge" / "public" / "js" / "eduedge_question_builder.bundle.js").read_text()
		self.assertIn("EduEdgeQuestionBuilder.vue", bundle)
		self.assertIn("createEduEdgeQuestionBuilderApp", bundle)
		self.assertIn("createEduEdgeApp", bundle)
		self.assertIn("window.EduEdgeQuestionBuilder", bundle)

	def test_builder_is_teacher_friendly_and_hides_technical_answer_fields(self):
		component = VUE_PATH.read_text()
		self.assertIn("<EdgeAppShell", component)
		self.assertIn("<EdgePageLayout>", component)
		self.assertIn("Question Code", component)
		self.assertIn("Subject / Course", component)
		self.assertIn("Only Topics configured under the selected Course are shown", component)
		self.assertIn("Answer Choices", component)
		self.assertIn("Correct Answer", component)
		self.assertIn("Add Answer", component)
		self.assertIn('"True/False": ["True", "False"]', component)
		self.assertIn('"Yes/No": ["Yes", "No"]', component)
		self.assertIn("function blankQuestion", component)
		self.assertIn('question_type: "Single Choice"', component)
		self.assertIn("options: []", component)
		self.assertNotIn('v-model="answer.option_key"', component)
		self.assertNotIn('v-model="answer.display_order"', component)
		self.assertIn("optionLabel(index + 1)", component)
		self.assertIn("moveAnswer(index", component)

	def test_builder_uses_governed_server_apis_for_save_and_versioning(self):
		component = VUE_PATH.read_text()
		for method in (
			"get_question_builder_context",
			"search_courses",
			"search_topics",
			"save_question",
			"create_question_version",
		):
			self.assertIn(f"eduedge.api.question_builder.{method}", component)
		self.assertIn("Save Draft", component)
		self.assertIn("Send for Review", component)
		self.assertIn("Approve Question", component)
		self.assertIn("Retire Question", component)
		self.assertIn("Create New Version", component)
		self.assertIn("Open Technical Record", component)

	def test_api_reuses_doctype_permissions_and_validation(self):
		api = (ROOT / "eduedge" / "api" / "question_builder.py").read_text()
		self.assertIn("_require_question_author", api)
		self.assertIn('doc.has_permission("read")', api)
		self.assertIn('doc.has_permission("write")', api)
		self.assertIn('frappe.new_doc(QUESTION_DOCTYPE)', api)
		self.assertIn('doc.set("options", [])', api)
		self.assertIn("doc.insert()", api)
		self.assertIn("doc.save()", api)
		self.assertIn("course_topic_query", api)
		self.assertIn("get_allowed_school_branches", api)
		self.assertIn("get_public_exam_capability_summary", api)
		self.assertIn("can_review_questions", api)
		self.assertNotIn("REVIEW_ROLES", api)
		self.assertIn("Question Code cannot be changed after the first save", api)
		self.assertIn("frappe.copy_doc(source)", api)
		self.assertIn('doc.supersedes_question = source.name', api)
		self.assertIn('doc.status = "Draft"', api)

	def test_cbt_create_action_and_navigation_use_builder_same_tab(self):
		operations = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "page"
			/ "eduedge_cbt_operations"
			/ "eduedge_cbt_operations.js"
		).read_text()
		navigation = (ROOT / "eduedge" / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn('route: "/app/eduedge-question-builder"', operations)
		self.assertIn("edgesuite: true", operations)
		self.assertIn("openCreateRoute", operations)
		self.assertIn('"/app/eduedge-question-builder"', navigation)

	def test_ci_checks_new_entry_scripts(self):
		workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
		self.assertIn("eduedge/public/js/eduedge_question_builder.bundle.js", workflow)
		self.assertIn("eduedge/eduedge/page/eduedge_question_builder/eduedge_question_builder.js", workflow)


if __name__ == "__main__":
	unittest.main()
