from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestEduEdgeLinkFieldRuntimeContract(unittest.TestCase):
	def test_product_runtime_registers_same_bundle_link_field_after_edgesuite_install(self):
		factory = (APP / "public/js/eduedge_ui/app_factory.js").read_text(encoding="utf-8")
		self.assertIn('import EdgeLinkFieldFallback from "./components/EdgeLinkFieldFallback.vue";', factory)
		self.assertIn('app.component("EdgeLinkField", EdgeLinkFieldFallback);', factory)
		self.assertLess(factory.index("runtime.install(app);"), factory.index('app.component("EdgeLinkField"'))

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
