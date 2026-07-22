import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAFE_API = ROOT / "eduedge" / "api" / "question_batch_safe.py"
HOOKS = ROOT / "eduedge" / "hooks.py"
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_batch.bundle.js"
EDITOR = ROOT / "eduedge" / "public" / "js" / "eduedge_question_batch" / "batch_rich_text_editor.js"


class TestQuestionBatchAccessAndEditorContract(unittest.TestCase):
	def test_upload_access_is_permission_backed_and_fail_closed(self):
		source = SAFE_API.read_text()
		self.assertIn('frappe.has_permission(QUESTION_DOCTYPE, "import")', source)
		self.assertIn("_require_upload_permission()", source)
		self.assertIn("You are not permitted to upload or import CBT questions", source)
		self.assertIn('if source == "upload"', source)
		self.assertIn("def preview_question_upload", source)
		self.assertIn("def import_question_upload", source)

	def test_whitelisted_upload_paths_use_safe_wrappers(self):
		hooks = HOOKS.read_text()
		for original, safe in (
			("eduedge.api.question_batch.save_question_batch", "eduedge.api.question_batch_safe.save_question_batch"),
			("eduedge.api.question_batch.preview_question_upload", "eduedge.api.question_batch_safe.preview_question_upload"),
			("eduedge.api.question_upload.import_question_upload", "eduedge.api.question_batch_safe.import_question_upload"),
		):
			self.assertIn(f'"{original}": "{safe}"', hooks)

	def test_batch_bundle_hides_upload_until_permission_is_confirmed(self):
		bundle = BUNDLE.read_text()
		self.assertIn("get_question_upload_access", bundle)
		self.assertIn("eduedgeUploadAccessResolved", bundle)
		self.assertIn("eduedgeCanUpload", bundle)
		self.assertIn("uploadTab.hidden = !visible", bundle)
		self.assertIn('mode === "upload"', bundle)
		self.assertIn('baseMethods.setMode.call(viewModel, "entry")', bundle)

	def test_new_question_is_inserted_at_top_and_focused(self):
		bundle = BUNDLE.read_text()
		self.assertIn("const newest = this.questions.pop()", bundle)
		self.assertIn("this.questions.unshift(newest)", bundle)
		self.assertIn('.querySelector(".eduedge-question-card input.form-control")?.focus()', bundle)

	def test_manual_cards_receive_rich_text_and_answer_symbol_support(self):
		bundle = BUNDLE.read_text()
		editor = EDITOR.read_text()
		self.assertIn("installBatchQuestionRichTextEditors", bundle)
		self.assertIn('import "./eduedge_question_builder/rich_text_editor.css"', bundle)
		self.assertIn("installQuestionRichTextEditor", editor)
		self.assertIn("eduedge-batch-question-editor-source", editor)
		self.assertIn("textarea.dispatchEvent(new Event(\"input\", { bubbles: true }))", editor)
		self.assertIn('row.classList.add("eduedge-answer-row")', editor)
		self.assertIn('card.classList.add("eduedge-question-panel--editor")', editor)
		self.assertIn("MutationObserver", editor)


if __name__ == "__main__":
	unittest.main()
