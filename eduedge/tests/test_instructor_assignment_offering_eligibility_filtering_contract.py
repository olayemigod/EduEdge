from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
LINK_SEARCH = APP / "api" / "instructor_assignment_link_search.py"
PLANNER_API = APP / "api" / "instructor_assignments.py"
REGISTER_API = APP / "api" / "instructor_assignment_register.py"
BRANCH_GOVERNANCE = APP / "services" / "instructor_branch_governance.py"
ASSIGNMENT_CONTROLLER = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_assignment"
    / "eduedge_instructor_assignment.py"
)
NATIVE_FORM = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_assignment"
    / "eduedge_instructor_assignment.js"
)
SEARCH_FIELDS = (
    APP
    / "public"
    / "js"
    / "eduedge_instructor_assignments"
    / "InstructorAssignmentSearchFields.vue"
)
PLANNER_UI = (
    APP
    / "public"
    / "js"
    / "eduedge_instructor_assignments"
    / "EduEdgeInstructorAssignments.vue"
)


class TestInstructorAssignmentOfferingEligibilityFilteringContract(unittest.TestCase):
    def test_offering_search_requires_branch_governance_period_overlap(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        for token in (
            "assignment_eligibility_overlaps_period",
            "assignment_eligibility_covers_period",
            "def _offering_available_for_instructor",
            "assignments._period_dates(",
            "if instructor and not _offering_available_for_instructor",
            "continue",
        ):
            self.assertIn(token, source)

    def test_dependent_searches_reject_offering_without_governed_period_overlap(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        for token in (
            "def _assert_offering_period_governance",
            "does not overlap this Instructor's Branch Governance eligibility period",
            "def search_assignment_class_arms",
            "def search_assignment_courses",
        ):
            self.assertIn(token, source)

        class_arm = source.split("def search_assignment_class_arms", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]
        course = source.split("def search_assignment_courses", 1)[1].split(
            "def _standard_filters", 1
        )[0]
        self.assertIn("_assert_offering_period_governance", class_arm)
        self.assertIn("_assert_offering_period_governance", course)

    def test_search_instructor_context_is_permission_scoped(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        for token in (
            "def _assert_search_instructor_available",
            "current_user_instructors()",
            'doc.check_permission("read")',
            'str(doc.status or "") != "Active"',
            "The selected Instructor is not available to your user.",
        ):
            self.assertIn(token, source)

    def test_optional_instructor_parameter_preserves_existing_positional_api_order(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        self.assertIn(
            "def search_assignment_offerings(\n\tbranch: str,\n\tquery: str = \"\",\n\tpage_length: int | str = 20,\n\tinstructor: str | None = None,",
            source,
        )
        self.assertIn(
            "def search_assignment_class_arms(\n\tbranch: str,\n\tprogram_offering: str,\n\tquery: str = \"\",\n\tpage_length: int | str = 20,\n\tinstructor: str | None = None,",
            source,
        )
        self.assertIn(
            "def search_assignment_courses(\n\tbranch: str,\n\tprogram_offering: str,\n\tquery: str = \"\",\n\tpage_length: int | str = 20,\n\tinstructor: str | None = None,",
            source,
        )

    def test_edgesuite_searches_pass_selected_instructor_context(self):
        source = SEARCH_FIELDS.read_text(encoding="utf-8")

        self.assertGreaterEqual(source.count('instructor: this.instructor || ""'), 3)
        for token in (
            "search_assignment_offerings",
            "search_assignment_class_arms",
            "search_assignment_courses",
        ):
            self.assertIn(token, source)

    def test_planner_preload_and_register_use_same_date_bounded_filter(self):
        planner = PLANNER_API.read_text(encoding="utf-8")
        register = REGISTER_API.read_text(encoding="utf-8")

        for token in (
            "def _filter_planner_options_by_instructor",
            "assignment_eligibility_overlaps_period(",
            "assignment_eligibility_covers_period(",
            "governed_offerings",
            "governed_groups",
            "governed_institutions",
            "governed_courses",
        ):
            self.assertIn(token, planner)

        self.assertGreaterEqual(
            planner.count("_filter_planner_options_by_instructor("),
            2,
        )
        self.assertIn("_filter_planner_options_by_instructor", register)

    def test_route_preset_rejects_class_outside_governed_offering_payload(self):
        source = PLANNER_UI.read_text(encoding="utf-8")

        for token in (
            "const governedOfferings = new Set(",
            ".filter((row) => row.school_branch === governedBranch)",
            "governedOfferings.has(preset.program_offering)",
            "program_offering: governedOffering",
            "student_groups: governedOffering && preset.student_group",
            "courses: governedOffering && preset.course",
            "does not overlap this Instructor's Branch Governance eligibility period",
        ):
            self.assertIn(token, source)

    def test_partial_period_discovery_exposes_clipped_governed_windows(self):
        governance = BRANCH_GOVERNANCE.read_text(encoding="utf-8")
        search = LINK_SEARCH.read_text(encoding="utf-8")
        planner = PLANNER_API.read_text(encoding="utf-8")

        for token in (
            "def assignment_eligibility_overlap_periods",
            "start = max(_start(row.get(\"valid_from\")), target_start)",
            "end = min(_end(row.get(\"valid_to\")), target_end)",
            '"valid_from": str(start)',
            '"valid_to": str(end)',
        ):
            self.assertIn(token, governance)

        self.assertIn('"branch_eligibility_periods"', search)
        self.assertIn("assignment_eligibility_overlap_periods(", search)
        self.assertIn('"branch_eligibility_periods"', planner)
        self.assertIn("assignment_eligibility_overlap_periods(", planner)

    def test_partial_period_native_and_planner_forms_use_safe_date_windows(self):
        controller = ASSIGNMENT_CONTROLLER.read_text(encoding="utf-8")
        native = NATIVE_FORM.read_text(encoding="utf-8")
        planner = PLANNER_UI.read_text(encoding="utf-8")

        for token in (
            "assignment_eligibility_overlap_periods(",
            "This Class overlaps multiple Branch Eligibility periods",
            "if len(matching_windows) == 1",
        ):
            self.assertIn(token, controller)

        for token in (
            "branch_eligibility_periods",
            "eligibilityPeriods.length === 1",
            "Use a governed window",
        ):
            self.assertIn(token, native)

        for token in (
            "branch_eligibility_periods",
            "row.branch_eligibility_periods.length === 1",
            "eligibilityPeriodsLabel(row)",
        ):
            self.assertIn(token, planner)

    def test_native_form_queries_apply_same_period_governance(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        offering_query = source.split("def instructor_assignment_offering_query", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]
        class_arm_query = source.split("def instructor_assignment_class_arm_query", 1)[1].split(
            "@frappe.whitelist()", 1
        )[0]
        course_query = source.split("def instructor_assignment_course_query", 1)[1]

        self.assertIn("instructor=instructor", offering_query)
        self.assertIn("instructor=instructor", class_arm_query)
        self.assertIn("_assert_offering_period_governance(instructor, branch, offering)", course_query)

        native = NATIVE_FORM.read_text(encoding="utf-8")
        self.assertIn("get_assignment_offering_context", native)
        self.assertIn("branch_eligibility_full_period === false", native)
        self.assertIn('await clearFields(frm, ["student_group", "course", "valid_from", "valid_to"])', native)


if __name__ == "__main__":
    unittest.main()
