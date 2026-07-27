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
		self.assertEqual(payload["roles"], [])
		access = (APP / "access_control.py").read_text()
		self.assertIn('"/app/eduedge-branch-governance"', access)
		self.assertIn('("user_branch_access", "read")', access)
		self.assertIn('("school_branch", "write")', access)

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

	def test_governance_ui_is_guided_branch_safe_and_uses_edgesuite_dialogs(self):
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
			"<EdgeFormDialog",
			"<EdgeModal",
			"openAssignmentDialog",
			"openQuickEditor",
			"saveRecordModal",
			"set_branch_enforcement",
			"missing_accounting_labels",
			"Assignment details restricted",
		):
			self.assertIn(token, vue)
		self.assertNotIn("new frappe.ui.Dialog", vue)
		self.assertNotIn("frappe.confirm(", vue)

	def test_branch_role_select_is_renderable_and_persistent_in_quick_editor(self):
		backend = (APP / "api" / "modal_records.py").read_text()
		adapter = (APP / "public" / "js" / "eduedge_ui" / "modal_records.js").read_text()
		self.assertIn('"fieldname": "branch_role", "type": "Select"', backend)
		self.assertIn('"options": BRANCH_ROLES', backend)
		self.assertIn('const value = String(option);', adapter)
		self.assertIn('return { value, label: translateModalText(value) };', adapter)
		self.assertIn('field.options.map(translateModalOption).filter(Boolean)', adapter)
		self.assertIn('modal.values = { ...(schema.values || {}) };', adapter)
		self.assertIn('values: JSON.stringify(modal.values || {})', adapter)

	def test_backend_enforces_coverage_and_configured_permissions(self):
		service = (APP / "services" / "branch_governance.py").read_text()
		api = (APP / "api" / "branch_governance.py").read_text()
		self.assertIn("Every enabled campus is covered", service)
		self.assertIn("blocking_failures", service)
		self.assertIn("enable_user_branch_access_enforcement", service)
		self.assertIn("get_allowed_school_branches", service)
		self.assertIn("include_assignment_details", service)
		self.assertIn("include_all_branches", service)
		self.assertIn("user_has_role_permission", api)
		self.assertIn('"write", "EduEdge User Branch Access"', api)
		self.assertIn('_has("write", "EduEdge School Branch")', api)
		self.assertIn('_has("write", "EduEdge Settings")', api)
		self.assertNotIn("MANAGE_ROLES", api)
		self.assertNotIn("VIEW_ROLES", api)
		self.assertNotIn("frappe.get_roles", service)
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
