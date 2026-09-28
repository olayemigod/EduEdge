from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
BATCH_API = APP / "api" / "instructor_assignments.py"
LINK_SEARCH = APP / "api" / "instructor_assignment_link_search.py"
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


class TestInstructorAssignmentAuthoringHardeningContract(unittest.TestCase):
    def test_batch_planner_never_changes_existing_assignment_status_directly(self):
        source = BATCH_API.read_text(encoding="utf-8")

        self.assertIn(
            "Existing assignment status differs. Use the governed Disable or Re-enable Assignment action",
            source,
        )
        self.assertIn(
            "Existing Instructor Assignment status cannot be changed from the batch planner",
            source,
        )
        self.assertNotIn('doc.enabled = cint(row["requested_enabled"])', source)

    def test_native_form_has_governed_cascading_link_queries(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        for token in (
            "def instructor_assignment_instructor_query",
            "def instructor_assignment_branch_query",
            "def instructor_assignment_offering_query",
            "def instructor_assignment_class_arm_query",
            "def instructor_assignment_course_query",
            "eligible_branch_names",
            "_assert_governed_branch",
            "assignments._require_assignment_manager()",
        ):
            self.assertIn(token, source)

    def test_native_course_query_is_curriculum_only(self):
        source = LINK_SEARCH.read_text(encoding="utf-8")

        start = source.index("def instructor_assignment_course_query")
        course_query = source[start:]
        self.assertIn("configured = core._course_membership", course_query)
        self.assertIn('"name": ["in", sorted(configured)]', course_query)
        self.assertIn(
            "planner-only curriculum additions stay on EdgeSuite",
            course_query,
        )

    def test_native_form_clears_stale_dependent_values(self):
        source = NATIVE_FORM.read_text(encoding="utf-8")

        for token in (
            'frm.set_query("instructor"',
            'frm.set_query("school_branch"',
            'frm.set_query("program_offering"',
            'frm.set_query("student_group"',
            'frm.set_query("course"',
            '"school_branch"',
            '"program_offering"',
            '"student_group"',
            '"course"',
            "applyOfferingContext",
        ):
            self.assertIn(token, source)

    def test_assignment_conflict_checks_are_serialized_by_institution(self):
        source = ASSIGNMENT_CONTROLLER.read_text(encoding="utf-8")

        self.assertIn("def _lock_assignment_scope", source)
        self.assertIn("tabEduEdge Institution", source)
        self.assertIn("for update", source.lower())
        self.assertLess(
            source.index("self._lock_assignment_scope()"),
            source.index("self._validate_duplicate()"),
        )
        self.assertLess(
            source.index("self._lock_assignment_scope()"),
            source.index("self._validate_primary_responsibility()"),
        )

    def test_new_assignment_defaults_to_selected_academic_period(self):
        controller = ASSIGNMENT_CONTROLLER.read_text(encoding="utf-8")
        native = NATIVE_FORM.read_text(encoding="utf-8")

        for token in (
            "def _academic_period_dates",
            "if self.is_new():",
            "if not self.valid_from and period_start",
            "if not self.valid_to and period_end",
            "Valid From cannot be earlier than the selected Class academic period",
            "Valid From cannot be later than the selected Class academic period",
            "Valid To cannot be earlier than the selected Class academic period",
            "Valid To cannot be later than the selected Class academic period",
            '"term_start_date", "term_end_date"',
            '"year_start_date", "year_end_date"',
        ):
            self.assertIn(token, controller)

        batch = BATCH_API.read_text(encoding="utf-8")
        self.assertIn("resolved Valid To cannot be earlier than Valid From", batch)

        for token in (
            "get_assignment_offering_context",
            "period_start_date",
            "period_end_date",
            "branch_eligibility_full_period === false",
            "branch_eligibility_periods",
            "eligibilityPeriods.length === 1",
            "singleWindow ? (singleWindow.valid_from || null)",
            "singleWindow ? (singleWindow.valid_to || null)",
            "row.period_start_date || null",
            "row.period_end_date || null",
        ):
            self.assertIn(token, native)

    def test_existing_native_assignment_identity_is_read_only(self):
        source = NATIVE_FORM.read_text(encoding="utf-8")

        for fieldname in (
            "instructor",
            "assignment_type",
            "assignment_scope",
            "school_branch",
            "program_offering",
            "student_group",
            "course",
            "valid_from",
            "valid_to",
        ):
            self.assertIn(f'"{fieldname}"', source)
        self.assertIn('frm.set_df_property(fieldname, "read_only", locked ? 1 : 0)', source)
        self.assertIn("Use EduEdge End, Replace, Transfer, Prepare, Disable or Re-enable actions", source)


if __name__ == "__main__":
    unittest.main()
