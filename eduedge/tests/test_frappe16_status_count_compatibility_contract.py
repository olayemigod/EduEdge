from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestFrappe16StatusCountCompatibilityContract(unittest.TestCase):
	def test_question_and_template_lists_use_permission_aware_python_counts(self):
		for relative_path in (
			"api/question_bank.py",
			"api/exam_templates_list.py",
		):
			source = (APP / relative_path).read_text(encoding="utf-8")
			self.assertIn('fields=["status"]', source, relative_path)
			self.assertIn("limit_page_length=0", source, relative_path)
			self.assertIn('counts = {"Total": len(rows)', source, relative_path)
			self.assertNotIn("frappe.db.count(", source, relative_path)
			self.assertNotIn("count(name) as count", source, relative_path)


if __name__ == "__main__":
	unittest.main()
