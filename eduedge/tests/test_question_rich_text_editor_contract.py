import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_JS = ROOT / "eduedge" / "public" / "js"
EDITOR_JS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.js"
EDITOR_CSS = PUBLIC_JS / "eduedge_question_builder" / "rich_text_editor.css"
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

	def test_bundle_keeps_native_edgesuite_mount_and_loads_toolbar_styles(self):
		bundle = BUNDLE.read_text()
		self.assertIn('import "./eduedge_question_builder/rich_text_editor.css"', bundle)
		self.assertIn("return createEduEdgeApp(EduEdgeQuestionBuilder, rootProps)", bundle)
		self.assertNotIn("app.mount =", bundle)
		self.assertNotIn("MutationObserver", bundle)

	def test_page_loader_installs_toolbar_on_the_actual_question_root(self):
		loader = PAGE_LOADER.read_text()
		self.assertIn("installQuestionToolbar", loader)
		self.assertIn('root.querySelector(".eduedge-question-editor")', loader)
		self.assertIn("MutationObserver", loader)
		self.assertIn("window.setInterval(ensureToolbar, 500)", loader)
		self.assertIn("wrapper.question_toolbar = installQuestionToolbar(root[0])", loader)
		self.assertIn("wrapper.question_toolbar?.destroy()", loader)
		self.assertIn('editor.setAttribute("dir", "ltr")', loader)
		self.assertIn('editor.dispatchEvent(new Event("input", { bubbles: true }))', loader)

	def test_page_toolbar_supports_required_formatting_and_symbols(self):
		loader = PAGE_LOADER.read_text()
		for command in (
			'command: "bold"',
			'command: "italic"',
			'command: "underline"',
			'command: "superscript"',
			'command: "subscript"',
			'command: "insertUnorderedList"',
			'command: "insertOrderedList"',
		):
			self.assertIn(command, loader)
		for symbol in ("²", "³", "₁", "₂", "√", "π", "θ", "Δ", "∑", "∞", "×", "÷", "±", "≤", "≥", "≠", "°"):
			self.assertIn(symbol, loader)
		self.assertIn("setRangeText", loader)
		self.assertIn("last focused answer, answer-key or marking-guide field", loader)

	def test_legacy_enhancer_avoids_caret_rewriting(self):
		source = EDITOR_JS.read_text()
		self.assertIn('editor.setAttribute("dir", "ltr")', source)
		self.assertIn('editor.contentEditable = readOnly ? "false" : "true"', source)
		self.assertIn('source.style.display = "none"', source)
		self.assertIn('source.dispatchEvent(new Event("input", { bubbles: true }))', source)
		self.assertIn("MutationObserver", source)
		self.assertIn("document.activeElement !== editor", source)
		self.assertNotIn("editor.innerHTML = form.question_text", source)

	def test_styles_force_left_to_right_readable_editor(self):
		styles = EDITOR_CSS.read_text()
		self.assertIn("direction: ltr", styles)
		self.assertIn("text-align: left", styles)
		self.assertIn("unicode-bidi: plaintext", styles)
		self.assertIn(".eduedge-rich-editor__surface sup", styles)
		self.assertIn(".eduedge-rich-editor__surface sub", styles)


if __name__ == "__main__":
	unittest.main()
