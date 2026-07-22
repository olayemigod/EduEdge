import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_JS = ROOT / "eduedge" / "public" / "js"
EDITOR_JS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.js"
EDITOR_CSS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.css"
BUNDLE = PUBLIC_JS / "eduedge_question_builder.bundle.js"
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

	def test_bundle_installs_and_cleans_up_rich_text_enhancer(self):
		bundle = BUNDLE.read_text()
		self.assertIn("installQuestionRichTextEditor", bundle)
		self.assertIn('import "./eduedge_question_builder/rich_text_editor.css"', bundle)
		self.assertIn('viewModel.$options?.name !== "EduEdgeQuestionBuilder"', bundle)
		self.assertIn("mounted()", bundle)
		self.assertIn("updated()", bundle)
		self.assertIn("beforeUnmount()", bundle)
		self.assertIn(".refresh()", bundle)
		self.assertIn(".destroy()", bundle)

	def test_editor_fixes_direction_and_avoids_caret_rewriting(self):
		source = EDITOR_JS.read_text()
		self.assertIn('editor.setAttribute("dir", "ltr")', source)
		self.assertIn('editor.setAttribute("contenteditable"', source)
		self.assertIn('source.style.display = "none"', source)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', source)
		self.assertIn("MutationObserver", source)
		self.assertIn("document.activeElement !== editor", source)
		self.assertNotIn("editor.innerHTML = form.question_text", source)

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
		self.assertIn("last focused answer or answer-key field", source)

	def test_styles_force_left_to_right_readable_editor(self):
		styles = EDITOR_CSS.read_text()
		self.assertIn("direction: ltr", styles)
		self.assertIn("text-align: left", styles)
		self.assertIn("unicode-bidi: plaintext", styles)
		self.assertIn(".eduedge-rich-editor__surface sup", styles)
		self.assertIn(".eduedge-rich-editor__surface sub", styles)


if __name__ == "__main__":
	unittest.main()
