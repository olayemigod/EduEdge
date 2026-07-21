import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TestQuestionBatchContract(unittest.TestCase):
	def test_question_batch_page_is_permission_driven_edgesuite_page(self):
		page_root = ROOT / "eduedge" / "eduedge" / "page" / "eduedge_question_batch"
		payload = json.loads((page_root / "eduedge_question_batch.json").read_text())
		self.assertEqual(payload["name"], "eduedge-question-batch")
		self.assertEqual(payload["roles"], [])

		access = (ROOT / "eduedge" / "access_control.py").read_text()
		self.assertIn('"/app/eduedge-question-batch": (("cbt_question", "create"),)', access)

		loader = (page_root / "eduedge_question_batch.js").read_text()
		self.assertIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertIn('frappe.require("eduedge_question_batch.bundle.js"', loader)
		self.assertIn("window.createEduEdgeQuestionBatchApp", loader)
		self.assertIn("resolveBatchMode", loader)
		self.assertIn('mode === "upload"', loader)

	def test_question_batch_route_is_registered_as_edgesuite_ui(self):
		navigation = (ROOT / "eduedge" / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn('"/app/eduedge-question-batch"', navigation)

		loader = (
			ROOT
			/ "eduedge"
			/ "eduedge"
			/ "page"
			/ "eduedge_cbt_operations"
			/ "eduedge_cbt_operations.js"
		).read_text()
		self.assertIn('label: "Single Question"', loader)
		self.assertIn('label: "Multiple Questions"', loader)
		self.assertIn('label: "Upload Questions"', loader)
		self.assertIn('route: "/app/eduedge-question-batch?mode=entry"', loader)
		self.assertIn('route: "/app/eduedge-question-batch?mode=upload"', loader)

	def test_manual_batch_is_limited_draft_only_and_controller_validated(self):
		api = (ROOT / "eduedge" / "api" / "question_batch.py").read_text()
		self.assertIn("MAX_MANUAL_QUESTIONS = 50", api)
		self.assertIn("MAX_UPLOAD_ROWS = 500", api)
		self.assertIn("MAX_UPLOAD_BYTES = 5 * 1024 * 1024", api)
		self.assertIn('doc.status = "Draft"', api)
		self.assertIn('doc.run_method("validate")', api)
		self.assertIn("doc.insert()", api)
		self.assertIn("_duplicate_codes", api)
		self.assertIn('frappe.has_permission(QUESTION_DOCTYPE, "create")', api)
		self.assertNotIn("ignore_permissions=True", api)
		self.assertNotIn("frappe.db.commit", api)

	def test_upload_preview_supports_csv_xlsx_and_blocks_invalid_rows(self):
		api = (ROOT / "eduedge" / "api" / "question_batch.py").read_text()
		for marker in (
			"def _parse_csv",
			"def _parse_xlsx",
			"load_workbook",
			"base64.b64decode",
			"Only CSV and XLSX question files are supported",
			"Question Code is repeated in this file",
			"Question Code already exists",
			'"can_import": bool(preview) and all(row["valid"] for row in preview)',
		):
			self.assertIn(marker, api)

		import_api = (ROOT / "eduedge" / "api" / "question_upload.py").read_text()
		self.assertIn("_parse_upload(file_name, _decode_upload(file_content))", import_api)
		self.assertIn('doc.run_method("validate")', import_api)
		self.assertIn("doc.insert()", import_api)
		self.assertNotIn("frappe.db.commit", import_api)
		self.assertNotIn("ignore_permissions=True", import_api)

	def test_question_batch_ui_has_shared_context_entry_and_preview(self):
		component = (
			ROOT
			/ "eduedge"
			/ "public"
			/ "js"
			/ "eduedge_question_batch"
			/ "EduEdgeQuestionBatch.vue"
		).read_text()
		for marker in (
			"Multiple Entry",
			"Upload Questions",
			"Apply once to every question",
			"School Branch / Campus",
			"Subject / Course",
			"Only Topics configured under the selected Course are shown",
			"Add Question",
			"Save ${questions.length} Draft Question",
			"Download CSV Template",
			'accept=".csv,.xlsx"',
			"Validate File",
			"Resolve every validation error before importing",
			"eduedge.api.question_batch.save_question_batch",
			"eduedge.api.question_batch.preview_question_upload",
			"eduedge.api.question_upload.import_question_upload",
		):
			self.assertIn(marker, component)
		self.assertIn('"True/False": ["True", "False"]', component)
		self.assertIn('"Yes/No": ["Yes", "No"]', component)
		self.assertIn("while (question.options.length < 2)", component)
		self.assertIn('question.question_type === "Multiple Choice"', component)
		self.assertIn("The operation is all-or-nothing", component)

	def test_upload_template_documents_answer_key_conventions(self):
		component = (
			ROOT
			/ "eduedge"
			/ "public"
			/ "js"
			/ "eduedge_question_batch"
			/ "EduEdgeQuestionBatch.vue"
		).read_text()
		for column in (
			"question_code",
			"question_type",
			"question",
			"answer_a",
			"answer_h",
			"correct_answers",
			"answer_key",
			"marking_guide",
			"default_mark",
			"negative_mark",
		):
			self.assertIn(f'"{column}"', component)
		self.assertIn("B|D", component)
		self.assertIn("Yes/No and True/False answers are generated automatically", component)


if __name__ == "__main__":
	unittest.main()
