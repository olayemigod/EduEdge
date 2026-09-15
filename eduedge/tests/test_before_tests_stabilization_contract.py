from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBeforeTestsStabilizationContract(unittest.TestCase):
	def test_test_root_stabilizer_runs_inside_frappe_test_process(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('before_tests = "eduedge.ci.ensure_erpnext_test_roots"', hooks)

	def test_stabilizer_is_ci_test_only_and_commits_missing_item_group_root(self):
		ci = (APP / "ci.py").read_text()
		self.assertIn("def ensure_erpnext_test_roots()", ci)
		self.assertIn('"Item Group", "All Item Groups"', ci)
		self.assertIn("frappe.db.commit()", ci)
		install = (APP / "install.py").read_text()
		self.assertNotIn("ensure_erpnext_test_roots", install)


if __name__ == "__main__":
	unittest.main()
