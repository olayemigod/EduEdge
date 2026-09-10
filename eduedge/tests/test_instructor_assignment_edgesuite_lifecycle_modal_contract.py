from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
END_COMPONENT = APP / "public" / "js" / "eduedge_ui" / "components" / "InstructorAssignmentEndDialog.vue"
END_RUNTIME = APP / "public" / "js" / "eduedge_instructor_assignment_end.bundle.js"
REPLACEMENT_RUNTIME = APP / "public" / "js" / "eduedge_instructor_assignments" / "replacement_dialog.js"


class TestInstructorAssignmentEdgeSuiteLifecycleModalContract(unittest.TestCase):
    def test_end_assignment_uses_edgesuite_modal_and_governed_post_api(self):
        source = END_COMPONENT.read_text(encoding="utf-8")
        for token in (
            "<EdgeModal",
            'title="End Instructor Assignment"',
            "End Date",
            "Why is this responsibility ending?",
            "eduedge.api.instructor_assignment_lifecycle.end_instructor_assignment",
            'type: "POST"',
            "Branch Eligibility is governed independently",
        ):
            self.assertIn(token, source)
        self.assertNotIn("frappe.ui.Dialog", source)

    def test_runtime_replaces_legacy_end_method_after_component_registration(self):
        source = END_RUNTIME.read_text(encoding="utf-8")
        for token in (
            "methods.endAssignment = function",
            "showDialog(this, item)",
            "installWhenReady",
            "window.EduEdgeInstructorAssignments",
            "__eduedgeAssignmentEndDialogInstalled",
        ):
            self.assertIn(token, source)

    def test_existing_assignment_bundle_loads_lifecycle_modal_bridge(self):
        source = REPLACEMENT_RUNTIME.read_text(encoding="utf-8")
        self.assertIn('import "../eduedge_instructor_assignment_end.bundle.js";', source)

    def test_governance_modal_dark_surfaces_use_edgesuite_semantic_tokens(self):
        source = END_RUNTIME.read_text(encoding="utf-8")
        for token in (
            "eduedge-assignment-governance-theme-bridge",
            "--edge-color-surface-muted",
            "--edge-color-control-surface",
            "--edge-color-control-border",
            "--edge-color-control-text",
            "--edge-color-ink-400",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
