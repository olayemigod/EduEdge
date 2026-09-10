from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEduEdgeLinkFieldRuntimeContract(unittest.TestCase):
	def test_product_runtime_registers_same_bundle_stateful_components_after_edgesuite_install(self):
		factory = (APP / "public/js/eduedge_ui/app_factory.js").read_text(encoding="utf-8")
		for expected in (
			'import EdgeModalFallback from "./components/EdgeModalFallback.vue";',
			'import EdgeLinkFieldFallback from "./components/EdgeLinkFieldFallback.vue";',
			'import EdgeFormDialogFallback from "./components/EdgeFormDialogFallback.vue";',
			'app.component("EdgeModal", EdgeModalFallback);',
			'app.component("EdgeLinkField", EdgeLinkFieldFallback);',
			'app.component("EdgeFormDialog", EdgeFormDialogFallback);',
		):
			self.assertIn(expected, factory)
		for registration in (
			'app.component("EdgeModal"',
			'app.component("EdgeLinkField"',
			'app.component("EdgeFormDialog"',
		):
			self.assertLess(factory.index("runtime.install(app);"), factory.index(registration))
		self.assertNotIn("registerFallbackComponent", factory)

	def test_link_field_fallback_preserves_smart_search_and_selection_contract(self):
		component_path = APP / "public/js/eduedge_ui/components/EdgeLinkFieldFallback.vue"
		self.assertTrue(component_path.exists())
		component = component_path.read_text(encoding="utf-8")
		for expected in (
			'name: "EdgeLinkFieldFallback"',
			"searcher:",
			"context:",
			"selectedLabel:",
			"openOnFocus:",
			"debounceMs:",
			'"update:model-value"',
			'"query-change"',
			'"select"',
			'"clear"',
			"await this.searcher(cleaned",
			"requestSerial",
			"handleOutsidePointer",
			"moveActive",
			"selectActive",
		):
			self.assertIn(expected, component)

	def test_form_dialog_requests_remote_link_options_when_field_opens(self):
		dialog = (
			APP / "public/js/eduedge_ui/components/EdgeFormDialogFallback.vue"
		).read_text(encoding="utf-8")
		self.assertIn('@open="requestOptions(field, \'\')"', dialog)
		self.assertIn('@query-change="requestOptions(field, $event)"', dialog)
		self.assertIn('this.$emit("search-options", { field, query: query || ""', dialog)

	def test_question_responsibility_dialog_uses_remote_user_and_course_options(self):
		responsibilities = (
			APP / "public/js/eduedge_question_responsibilities/EduEdgeQuestionResponsibilities.vue"
		).read_text(encoding="utf-8")
		for expected in (
			'{ fieldname: "user", type: "Link"',
			'{ fieldname: "course", type: "Link"',
			'@search-options="searchModalOptions"',
			"eduedge.api.question_responsibilities.search_options",
			"options: response.message || []",
		):
			self.assertIn(expected, responsibilities)

	def test_question_responsibility_toggle_uses_same_runtime_modal_and_refreshes_context(self):
		modal = (
			APP / "public/js/eduedge_ui/components/EdgeModalFallback.vue"
		).read_text(encoding="utf-8")
		responsibilities = (
			APP / "public/js/eduedge_question_responsibilities/EduEdgeQuestionResponsibilities.vue"
		).read_text(encoding="utf-8")
		for expected in (
			'name: "EdgeModalFallback"',
			'<slot name="footer" />',
			'emits: ["close"]',
			'@click="executeToggle"',
			"eduedge.api.question_responsibilities.set_enabled",
			"await this.loadContext();",
		):
			self.assertIn(expected, modal if expected in modal else responsibilities)

	def test_question_and_template_pages_continue_to_use_permission_aware_link_search(self):
		question = (
			APP / "public/js/eduedge_question_bank/EduEdgeQuestionBank.vue"
		).read_text(encoding="utf-8")
		templates = (
			APP / "public/js/eduedge_exam_templates/EduEdgeExamTemplates.vue"
		).read_text(encoding="utf-8")
		for source in (question, templates):
			self.assertIn("<EdgeLinkField", source)
			self.assertIn(':searcher="searchCourses"', source)
			self.assertIn('@update:model-value="courseValueChanged"', source)
			self.assertIn('@select="courseSelected"', source)
			self.assertIn('@clear="courseCleared"', source)


if __name__ == "__main__":
	unittest.main()
