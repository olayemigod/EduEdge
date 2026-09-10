import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BATCH_API = ROOT / "eduedge" / "api" / "question_batch.py"
UPLOAD_API = ROOT / "eduedge" / "api" / "question_upload.py"
BUNDLE = ROOT / "eduedge" / "public" / "js" / "eduedge_question_batch.bundle.js"
LOADER = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "page"
	/ "eduedge_question_batch"
	/ "eduedge_question_batch.js"
)
PERMISSION_CSS = ROOT / "eduedge" / "public" / "css" / "eduedge_question_batch_permissions.bundle.css"


class TestQuestionBatchImportPermissionContract(unittest.TestCase):
	def test_server_separates_manual_create_from_file_import(self):
		batch_api = BATCH_API.read_text()
		self.assertIn('frappe.has_permission(QUESTION_DOCTYPE, "import")', batch_api)
		self.assertIn('"can_upload": _has_import_permission()', batch_api)
		self.assertIn('if source == "upload":', batch_api)
		self.assertIn("_require_import_permission()", batch_api)
		self.assertIn("def preview_question_upload", batch_api)

		upload_api = UPLOAD_API.read_text()
		self.assertIn("_require_import_permission,", upload_api)
		self.assertIn("def import_question_upload", upload_api)
		self.assertIn("\t_require_import_permission()", upload_api)

	def test_ui_fails_closed_until_import_permission_is_confirmed(self):
		bundle = BUNDLE.read_text()
		self.assertIn("const originalLoadContext", bundle)
		self.assertIn('setAttribute("data-can-upload", "0")', bundle)
		self.assertIn("Boolean(this.context?.can_upload)", bundle)
		self.assertIn('this.setMode("entry")', bundle)

		loader = LOADER.read_text()
		self.assertIn('"eduedge_question_batch_permissions.bundle.css"', loader)
		self.assertIn('data-can-upload="0"', loader)

		permission_css = PERMISSION_CSS.read_text()
		self.assertIn(':not([data-can-upload="1"])', permission_css)
		self.assertIn("button:nth-child(2)", permission_css)


if __name__ == "__main__":
	unittest.main()
