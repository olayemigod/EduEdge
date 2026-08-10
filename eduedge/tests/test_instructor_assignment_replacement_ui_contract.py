from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentReplacementUIContract(unittest.TestCase):
    def test_lifecycle_state_exposes_server_authoritative_replace_capability_and_links(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            'return "Replaced"',
            '"can_replace"',
            "has_successor_period",
            'status == "Current"',
            '"replaced_by_assignment"',
            '"replaced_by"',
            '"replaces_assignment"',
            '"replaces"',
            '"replacement_reason"',
            "def _relation_summaries",
            'frappe.get_list(\n        "EduEdge Instructor Assignment"',
        ):
            self.assertIn(token, lifecycle)

    def test_register_surfaces_replace_action_relationship_history_and_scoped_instructors(self):
        bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
        for token in (
            'openInstructorAssignmentReplacementDialog',
            'item.can_replace',
            '"Replace / Handover"',
            'item?.lifecycle_status === "Replaced"',
            'label: `Replaced by ${person}`',
            'label: `Replaces ${person}`',
            '"Open linked assignment"',
            "syncReplacementRegister",
            "installReplacementRegisterEnhancer",
            "const originalLoad = methods.load",
            "await originalLoad.apply(this, args)",
            "await this.$nextTick?.()",
            "syncReplacementRegister(this)",
            "instructors: proxy.data?.instructors || []",
        ):
            self.assertIn(token, bundle)

    def test_dialog_mounts_as_edgesuite_modal_in_product_vue_runtime(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "replacement_dialog.js"
        ).read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "InstructorAssignmentReplacementDialog.vue"
        ).read_text(encoding="utf-8")

        for token in (
            'InstructorAssignmentReplacementDialog from "./InstructorAssignmentReplacementDialog.vue"',
            'createEduEdgeApp(InstructorAssignmentReplacementDialog',
            'document.body.appendChild(host)',
            'app.mount(host)',
            'app?.unmount?.()',
        ):
            self.assertIn(token, helper)

        self.assertNotIn("frappe.ui.Dialog", helper)
        self.assertNotIn("new frappe.ui.Dialog", helper)

        for token in (
            "<EdgeModal",
            "<EdgeLinkField",
            'title="Replace / Handover Instructor Assignment"',
            "Replacement Instructor *",
            "Handover Date *",
            "Reason *",
            "Only active Instructors already available to your permissions are shown.",
            'row.name !== this.item.instructor',
            'String(row.status || "Active") === "Active"',
        ):
            self.assertIn(token, component)

    def test_dialog_previews_before_confirming_and_immediately_invalidates_stale_preview(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "InstructorAssignmentReplacementDialog.vue"
        ).read_text(encoding="utf-8")

        for token in (
            "Preview Replacement",
            "Confirm Replacement",
            "preview_instructor_assignment_replacement",
            "replace_instructor_assignment",
            'type: "POST"',
            "setField(fieldname, value)",
            "this.invalidatePreview();",
            "this.previewPlan = null;",
            "this.previewedArgs = null;",
            "sameArgs(currentArgs, this.previewedArgs)",
            "Replacement details changed after preview",
            "Changing any field after preview requires a fresh preview.",
            "Branch Eligibility impact",
            "The outgoing Instructor's Branch Eligibility is not changed",
            "previewPlan.successor?.valid_from",
            "previewPlan.successor?.valid_to",
            "previewPlan.conflicts || []",
            "if (completed) this.close();",
        ):
            self.assertIn(token, component)

    def test_dialog_does_not_bypass_backend_lifecycle_write_path(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "replacement_dialog.js"
        ).read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "InstructorAssignmentReplacementDialog.vue"
        ).read_text(encoding="utf-8")
        combined = helper + component
        for forbidden in (
            "frappe.db.set_value",
            "frappe.client.set_value",
            "frappe.db.insert",
            "frappe.client.insert",
            "frappe.client.save",
        ):
            self.assertNotIn(forbidden, combined)

    def test_replace_actions_are_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"replace_",', request_guard)


if __name__ == "__main__":
    unittest.main()
