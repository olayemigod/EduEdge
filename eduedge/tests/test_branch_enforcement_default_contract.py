from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBranchEnforcementDefaultContract(unittest.TestCase):
	def test_new_sites_default_to_isolated_branch_access(self):
		settings = (
			APP
			/ "eduedge/doctype/eduedge_settings/eduedge_settings.json"
		).read_text()
		self.assertIn('"default":"1","fieldname":"enable_user_branch_access_enforcement"', settings)
		self.assertIn('"default":"0","fieldname":"allow_hq_all_branch_view"', settings)
		self.assertIn('"role":"EduEdge Super Administrator"', settings)

	def test_existing_multi_branch_sites_receive_readiness_blocker_not_silent_migration(self):
		readiness = (APP / "services/setup_readiness.py").read_text()
		install = (APP / "install.py").read_text()
		self.assertIn("not enforcement_enabled and branch_count > 1", readiness)
		self.assertIn("Branch Access enforcement is disabled on a multi-branch school", readiness)
		self.assertIn("not enforcement_enabled and branch_count == 1", readiness)
		self.assertNotIn('set_single_value("EduEdge Settings", "enable_user_branch_access_enforcement"', install)
		self.assertNotIn('frappe.db.set_value("EduEdge Settings",', install)


if __name__ == "__main__":
	unittest.main()
