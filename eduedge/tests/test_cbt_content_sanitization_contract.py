from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCBTContentSanitizationContract(unittest.TestCase):
	def test_question_controller_sanitises_all_stored_content(self):
		controller = (
			APP
			/ "eduedge/doctype/eduedge_cbt_question/eduedge_cbt_question.py"
		).read_text()
		for expected in (
			"from frappe.utils import cint, flt, now_datetime, sanitize_html",
			"CONTENT_FIELDS",
			"def sanitize_question_content(value)",
			"self._sanitize_stored_content()",
			"def _sanitize_stored_content(self)",
			"row.option_text = sanitize_question_content",
			"before_value = sanitize_question_content(before_value)",
			"sanitize_question_content(row.option_text)",
		):
			self.assertIn(expected, controller)
		self.assertLess(
			controller.index("self._sanitize_stored_content()"),
			controller.index("self._validate_identity()"),
		)


if __name__ == "__main__":
	unittest.main()
