import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ACADEMIC_PERMISSIONS = ROOT / "eduedge" / "education" / "academic_permissions.py"
BRANCH_CONTEXT = ROOT / "eduedge" / "services" / "branch_context.py"
QUESTION_BUILDER = ROOT / "eduedge" / "api" / "question_builder.py"
QUESTION_BATCH = ROOT / "eduedge" / "api" / "question_batch.py"


class TestCustomRoleAcademicScopeContract(unittest.TestCase):
	def test_custom_roles_are_scoped_by_access_assignments_not_fixed_role_names(self):
		permissions = ACADEMIC_PERMISSIONS.read_text()
		self.assertNotIn("SCOPED_ROLES", permissions)
		self.assertIn("is_branch_access_enforced()", permissions)
		self.assertIn("return not bool(roles.intersection(PRIVILEGED_ROLES))", permissions)

	def test_allowed_institutions_use_the_central_hierarchical_resolver(self):
		permissions = ACADEMIC_PERMISSIONS.read_text()
		context = BRANCH_CONTEXT.read_text()
		self.assertIn("get_allowed_institutions(user=user)", permissions)
		self.assertNotIn("get_allowed_school_branches", permissions)
		self.assertIn("def get_allowed_institutions", context)
		self.assertIn("direct_branches", context)
		self.assertIn('pluck="institution"', context)
		self.assertIn("ASSIGNMENT_SCOPE_INSTITUTION", context)
		self.assertIn("ASSIGNMENT_SCOPE_COMPANY", context)

	def test_course_search_and_batch_save_remain_permission_aware(self):
		builder = QUESTION_BUILDER.read_text()
		batch = QUESTION_BATCH.read_text()
		self.assertIn('frappe.get_list(\n\t\t"Course"', builder)
		self.assertNotIn('ignore_permissions=True', builder)
		self.assertIn('doc.run_method("validate")', batch)
		self.assertIn("doc.insert()", batch)
		self.assertNotIn('ignore_permissions=True', batch)


if __name__ == "__main__":
	unittest.main()
