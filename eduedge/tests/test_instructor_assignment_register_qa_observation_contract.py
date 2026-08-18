from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = (
    ROOT
    / "eduedge"
    / "public"
    / "js"
    / "eduedge_instructor_assignment_register_filters.bundle.js"
)
FILTERS = (
    ROOT
    / "eduedge"
    / "public"
    / "js"
    / "eduedge_ui"
    / "components"
    / "InstructorAssignmentRegisterFilters.vue"
)


class TestInstructorAssignmentRegisterQAObservationContract(unittest.TestCase):
    def test_filter_runtime_keeps_existing_filter_app_mounted_during_refresh(self):
        source = RUNTIME.read_text(encoding="utf-8")
        for token in (
            "existing?.host?.isConnected && existing.instructor === proxy.instructor",
            "if (proxy.registerFilterLoading) return existing || null;",
            "this.registerFilterLoading = false;",
            "await this.$nextTick?.();",
            "mountRegisterFilters(this);",
        ):
            self.assertIn(token, source)
        self.assertIn("Never replace the child filter app while its request is still settling", source)

    def test_assignment_register_and_branch_eligibility_are_tabbed_register_first(self):
        source = RUNTIME.read_text(encoding="utf-8")
        for token in (
            'const DEFAULT_REGISTER_TAB = "register"',
            'data-register-tab="register"',
            'data-register-tab="eligibility"',
            "Instructor Assignment Register",
            "Branch Eligibility Periods",
            'proxy.assignmentRegisterTab = active',
            'registerPanel.hidden = active !== DEFAULT_REGISTER_TAB',
            'eligibilityPanel.hidden = active !== "eligibility"',
            "eduedge-instructor-assignment-tabs-layout",
        ):
            self.assertIn(token, source)

    def test_page_is_view_first_and_planner_opens_only_from_add_action(self):
        source = RUNTIME.read_text(encoding="utf-8")
        for token in (
            "assignmentPlannerOpen: false",
            'panelByHeading("Who is being assigned?")',
            "Instructor records",
            "Add Assignment",
            "Close Assignment Planner",
            "data-eduedge-toggle-assignment-planner",
            "element.hidden = !open",
            "proxy.assignmentPlannerOpen = !proxy.assignmentPlannerOpen",
        ):
            self.assertIn(token, source)

    def test_filters_are_grouped_into_quick_views_and_explicit_more_filters(self):
        source = FILTERS.read_text(encoding="utf-8")
        for token in (
            "Quick views",
            "Lifecycle",
            "Academic context",
            "Responsibility & history",
            "More Filters",
            "Show ▼",
            "Hide ▲",
            "advancedOpen",
            'aria-controls="eduedge-assignment-more-filters"',
            "eduedge-register-more-toggle",
            "Search assignments",
            "eduedge-register-primary-grid",
            "eduedge-register-advanced-grid",
        ):
            self.assertIn(token, source)
        self.assertLess(source.index('v-if="advancedOpen"'), source.index("<span>Academic context</span>"))

    def test_tabs_and_view_first_ui_do_not_change_business_data(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('panelByHeading("Instructor Assignment Register")', source)
        self.assertIn('panelByHeading("Branch Eligibility Periods")', source)
        self.assertNotIn("frappe.db.set_value", source)
        self.assertNotIn("frappe.client.set_value", source)
        self.assertNotIn("delete_doc", source)


if __name__ == "__main__":
    unittest.main()
