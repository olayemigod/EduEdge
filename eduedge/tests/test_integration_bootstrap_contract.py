from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestIntegrationBootstrapContract(unittest.TestCase):
	def test_ci_bootstrap_is_explicit_and_not_a_product_hook(self):
		helper = (APP / "ci.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("def ensure_erpnext_test_roots", helper)
		self.assertIn('"All Item Groups"', helper)
		self.assertIn("frappe.db.commit()", helper)
		self.assertNotIn("ensure_erpnext_test_roots", hooks)

	def test_database_workflows_prepare_upstream_erpnext_test_root(self):
		for filename in ("integration.yml", "edgesuite-ui-candidate-compat.yml"):
			workflow = (ROOT / ".github" / "workflows" / filename).read_text()
			self.assertIn("eduedge.ci.ensure_erpnext_test_roots", workflow)
			self.assertLess(
				workflow.index("eduedge.ci.ensure_erpnext_test_roots"),
				workflow.index("run-tests"),
			)


if __name__ == "__main__":
	unittest.main()
