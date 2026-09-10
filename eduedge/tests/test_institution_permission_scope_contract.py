from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionPermissionScopeContract(unittest.TestCase):
	def test_company_wide_institution_access_requires_explicit_company_assignment(self):
		source = (APP / "education/institution_permissions.py").read_text(encoding="utf-8")
		context = (APP / "services/branch_context.py").read_text(encoding="utf-8")
		self.assertIn("get_allowed_institutions", source)
		self.assertNotIn("STRUCTURE_MANAGER_ROLES", source)
		self.assertNotIn("_has_company_structure_scope", source)
		self.assertIn("ASSIGNMENT_SCOPE_COMPANY", context)
		self.assertIn("ASSIGNMENT_SCOPE_INSTITUTION", context)
		self.assertIn('or_filters.append(["company", "in", sorted(company_scopes)])', context)
		self.assertIn('or_filters.append(["name", "in", sorted(direct_institutions)])', context)

	def test_legacy_mode_remains_backward_compatible(self):
		source = (APP / "education/institution_permissions.py").read_text(encoding="utf-8")
		self.assertIn("is_branch_access_enforced", source)
		self.assertIn("def _should_scope", source)
		self.assertIn('PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}', source)


if __name__ == "__main__":
	unittest.main()
