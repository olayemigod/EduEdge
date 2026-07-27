from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionPermissionScopeContract(unittest.TestCase):
	def test_structure_roles_need_hq_scope_for_company_wide_institution_access(self):
		source = (APP / "education/institution_permissions.py").read_text(encoding="utf-8")
		for expected in (
			"get_branch_access_profile",
			"_has_company_structure_scope",
			"can_view_all_branches",
			"roles.intersection(STRUCTURE_MANAGER_ROLES) and _has_company_structure_scope",
			'filters={"name": ["in", branch_names]}',
			'{"name": ["in", branch_names], "institution": doc.name}',
		):
			self.assertIn(expected, source)

	def test_legacy_mode_remains_backward_compatible(self):
		source = (APP / "education/institution_permissions.py").read_text(encoding="utf-8")
		self.assertIn("if not is_branch_access_enforced():\n\t\treturn True", source)
		self.assertIn('PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}', source)


if __name__ == "__main__":
	unittest.main()
