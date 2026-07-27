import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_builder.bundle.js"
LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_builder"
	/ "eduedge_question_builder.js"
)
CSS = ROOT / "eduedge" / "public" / "css" / "eduedge_question_builder.bundle.css"


class TestQuestionBuilderRichEditorRuntimeContract(unittest.TestCase):
	def test_vue_bundle_owns_rich_editor_lifecycle(self):
		bundle = BUNDLE.read_text()
		self.assertIn("installQuestionRichTextEditor", bundle)
		self.assertIn("EduEdgeQuestionBuilder.mounted", bundle)
		self.assertIn("EduEdgeQuestionBuilder.updated", bundle)
		self.assertIn("EduEdgeQuestionBuilder.beforeUnmount", bundle)
		self.assertIn("_eduedgeRichTextEditor?.refresh?.()", bundle)
		self.assertIn("_eduedgeRichTextEditor?.destroy?.()", bundle)

	def test_page_loads_explicit_editor_css_before_mount(self):
		loader = LOADER.read_text()
		self.assertIn('"eduedge_question_builder.bundle.css"', loader)
		self.assertIn('"eduedge_question_builder.bundle.js"', loader)
		self.assertLess(
			loader.index('"eduedge_question_builder.bundle.css"'),
			loader.index("window.createEduEdgeQuestionBuilderApp"),
		)
		self.assertNotIn("installQuestionToolbar", loader)
		self.assertNotIn("MutationObserver", loader)
		self.assertNotIn("setInterval", loader)

	def test_explicit_css_contains_toolbar_and_surface_contracts(self):
		css = CSS.read_text()
		self.assertIn(".eduedge-rich-editor__toolbar", css)
		self.assertIn(".eduedge-rich-editor__button", css)
		self.assertIn(".eduedge-rich-editor__surface", css)
		self.assertIn(".eduedge-rich-editor__symbols", css)


if __name__ == "__main__":
	unittest.main()
