import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_builder.bundle.js"
RUNTIME = ROOT / "eduedge" / "public" / "js" / "eduedge_question_rich_text.bundle.js"
LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_builder"
	/ "eduedge_question_builder.js"
)
CSS = ROOT / "eduedge" / "public" / "css" / "eduedge_question_rich_text.bundle.css"


class TestQuestionBuilderRichEditorRuntimeContract(unittest.TestCase):
	def test_page_loader_owns_shared_editor_lifecycle(self):
		loader = LOADER.read_text()
		self.assertIn('"eduedge_question_rich_text.bundle.js"', loader)
		self.assertIn("window.installEduEdgeQuestionRichTextEditors(root[0])", loader)
		self.assertIn("wrapper.rich_text_runtime?.destroy?.()", loader)
		self.assertLess(
			loader.index('"eduedge_question_rich_text.bundle.js"'),
			loader.index("window.installEduEdgeQuestionRichTextEditors(root[0])"),
		)

	def test_builder_bundle_does_not_mount_a_duplicate_editor(self):
		bundle = BUNDLE.read_text()
		self.assertIn("return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps)", bundle)
		self.assertNotIn("installQuestionRichTextEditor", bundle)
		self.assertNotIn("EduEdgeQuestionBuilder.updated", bundle)
		self.assertNotIn("app.mount =", bundle)

	def test_shared_runtime_detects_single_question_source(self):
		runtime = RUNTIME.read_text()
		self.assertIn('.eduedge-question-editor', runtime)
		self.assertIn('document.activeElement !== editor', runtime)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', runtime)

	def test_page_loads_explicit_shared_css_before_mount(self):
		loader = LOADER.read_text()
		self.assertIn('"eduedge_question_rich_text.bundle.css"', loader)
		self.assertIn('"eduedge_question_builder.bundle.js"', loader)
		self.assertLess(
			loader.index('"eduedge_question_rich_text.bundle.css"'),
			loader.index("window.createEduEdgeQuestionBuilderApp"),
		)

	def test_explicit_css_contains_toolbar_and_surface_contracts(self):
		css = CSS.read_text()
		self.assertIn(".eduedge-rich-editor__toolbar", css)
		self.assertIn(".eduedge-rich-editor__button", css)
		self.assertIn(".eduedge-rich-editor__surface", css)
		self.assertIn(".eduedge-rich-editor__symbols", css)


if __name__ == "__main__":
	unittest.main()
