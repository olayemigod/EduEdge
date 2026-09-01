from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
EDUEDGE = ROOT / "eduedge"


class TestDepartmentHierarchyPermissionPatchContract(unittest.TestCase):
	def test_patch_aligns_department_with_academic_hierarchy_roles(self):
		patch = (
			EDUEDGE
			/ "patches"
			/ "v0_9"
			/ "add_department_hierarchy_permissions.py"
		).read_text(encoding="utf-8")
		patches = (EDUEDGE / "patches.txt").read_text(encoding="utf-8")

		for token in (
			"HIERARCHY_MANAGERS = PLATFORM_MANAGERS + SCHOOL_MANAGERS",
			'HIERARCHY_VIEWERS = ACADEMIC_OPERATORS + ADMISSION_OPERATORS + ("CBT Invigilator",)',
			'_ensure_permission_row("Department", role, set(MANAGE))',
			'_ensure_permission_row("Department", role, set(VIEW))',
			'frappe.clear_cache(doctype="Department")',
		):
			self.assertIn(token, patch)

		self.assertIn(
			"eduedge.patches.v0_9.add_department_hierarchy_permissions",
			patches,
		)
		self.assertNotIn("ignore_permissions", patch)
		self.assertNotIn("frappe.db.set_value", patch)


if __name__ == "__main__":
	unittest.main()
