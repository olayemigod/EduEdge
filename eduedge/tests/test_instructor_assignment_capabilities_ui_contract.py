from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentCapabilitiesUIContract(unittest.TestCase):
    def _runtime(self):
        return (APP / "public" / "js" / "eduedge_instructor_assignment_capabilities.bundle.js").read_text(encoding="utf-8")

    def _component(self):
        return (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentCapabilityDialog.vue"
        ).read_text(encoding="utf-8")

    def test_runtime_loads_manager_scoped_server_capability_state_fail_closed(self):
        runtime = self._runtime()
        api = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        for token in (
            "get_instructor_assignment_capability_admin_states",
            "loadCapabilityStates",
            "JSON.stringify(assignments.map((item) => item.name))",
            "can_manage_capabilities: false",
            "capabilities: {}",
            'capability_version: ""',
            "capability_state_unavailable: true",
        ):
            self.assertIn(token, runtime)
        for token in (
            "def get_instructor_assignment_capability_admin_states",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="view_instructor_assignment_capability_admin_states")',
        ):
            self.assertIn(token, api)

    def test_register_shows_capabilities_only_when_server_allows_management(self):
        source = self._runtime()
        for token in (
            "item.can_manage_capabilities",
            "item.capability_version",
            "data-eduedge-assignment-capabilities",
            '__("Capabilities")',
            "Capabilities (${count})",
            "syncCapabilityActions",
        ):
            self.assertIn(token, source)

    def test_dialog_uses_edgesuite_modal_and_keeps_question_governance_separate(self):
        source = self._component()
        for token in (
            "<EdgeModal",
            'title="Manage Assignment Capabilities"',
            "Exact Subject responsibility",
            "Assignment capabilities are not Question Governance.",
            "Subject review and final approval remain controlled separately through Question Responsibility governance.",
            "View Subject Content",
            "Manage Subject Topics",
            "Author CBT Questions",
            "Create Assessment Plans",
            "Enter Marks",
        ):
            self.assertIn(token, source)
        self.assertNotIn("frappe.ui.Dialog", source)

    def test_ui_guides_capability_dependency_and_requires_reason(self):
        source = self._component()
        for token in (
            'fieldname === "can_view_subject_content" && !checked',
            'fieldname !== "can_view_subject_content" && checked',
            "next.can_view_subject_content = 1",
            "Give a reason for changing these capabilities.",
            "at least 3 characters",
            "hasChanges",
            "Save Capabilities",
        ):
            self.assertIn(token, source)

    def test_save_is_post_only_and_uses_optimistic_concurrency_version(self):
        source = self._component()
        api = (APP / "api" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")
        for token in (
            "update_instructor_assignment_capabilities",
            'type: "POST"',
            "capabilities: JSON.stringify(this.form)",
            "expected_modified: this.item.capability_version",
        ):
            self.assertIn(token, source)
        for token in (
            "expected_modified: str | None = None",
            "expected_version",
            "str(doc.modified or \"\") != expected_version",
            "changed after its capabilities were loaded",
            '"capability_version": str(doc.modified or "")',
        ):
            self.assertIn(token, api)

    def test_capability_ui_does_not_bypass_backend_or_mutate_question_governance(self):
        combined = self._runtime() + self._component()
        for forbidden in (
            "frappe.db.set_value",
            "frappe.client.set_value",
            "frappe.db.insert",
            "frappe.client.insert",
            "can_subject_review",
            "can_final_approve",
            "save_assignment(",
        ):
            self.assertNotIn(forbidden, combined)

    def test_loader_keeps_edgesuite_first_and_installs_capability_runtime_before_mount(self):
        loader = (
            APP
            / "eduedge"
            / "page"
            / "eduedge_instructor_assignments"
            / "eduedge_instructor_assignments.js"
        ).read_text(encoding="utf-8")
        for token in (
            'frappe.require("edgesuite_ui.bundle.js"',
            '"eduedge_instructor_assignment_capabilities.bundle.js"',
            "frappe.require(capabilityBundle",
            "window.installInstructorAssignmentCapabilities",
            "mount_instructor_assignments_with_register_runtime",
        ):
            self.assertIn(token, loader)
        self.assertLess(
            loader.index('frappe.require("edgesuite_ui.bundle.js"'),
            loader.index('"eduedge_instructor_assignment_capabilities.bundle.js"'),
        )


if __name__ == "__main__":
    unittest.main()
