from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentPreparationUIContract(unittest.TestCase):
    def _component_source(self):
        return (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentPreparationDialog.vue"
        ).read_text(encoding="utf-8")

    def test_lifecycle_state_exposes_preparation_capability_without_current_only_gate(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            '"can_prepare"',
            '"preparation_source_period_end"',
            '"prepared_from_assignment"',
            '"prepared_from"',
            '"preparation_reason"',
            "_preparation_capability",
            "_period_dates",
            "active_instructors",
            "period_end or row.valid_to",
            "Unlike Transfer/Replace, an enabled historical assignment may be a valid source.",
        ):
            self.assertIn(token, lifecycle)
        self.assertIn('status == "Current"', lifecycle)
        capability = lifecycle.split("def _preparation_capability", 1)[1].split("@frappe.whitelist()", 1)[0]
        self.assertNotIn('status == "Current"', capability)
        self.assertNotIn("row.ended_on", capability)
        self.assertNotIn("row.replaced_by_assignment", capability)
        self.assertNotIn("row.transferred_to_assignment", capability)

    def test_register_surfaces_prepare_action_and_readable_preparation_origin(self):
        bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
        for token in (
            "openInstructorAssignmentPreparationDialog",
            "item.can_prepare",
            '__("Prepare Next Term / Session")',
            'label: `Prepared from ${relation.assignment_title',
            'data-eduedge-prepare-assignment',
            "preparationBusy",
            "displayContext: proxy.data || {}",
            '"Open linked assignment"',
        ):
            self.assertIn(token, bundle)

    def test_dialog_mounts_as_edgesuite_modal_and_uses_permission_scoped_page_context(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "preparation_dialog.js"
        ).read_text(encoding="utf-8")
        component = self._component_source()

        for token in (
            'InstructorAssignmentPreparationDialog from "../eduedge_ui/components/InstructorAssignmentPreparationDialog.vue"',
            "createEduEdgeApp(InstructorAssignmentPreparationDialog",
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
            'title="Prepare Next Term / Session"',
            "Source responsibility",
            "Destination Branch / Campus",
            "Destination Class / Programme Offering",
            "Destination Class Arm",
            "Destination Subject / Course",
            "Valid From",
            "Valid To",
            "Preparation Reason",
            "Only Branches available to your current permissions are shown.",
        ):
            self.assertIn(token, component)

    def test_destination_offerings_are_future_bounded_and_cascade_safely(self):
        component = self._component_source()
        for token in (
            "sourcePeriodEnd",
            'row.school_branch === branch',
            'row.name !== this.item.program_offering',
            "row.period_start_date && row.period_end_date",
            "row.period_start_date > sourceEnd",
            'fieldname === "destination_branch"',
            'next.destination_program_offering = ""',
            'next.destination_student_group = ""',
            'next.destination_course = ""',
            'next.valid_from = ""',
            'next.valid_to = ""',
            'fieldname === "destination_program_offering"',
            'next.valid_from = offering?.period_start_date || ""',
            'next.valid_to = offering?.period_end_date || ""',
        ):
            self.assertIn(token, component)

    def test_class_arm_and_subject_options_match_destination_context_and_existing_curriculum(self):
        component = self._component_source()
        for token in (
            "requiresClassArm",
            "requiresCourse",
            "row.eduedge_school_branch === offering.school_branch || row.school_branch === offering.school_branch",
            "row.program === offering.program",
            "row.academic_year === offering.academic_year",
            "row.academic_term === offering.academic_term",
            "linkedOffering === offering.name",
            'this.displayContext?.configured_course_map?.[this.selectedOffering.program]',
            "configured.has(row.name)",
            "Preparation never changes curriculum.",
        ):
            self.assertIn(token, component)
        self.assertNotIn("_apply_curriculum_additions", component)

    def test_dialog_previews_before_confirming_and_invalidates_all_stale_inputs(self):
        component = self._component_source()
        for token in (
            "Preview Preparation",
            "Confirm Preparation",
            "preview_instructor_assignment_preparation",
            "prepare_instructor_assignment_for_next_period",
            'type: "POST"',
            "setField(fieldname, value)",
            "this.invalidatePreview();",
            "this.previewPlan = null;",
            "this.previewedArgs = null;",
            "sameArgs(currentArgs, this.previewedArgs)",
            "Preparation details changed after preview",
            "Changing Branch, Class, Class Arm, Subject, dates or reason after preview requires a fresh server preview.",
            "Branch Eligibility impact",
            "The source Branch Eligibility is not shortened or deleted by preparation.",
            "previewPlan.destination?.valid_from",
            "previewPlan.destination?.valid_to",
            "previewPlan.conflicts || []",
            "if (completed) this.close();",
        ):
            self.assertIn(token, component)

    def test_dialog_makes_source_immutability_and_readable_labels_explicit(self):
        component = self._component_source()
        for token in (
            "sourceTitle",
            "sourcePeriodSummary",
            "branchLabel(name)",
            "offeringLabel(name)",
            "groupLabel(name)",
            "courseLabel(name)",
            "destinationTitle(destination)",
            "branchEligibilitySummary(branch)",
            "The source assignment and its Branch Eligibility remain unchanged.",
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
            "prepared_to_assignment",
        ):
            self.assertNotIn(forbidden, component)

    def test_dialog_does_not_bypass_backend_preparation_write_path(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "preparation_dialog.js"
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

    def test_prepare_actions_remain_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"prepare_",', request_guard)


if __name__ == "__main__":
    unittest.main()
