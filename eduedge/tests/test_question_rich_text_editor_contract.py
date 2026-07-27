import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_JS = ROOT / "eduedge" / "public" / "js"
EDITOR_JS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.js"
LEGACY_EDITOR_CSS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.css"
EXPLICIT_EDITOR_CSS = ROOT / "eduedge" / "public" / "css" / "eduedge_question_builder.bundle.css"
BUNDLE = PUBLIC_JS / "eduedge_question_builder.bundle.js"
PAGE_LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_builder"
	/ "eduedge_question_builder.js"
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

	def test_bundle_owns_editor_lifecycle_without_replacing_mount(self):
		bundle = BUNDLE.read_text()
		self.assertIn("installQuestionRichTextEditor", bundle)
		self.assertIn("EduEdgeQuestionBuilder.mounted", bundle)
		self.assertIn("EduEdgeQuestionBuilder.updated", bundle)
		self.assertIn("EduEdgeQuestionBuilder.beforeUnmount", bundle)
		self.assertIn("return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps)", bundle)
		self.assertNotIn("app.mount =", bundle)

	def test_page_loader_uses_explicit_css_and_no_duplicate_toolbar_runtime(self):
		loader = PAGE_LOADER.read_text()
		self.assertIn('"eduedge_question_builder.bundle.css"', loader)
		self.assertIn('"eduedge_question_builder.bundle.js"', loader)
		self.assertIn("wrapper.vue_app.mount(root[0])", loader)
		self.assertNotIn("installQuestionToolbar", loader)
		self.assertNotIn("MutationObserver", loader)
		self.assertNotIn("setInterval", loader)

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
		):
			self.assertIn(command, source)
		for symbol in ("²", "³", "₁", "₂", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"):
			self.assertIn(symbol, source)
		self.assertIn("setRangeText", source)
		self.assertIn("last focused answer or answer-key field", source)

	def test_enhancer_avoids_caret_rewriting(self):
		source = EDITOR_JS.read_text()
		self.assertIn('editor.setAttribute("dir", "ltr")', source)
		self.assertIn('editor.contentEditable = readOnly ? "false" : "true"', source)
		self.assertIn('source.style.display = "none"', source)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', source)
		self.assertIn("MutationObserver", source)
		self.assertIn("document.activeElement !== editor", source)
		self.assertNotIn("editor.innerHTML = form.question_text", source)

	def test_explicit_styles_force_left_to_right_readable_editor(self):
		styles = EXPLICIT_EDITOR_CSS.read_text()
		self.assertIn("direction: ltr", styles)
		self.assertIn("text-align: left", styles)
		self.assertIn("unicode-bidi: plaintext", styles)
		self.assertIn(".eduedge-rich-editor__surface sup", styles)
		self.assertIn(".eduedge-rich-editor__surface sub", styles)
		self.assertEqual(LEGACY_EDITOR_CSS.read_text().strip(), styles.split("*/", 1)[1].strip())


if __name__ == "__main__":
	unittest.main()
