import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "eduedge" / "public" / "js" / "eduedge_question_rich_text.bundle.js"
STYLE = ROOT / "eduedge" / "public" / "css" / "eduedge_question_rich_text.bundle.css"
BUILDER_BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_builder.bundle.js"
BUILDER_LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_builder"
	/ "eduedge_question_builder.js"
)
BATCH_LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_batch"
	/ "eduedge_question_batch.js"
)


class TestSharedQuestionRichTextContract(unittest.TestCase):
	def test_runtime_supports_single_and_multiple_question_sources(self):
		runtime = RUNTIME.read_text()
		self.assertIn('.eduedge-question-editor', runtime)
		self.assertIn('.eduedge-question-card', runtime)
		self.assertIn(':scope > .eduedge-batch-field--wide > textarea', runtime)
		self.assertIn('window.installEduEdgeQuestionRichTextEditors', runtime)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', runtime)

	def test_toolbar_preserves_required_formatting_and_symbols(self):
		runtime = RUNTIME.read_text()
		for command in (
			'"bold"',
			'"italic"',
			'"underline"',
			'"superscript"',
			'"subscript"',
			'"insertUnorderedList"',
			'"insertOrderedList"',
			'"removeFormat"',
		):
			self.assertIn(command, runtime)
		for symbol in ("²", "³", "₀", "₁", "₂", "₃", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"):
			self.assertIn(symbol, runtime)

	def test_typing_surface_is_not_rewritten_while_focused(self):
		runtime = RUNTIME.read_text()
		self.assertIn('document.activeElement !== editor', runtime)
		self.assertNotIn('editor.innerHTML = sourceValue(source);\n\t\tupdateSource', runtime)

	def test_shared_style_bundle_covers_toolbar_and_multiple_cards(self):
		style = STYLE.read_text()
		self.assertIn('.eduedge-rich-editor__toolbar', style)
		self.assertIn('.eduedge-rich-editor__surface', style)
		self.assertIn('.eduedge-question-card .eduedge-rich-editor__surface', style)
		self.assertIn('.eduedge-rich-editor.is-read-only', style)

	def test_both_page_loaders_mount_and_destroy_shared_runtime(self):
		for loader_path in (BUILDER_LOADER, BATCH_LOADER):
			loader = loader_path.read_text()
			self.assertIn('"eduedge_question_rich_text.bundle.css"', loader)
			self.assertIn('"eduedge_question_rich_text.bundle.js"', loader)
			self.assertIn('window.installEduEdgeQuestionRichTextEditors(root[0])', loader)
			self.assertIn('wrapper.rich_text_runtime?.destroy?.()', loader)

	def test_legacy_builder_dom_enhancer_is_not_mounted_twice(self):
		bundle = BUILDER_BUNDLE.read_text()
		self.assertNotIn('installQuestionRichTextEditor', bundle)
		self.assertNotIn('mountedWithRichTextEditor', bundle)
		self.assertNotIn('updatedWithRichTextEditor', bundle)


if __name__ == "__main__":
	unittest.main()
