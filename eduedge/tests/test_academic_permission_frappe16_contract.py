import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PERMISSIONS = ROOT / "eduedge" / "education" / "academic_permissions.py"


class TestAcademicPermissionFrappe16Contract(unittest.TestCase):
	def test_has_permission_hook_returns_explicit_boolean_decisions(self):
		source = PERMISSIONS.read_text()
		module = ast.parse(source)
		function = next(
			node
			for node in module.body
			if isinstance(node, ast.FunctionDef)
			and node.name == "has_academic_institution_permission"
		)
		returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
		self.assertTrue(returns)
		self.assertFalse(
			any(node.value is None or isinstance(node.value, ast.Constant) and node.value.value is None for node in returns)
		)
		function_source = ast.get_source_segment(source, function) or ""
		self.assertIn("return True", function_source)
		self.assertIn("return False", function_source)
		self.assertIn("return institution in _allowed_institutions(resolved_user)", function_source)

	def test_legacy_unclassified_academic_masters_fail_closed_for_scoped_users(self):
		source = PERMISSIONS.read_text()
		self.assertNotIn("coalesce(`tab{doctype}`.`{fieldname}`, '') = ''", source)
		self.assertIn("Fail closed for restricted users", source)
		self.assertIn('"Course",', source)
		self.assertIn('"EduEdge Super Administrator"', source)


if __name__ == "__main__":
	unittest.main()
