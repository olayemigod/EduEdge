from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentTransferUIContract(unittest.TestCase):
    def _component_source(self):
        return (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentTransferDialog.vue"
        ).read_text(encoding="utf-8")

    def test_lifecycle_state_exposes_transfer_status_capability_and_relationships(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            'return "Transferred"',
            '"can_transfer"',
            '"transferred_to_assignment"',
            '"transferred_to"',
            '"transferred_from_assignment"',
            '"transferred_from"',
            '"transfer_reason"',
            "has_successor_period",
            'status == "Current"',
        ):
            self.assertIn(token, lifecycle)

    def test_register_surfaces_transfer_action_status_and_readable_relationship_history(self):
        bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
        for token in (
            "openInstructorAssignmentTransferDialog",
            "item.can_transfer",
            '__("Transfer")',
            'item?.lifecycle_status === "Transferred"',
            'label: `Transferred to ${relation.assignment_title',
            'label: `Transferred from ${relation.assignment_title',
            '"Open linked assignment"',
            "syncLifecycleRegister",
            "displayContext: proxy.data || {}",
            "data-eduedge-lifecycle-relation",
            "data-eduedge-transfer-assignment",
        ):
            self.assertIn(token, bundle)

    def test_dialog_mounts_as_edgesuite_modal_and_uses_permission_scoped_page_context(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "transfer_dialog.js"
        ).read_text(encoding="utf-8")
        component = self._component_source()

        for token in (
            'InstructorAssignmentTransferDialog from "../eduedge_ui/components/InstructorAssignmentTransferDialog.vue"',
            "createEduEdgeApp(InstructorAssignmentTransferDialog",
            "document.body.appendChild(host)",
            "app.mount(host)",
            "app?.unmount?.()",
            "displayContext",
        ):
            self.assertIn(token, helper)
        self.assertNotIn("frappe.ui.Dialog", helper)

        for token in (
            "<EdgeModal",
            "<EdgeLinkField",
            'title="Transfer Instructor Assignment"',
            "Destination Branch / Campus",
            "Destination Class / Programme Offering",
            "Destination Class Arm",
            "Destination Subject / Course",
            "Transfer Date",
            "Reason",
            "Only Branches available to your current permissions are shown.",
        ):
            self.assertIn(token, component)

    def test_destination_filters_cascade_and_subjects_are_existing_curriculum_only(self):
        component = self._component_source()
        for token in (
            'row.school_branch === branch',
            "row.period_start_date",
            "row.period_end_date",
            'this.displayContext?.configured_course_map?.[this.selectedOffering.program]',
            "configured.has(row.name)",
            'fieldname === "destination_branch"',
            'next.destination_program_offering = ""',
            'next.destination_student_group = ""',
            'next.destination_course = ""',
            'fieldname === "destination_program_offering"',
            "Transfer never changes curriculum.",
        ):
            self.assertIn(token, component)
        self.assertNotIn("_apply_curriculum_additions", component)

    def test_dialog_previews_before_confirming_and_invalidates_stale_preview(self):
        component = self._component_source()
        for token in (
            "Preview Transfer",
            "Confirm Transfer",
            "preview_instructor_assignment_transfer",
            "transfer_instructor_assignment",
            'type: "POST"',
            "setField(fieldname, value)",
            "this.invalidatePreview();",
            "this.previewPlan = null;",
            "this.previewedArgs = null;",
            "sameArgs(currentArgs, this.previewedArgs)",
            "Transfer details changed after preview",
            "Changing any field after preview requires a fresh server preview.",
            "Branch Eligibility impact",
            "The source Branch Eligibility is not shortened or deleted by Transfer.",
            "previewPlan.destination?.valid_from",
            "previewPlan.destination?.valid_to",
            "previewPlan.conflicts || []",
            "if (completed) this.close();",
        ):
            self.assertIn(token, component)

    def test_popup_uses_readable_business_labels_not_internal_record_keys(self):
        component = self._component_source()
        for token in (
            "sourceTitle",
            "branchLabel(name)",
            "offeringLabel(name)",
            "groupLabel(name)",
            "courseLabel(name)",
            "destinationTitle(destination)",
            "branchEligibilitySummary(branch)",
            'row.branch_name || "Branch / Campus"',
            'row.offering_title || row.program || "Class / Programme Offering"',
            'row.course_name || "Subject / Course"',
        ):
            self.assertIn(token, component)

        for forbidden in (
            "{{ previewPlan.destination?.school_branch }}",
            "{{ previewPlan.destination?.program_offering }}",
            "{{ previewPlan.destination?.student_group }}",
            "{{ previewPlan.destination?.course }}",
            "{{ previewPlan.destination_branch_eligibility?.name }}",
        ):
            self.assertNotIn(forbidden, component)

    def test_dialog_does_not_bypass_backend_transfer_write_path(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "transfer_dialog.js"
        ).read_text(encoding="utf-8")
        component = self._component_source()
        combined = helper + component
        for forbidden in (
            "frappe.db.set_value",
            "frappe.client.set_value",
            "frappe.db.insert",
            "frappe.client.insert",
            "frappe.client.save",
        ):
            self.assertNotIn(forbidden, combined)

    def test_transfer_actions_are_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"transfer_",', request_guard)


if __name__ == "__main__":
    unittest.main()
