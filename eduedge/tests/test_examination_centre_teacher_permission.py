import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CENTRE_JSON = (
	ROOT
	/ "eduedge"
	/ "eduedge"
	/ "doctype"
	/ "eduedge_examination_centre"
	/ "eduedge_examination_centre.json"
)


class TestExaminationCentreTeacherPermission(unittest.TestCase):
	def test_teacher_has_branch_safe_read_only_centre_access(self):
		payload = json.loads(CENTRE_JSON.read_text())
		permissions = {row["role"]: row for row in payload["permissions"]}
		teacher = permissions["Teacher"]

		for permission in ("read", "report", "print", "export"):
			self.assertEqual(teacher.get(permission), 1)

		for permission in ("create", "write", "delete", "import", "share"):
			self.assertFalse(teacher.get(permission, 0))

	def test_teacher_remains_covered_by_branch_permission_hooks(self):
		permissions = (ROOT / "eduedge" / "cbt" / "permissions.py").read_text()
		self.assertIn('"Teacher"', permissions)
		self.assertIn("def examination_centre_query", permissions)
		self.assertIn("def has_school_branch_permission", permissions)
		self.assertIn("if not branch:", permissions)
		self.assertIn("return False", permissions)


if __name__ == "__main__":
	unittest.main()
