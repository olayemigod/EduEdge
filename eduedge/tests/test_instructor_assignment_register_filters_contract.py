from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentRegisterFiltersContract(unittest.TestCase):
    def _backend(self):
        return (APP / "api" / "instructor_assignment_register.py").read_text(encoding="utf-8")

    def _runtime(self):
        return (APP / "public" / "js" / "eduedge_instructor_assignment_register_filters.bundle.js").read_text(encoding="utf-8")

    def _component(self):
        return (
            APP
            / "public"
            / "js"
            / "eduedge_ui"
            / "components"
            / "InstructorAssignmentRegisterFilters.vue"
        ).read_text(encoding="utf-8")

    def test_backend_is_permission_aware_paged_and_bounded(self):
        source = self._backend()
        for token in (
            "def get_instructor_assignment_register_page",
            "core._require_read()",
            "core._allowed_branches()",
            "frappe.get_list(",
            '"EduEdge Instructor Assignment"',
            "DEFAULT_PAGE_SIZE = 50",
            "MAX_PAGE_SIZE = 100",
            "MAX_FILTER_SCAN = 5000",
            "limit_page_length=MAX_FILTER_SCAN + 1",
            '"scan_truncated": scan_truncated',
            '"has_previous": page > 1',
            '"has_next": page < page_count',
        ):
            self.assertIn(token, source)

    def test_backend_supports_business_filters_lifecycle_origin_and_history_dates(self):
        source = self._backend()
        for token in (
            '"branch"',
            '"academic_year"',
            '"academic_term"',
            '"program_offering"',
            '"student_group"',
            '"course"',
            '"assignment_type"',
            '"assignment_scope"',
            '"lifecycle_status"',
            '"origin"',
            '"date_from"',
            '"date_to"',
            '"search_text"',
            "_lifecycle_status(row, today)",
            'return "Prepared"',
            'return "Replacement"',
            'return "Transfer"',
            'return "Normal"',
        ):
            self.assertIn(token, source)

    def test_smart_presets_default_to_current_and_upcoming_without_deleting_history(self):
        source = self._backend()
        for token in (
            '"current_upcoming"',
            'status in {"Current", "Scheduled"}',
            'preset == "prepared"',
            'preset == "all"',
            '"Current"',
            '"Scheduled"',
            '"Ended"',
            '"Replaced"',
            '"Transferred"',
            '"Disabled"',
        ):
            self.assertIn(token, source)
        self.assertNotIn("frappe.delete_doc", source)
        self.assertNotIn("frappe.db.set_value", source)

    def test_filter_context_fails_closed_on_invalid_branch_and_cascading_context(self):
        source = self._backend()
        for token in (
            "The selected register Branch / Campus is not available to your user.",
            "The selected register Class / Programme Offering is not available to your user.",
            "The selected register Class does not belong to the selected Branch.",
            "The selected register Class does not belong to the selected Academic Session.",
            "The selected register Class does not belong to the selected Term / Semester.",
            "The selected register Class Arm is not available to your user.",
            "The selected register Subject / Course is not available to your user.",
        ):
            self.assertIn(token, source)

    def test_search_uses_readable_business_labels(self):
        source = self._backend()
        for token in (
            'branch.get("branch_name")',
            'branch.get("institution_name")',
            'offering.get("offering_title")',
            'group.get("eduedge_display_name")',
            'group.get("student_group_name")',
            'course.get("course_name")',
            "row.assignment_title",
            "row.assignment_type",
        ):
            self.assertIn(token, source)

    def test_filter_ui_cascades_branch_session_term_class_arm_and_subject(self):
        component = self._component()
        for token in (
            "Smart register filters",
            "Branch / Campus",
            "Academic Session",
            "Term / Semester",
            "Class / Programme Offering",
            "Class Arm",
            "Subject / Course",
            "Lifecycle Status",
            "History From",
            "History To",
            "Search",
            "branchChanged()",
            "academicYearChanged()",
            "academicTermChanged()",
            "offeringChanged()",
            'this.draft.program_offering = ""',
            'this.draft.student_group = ""',
            'this.draft.course = ""',
            "configured_course_map",
        ):
            self.assertIn(token, component)

    def test_filter_ui_exposes_presets_counts_chips_and_pagination(self):
        component = self._component()
        for token in (
            "Current + Upcoming",
            "Current",
            "Scheduled",
            "Ended",
            "Replaced / Handed Over",
            "Transferred",
            "Prepared for Next Period",
            "All History",
            "activeChips",
            "Clear Filters",
            "Showing {{ register.from_row }}–{{ register.to_row }} of {{ register.total }}",
            "Previous",
            "Next",
            "Apply Filters",
            "register.scan_truncated",
        ):
            self.assertIn(token, component)

    def test_runtime_redirects_only_the_page_read_and_preserves_lifecycle_calls(self):
        runtime = self._runtime()
        for token in (
            "BASE_PAGE_METHOD",
            "FILTERED_PAGE_METHOD",
            "register_filters: JSON.stringify(proxy.registerFilters || {})",
            "register_page: proxy.registerPage || 1",
            "register_page_size: proxy.registerPageSize || 50",
            "const originalCall = frappe.call",
            "frappe.call = redirectPageCall(this, originalCall)",
            "frappe.call = originalCall",
            "existingLoad.apply(this, args)",
            "mountRegisterFilters(this)",
        ):
            self.assertIn(token, runtime)
        self.assertNotIn("frappe.db.set_value", runtime)
        self.assertNotIn("frappe.client.set_value", runtime)

    def test_filters_persist_in_url_without_overwriting_planner_route_context(self):
        runtime = self._runtime()
        for token in (
            'const FILTER_PREFIX = "assignment_"',
            'params.get("instructor")',
            "window.history.replaceState",
            'params.set("instructor", proxy.instructor)',
            "assignment_",
        ):
            self.assertIn(token, runtime)
        self.assertNotIn('params.set("branch",', runtime)
        self.assertNotIn('params.set("offering",', runtime)

    def test_page_loader_installs_filter_runtime_after_edgesuite_and_before_mounting(self):
        loader = (
            APP
            / "eduedge"
            / "page"
            / "eduedge_instructor_assignments"
            / "eduedge_instructor_assignments.js"
        ).read_text(encoding="utf-8")
        for token in (
            'frappe.require("edgesuite_ui.bundle.js"',
            '"eduedge_instructor_assignment_register_filters.bundle.js"',
            "frappe.require(filterBundle",
            "mount_instructor_assignments_with_register_filters",
            "window.installInstructorAssignmentRegisterFilters",
            "mount_instructor_assignments(wrapper, visitId, page, $loading, fail)",
        ):
            self.assertIn(token, loader)
        self.assertLess(
            loader.index('frappe.require("edgesuite_ui.bundle.js"'),
            loader.index('"eduedge_instructor_assignment_register_filters.bundle.js"'),
        )


if __name__ == "__main__":
    unittest.main()
