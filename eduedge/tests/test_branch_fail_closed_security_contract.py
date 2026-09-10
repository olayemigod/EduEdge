from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBranchFailClosedSecurityContract(unittest.TestCase):
	def test_education_branch_scope_uses_empty_set_not_none_bypass(self):
		source = (APP / "education/permissions.py").read_text()
		self.assertIn("def _allowed_branch_names(user: str) -> set[str]:", source)
		self.assertIn("return set()", source)
		self.assertIn('if not allowed:\n\t\treturn "1=0"', source)
		self.assertNotIn("if allowed is None:", source)
		self.assertNotIn("return None", source)

	def test_cbt_branch_scope_uses_empty_collections_not_none_bypass(self):
		source = (APP / "cbt/permissions.py").read_text()
		self.assertIn("def _allowed_branch_rows(user: str) -> list[dict]:", source)
		self.assertIn("return []", source)
		self.assertIn("def _allowed_branch_names(user: str) -> set[str]:", source)
		self.assertNotIn("if allowed is None:", source)
		self.assertNotIn("if rows is None:", source)
		self.assertNotIn("return None", source)

	def test_review_workbench_is_explicitly_in_access_manifest(self):
		access = (APP / "access_control.py").read_text()
		self.assertIn('"/app/eduedge-cbt-review-workbench"', access)
		self.assertNotIn('"/app/eduedge-cbt-attempt-review":', access)


if __name__ == "__main__":
	unittest.main()
