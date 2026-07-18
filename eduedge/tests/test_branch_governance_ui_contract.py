from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestBranchGovernanceUIContract(unittest.TestCase):
	def test_edgesuite_page_and_bundle_exist(self):
		page_root = APP / "eduedge" / "page" / "eduedge_branch_governance"
		for filename in (
			"__init__.py",
			"eduedge_branch_governance.json",
			"eduedge_branch_governance.js",
		):
			self.assertTrue((page_root / filename).exists(), filename)
		payload = json.loads((page_root / "eduedge_branch_governance.json").read_text())
		self.assertEqual(payload["name"], "eduedge-branch-governance")
		self.assertIn("EduEdge Administrator", {row["role"] for row in payload["roles"]})

	def test_page_uses_edgesuite_runtime_and_controlled_failure_state(self):
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_branch_governance"
			/ "eduedge_branch_governance.js"
		).read_text()
		self.assertLess(loader.index("edgeui.bundle.js"), loader.index("eduedge_branch_governance.bundle.js"))
		self.assertIn("window.EdgeSuiteUI", loader)
		self.assertIn("EdgeAppShell", loader)
		self.assertIn("failed to load", loader)

	def test_governance_ui_is_guided_and_branch_safe(self):
		vue = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_branch_governance"
			/ "EduEdgeBranchGovernance.vue"
		).read_text()
		for token in (
			"<EdgeAppShell",
			"<EdgeDashboardLayout",
			"<EdgeStatusBadge",
			"openAssignmentDialog",
			"set_branch_enforcement",
			"missing_accounting_labels",
			"company: dialog.get_value(\"company\")",
		):
			self.assertIn(token, vue)

	def test_backend_enforces_coverage_before_activation(self):
		service = (APP / "services" / "branch_governance.py").read_text()
		api = (APP / "api" / "branch_governance.py").read_text()
		self.assertIn("Every enabled campus is covered", service)
		self.assertIn("blocking_failures", service)
		self.assertIn("enable_user_branch_access_enforcement", service)
		self.assertIn("MANAGE_ROLES", api)
		self.assertIn("_require_roles(MANAGE_ROLES)", api)
		for forbidden in (
			"ignore_permissions=True",
			'frappe.new_doc("Sales Invoice")',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
			".submit()",
			".cancel()",
		):
			self.assertNotIn(forbidden, service)

	def test_navigation_exposes_governance_center(self):
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn('/app/eduedge-branch-governance', navigation)


if __name__ == "__main__":
	unittest.main()
