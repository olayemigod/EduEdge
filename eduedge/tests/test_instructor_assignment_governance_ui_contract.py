from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentGovernanceUIContract(unittest.TestCase):
    def _runtime(self):
        return (APP / "public" / "js" / "eduedge_instructor_assignment_governance.bundle.js").read_text(encoding="utf-8")

    def _component(self):
        return (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentGovernanceDialog.vue"
        ).read_text(encoding="utf-8")

    def test_runtime_loads_server_governance_capabilities_fail_closed(self):
        source = self._runtime()
        for token in (
            "get_instructor_assignment_governance_states",
            "loadGovernanceStates",
            "JSON.stringify(assignments.map((item) => item.name))",
            "can_disable: false",
            "can_reenable: false",
            "can_delete_unused: false",
            "governance_unavailable: true",
        ):
            self.assertIn(token, source)

    def test_register_actions_follow_server_capability_only(self):
        source = self._runtime()
        for token in (
            "item.can_disable",
            "item.can_reenable",
            "item.can_delete_unused",
            'data-eduedge-disable-assignment',
            'data-eduedge-reenable-assignment',
            'data-eduedge-delete-unused-assignment',
            '__("Disable")',
            '__("Re-enable")',
            '__("Delete Unused")',
            "syncGovernanceActions",
        ):
            self.assertIn(token, source)

    def test_governance_dialog_is_edgesuite_modal_and_reason_required(self):
        component = self._component()
        for token in (
            "<EdgeModal",
            "Disable Future Assignment",
            "Re-enable Future Assignment",
            "Delete Unused Future Assignment",
            "Reason",
            "reasonError",
            "at least 3 characters",
            "Branch Eligibility is independent",
        ):
            self.assertIn(token, component)
        self.assertNotIn("frappe.ui.Dialog", component)

    def test_delete_requires_explicit_delete_confirmation(self):
        component = self._component()
        for token in (
            "Type DELETE to confirm",
            'deleteConfirmation !== "DELETE"',
            "Delete Unused Assignment",
            "deletion removes the unused future assignment record itself",
        ):
            self.assertIn(token, component)

    def test_dialog_uses_post_only_backend_actions_and_no_direct_client_db_writes(self):
        component = self._component()
        for token in (
            "disable_instructor_assignment",
            "reenable_instructor_assignment",
            "delete_unused_instructor_assignment",
            'type: "POST"',
        ):
            self.assertIn(token, component)
        for forbidden in (
            "frappe.db.set_value",
            "frappe.client.set_value",
            "frappe.db.insert",
            "frappe.client.insert",
            "frappe.client.save",
        ):
            self.assertNotIn(forbidden, component + self._runtime())

    def test_runtime_exposes_product_vue_factory_and_refreshes_after_action(self):
        source = self._runtime()
        for token in (
            "createEduEdgeInstructorAssignmentGovernanceApp",
            "createEduEdgeApp(InstructorAssignmentGovernanceDialog",
            "await proxy.load?.()",
            "window.installInstructorAssignmentGovernance",
        ):
            self.assertIn(token, source)

    def test_page_loader_keeps_edgesuite_first_and_installs_governance_before_mount(self):
        loader = (
            APP
            / "eduedge"
            / "page"
            / "eduedge_instructor_assignments"
            / "eduedge_instructor_assignments.js"
        ).read_text(encoding="utf-8")
        for token in (
            'frappe.require("edgesuite_ui.bundle.js"',
            '"eduedge_instructor_assignment_governance.bundle.js"',
            "frappe.require(governanceBundle",
            "window.installInstructorAssignmentGovernance",
            "mount_instructor_assignments_with_register_runtime",
        ):
            self.assertIn(token, loader)
        self.assertLess(
            loader.index('frappe.require("edgesuite_ui.bundle.js"'),
            loader.index('"eduedge_instructor_assignment_governance.bundle.js"'),
        )


if __name__ == "__main__":
    unittest.main()
