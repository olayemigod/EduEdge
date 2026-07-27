import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_JS = ROOT / "eduedge" / "public" / "js"
EDITOR_JS = PUBLIC_JS / "eduedge_question_rich_text.bundle.js"
EXPLICIT_EDITOR_CSS = ROOT / "eduedge" / "public" / "css" / "eduedge_question_rich_text.bundle.css"
BUNDLE = PUBLIC_JS / "eduedge_question_builder.bundle.js"
PAGE_LOADER = (
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
QUESTION_META = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "doctype"
	/ "eduedge_cbt_question"
	/ "eduedge_cbt_question.json"
)


class TestQuestionRichTextEditorContract(unittest.TestCase):
	def test_question_remains_a_frappe_text_editor_field(self):
		metadata = json.loads(QUESTION_META.read_text())
		fields = {field["fieldname"]: field for field in metadata["fields"]}
		self.assertEqual(fields["question_text"]["fieldtype"], "Text Editor")

	def test_shared_runtime_is_loaded_by_single_and_multiple_entry(self):
		for loader_path in (PAGE_LOADER, BATCH_LOADER):
			loader = loader_path.read_text()
			self.assertIn('"eduedge_question_rich_text.bundle.css"', loader)
			self.assertIn('"eduedge_question_rich_text.bundle.js"', loader)
			self.assertIn("window.installEduEdgeQuestionRichTextEditors(root[0])", loader)
			self.assertIn("wrapper.rich_text_runtime?.destroy?.()", loader)

	def test_builder_bundle_uses_normal_vue_mount_without_duplicate_toolbar(self):
		bundle = BUNDLE.read_text()
		self.assertIn("return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps)", bundle)
		self.assertNotIn("installQuestionRichTextEditor", bundle)
		self.assertNotIn("app.mount =", bundle)

	def test_editor_supports_required_formatting_and_symbols(self):
		source = EDITOR_JS.read_text()
		for command in (
			'command: "bold"',
			'command: "italic"',
			'command: "underline"',
			'command: "superscript"',
			'command: "subscript"',
			'command: "insertUnorderedList"',
			'command: "insertOrderedList"',
			'command: "removeFormat"',
		):
			self.assertIn(command, source)
		for symbol in ("²", "³", "₀", "₁", "₂", "₃", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"):
			self.assertIn(symbol, source)

	def test_enhancer_avoids_caret_rewriting(self):
		source = EDITOR_JS.read_text()
		self.assertIn('editor.setAttribute("dir", "ltr")', source)
		self.assertIn('editor.contentEditable = disabled ? "false" : "true"', source)
		self.assertIn('source.style.display = "none"', source)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', source)
		self.assertIn("MutationObserver", source)
		self.assertIn("document.activeElement !== editor", source)
		self.assertNotIn("editor.innerHTML = form.question_text", source)

	def test_runtime_detects_single_and_multiple_question_fields(self):
		source = EDITOR_JS.read_text()
		self.assertIn('.eduedge-question-editor', source)
		self.assertIn('.eduedge-question-card', source)
		self.assertIn(':scope > .eduedge-batch-field--wide > textarea', source)

	def test_explicit_styles_force_left_to_right_readable_editor(self):
		styles = EXPLICIT_EDITOR_CSS.read_text()
		self.assertIn("direction: ltr", styles)
		self.assertIn("text-align: left", styles)
		self.assertIn("unicode-bidi: plaintext", styles)
		self.assertIn(".eduedge-rich-editor__surface sup", styles)
		self.assertIn(".eduedge-rich-editor__surface sub", styles)
		self.assertIn(".eduedge-question-card .eduedge-rich-editor__surface", styles)


if __name__ == "__main__":
	unittest.main()
