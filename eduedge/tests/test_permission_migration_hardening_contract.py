from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestPermissionMigrationHardeningContract(unittest.TestCase):
	def test_after_migrate_does_not_regrant_role_permissions(self):
		install = (APP / "install.py").read_text()
		after_migrate = install.split("def after_migrate", 1)[1].split("def ensure_roles", 1)[0]
		for forbidden in (
			"ensure_admission_manager_permissions",
			"ensure_training_progress_permissions",
			"ensure_training_page_roles",
			"add_permission",
			"update_permission_property",
		):
			self.assertNotIn(forbidden, after_migrate)
		self.assertNotIn("TRAINING_PROGRESS_ROLES", install)
		self.assertNotIn("ADMISSION_PERMISSION_TYPES", install)

	def test_training_cleanup_patch_removes_delete_for_every_role(self):
		patches = (APP / "patches.txt").read_text()
		patch = (APP / "patches/v0_9/harden_training_progress_permissions.py").read_text()
		self.assertIn("harden_training_progress_permissions", patches)
		self.assertIn("get_default_permission_matrix", patch)
		self.assertIn("PORTAL_ONLY_ROLES", patch)
		self.assertIn("NO_EDUEDGE_DEFAULT_GRANTS", patch)
		self.assertIn('frappe.db.set_value("Custom DocPerm", row.name, "delete", 0', patch)
		self.assertIn("Other custom rights remain available", patch)


if __name__ == "__main__":
	unittest.main()
