import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_batch"
	/ "eduedge_question_batch.js"
)
CSS_BUNDLE = (
	ROOT
	/ "eduedge"
	/ "public"
	/ "css"
	/ "eduedge_question_batch.bundle.css"
)


class TestQuestionBatchAssetLoadingContract(unittest.TestCase):
	def test_page_loads_component_css_before_mounting(self):
		loader = LOADER.read_text()
		self.assertIn('"eduedge_question_batch.bundle.css"', loader)
		self.assertIn('"eduedge_question_batch.bundle.js"', loader)
		self.assertIn("frappe.require(", loader)
		self.assertLess(
			loader.index('"eduedge_question_batch.bundle.css"'),
			loader.index("window.createEduEdgeQuestionBatchApp"),
		)

	def test_explicit_css_bundle_contains_page_layout_contract(self):
		self.assertTrue(CSS_BUNDLE.exists())
		styles = CSS_BUNDLE.read_text()
		for selector in (
			".eduedge-batch-tabs",
			".eduedge-batch-panel",
			".eduedge-common-fields",
			".eduedge-question-card",
			".eduedge-card-answer-row",
			".eduedge-upload-drop",
		):
			self.assertIn(selector, styles)
		self.assertNotIn("<style", styles)


if __name__ == "__main__":
	unittest.main()
