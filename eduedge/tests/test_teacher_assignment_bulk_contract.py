from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentBulkContract(unittest.TestCase):
    def test_unified_page_uses_explicit_assignment_rows_not_global_cartesian_selection(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "Exact responsibility planner",
            "Add Academic Row",
            "Add Branch Access Row",
            "Assignment Row",
            "Duplicate",
            "Preview Exact Plan",
            "Each row owns one Branch and one Class",
            "Multiple Subjects or Class Arms selected inside that row apply only to that row",
            "rows: this.rows.map",
            "newRow(",
            "duplicateRow(row)",
            "coursesFor(row)",
            "groupsFor(row)",
        ):
            self.assertIn(token, component)
        for retired in (
            "form.branches.includes",
            "form.program_offerings.includes",
            "form.student_groups.includes",
            "form.courses.includes",
            "Skipped because the Subject is not configured for that Class",
        ):
            self.assertNotIn(retired, component)

    def test_row_planner_blocks_retired_cartesian_payloads_and_silent_skips(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "class PlannedAssignment",
            "class PlannedBranchAccess",
            "def _rows",
            "previous global Class × Class Arm × Subject assignment format has been retired",
            "use explicit Assignment Rows",
            "def _validate_batch_duplicates",
            "Institution Subject will be added to the selected Class curriculum",
            "add to Class curriculum",
            "curriculum_change_count",
            "curriculum_changes",
            '"row_summaries"',
            '"academic_record_count"',
            '"conflict_count"',
        ):
            self.assertIn(token, api)
        self.assertNotIn("skipped.append", api)
        self.assertNotIn("invalid_combinations_skipped", api)

    def test_class_and_subject_responsibilities_are_not_ambiguous(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for source in (api, controller):
            self.assertIn("Subject Instructor", source)
            self.assertIn("Class Teacher", source)
            self.assertIn("Form Teacher", source)
            self.assertIn("Head of Class / Level", source)
            self.assertIn("class responsibility", source)
            self.assertIn("separate Subject Instructor", source)
        self.assertIn("must be assigned to a specific Class Arm", api)
        self.assertIn("must use Class / Programme Offering scope", api)

    def test_subjects_are_validated_inside_each_exact_class_row(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "program_courses.get(offering.program",
            "course_institution",
            "selected Class belongs to another Branch or Institution",
            "Class Arm does not belong to the selected Programme Offering",
        ):
            self.assertIn(token, api)
        self.assertIn("These {{ courseLabel(row, true).toLowerCase() }} apply only to this row's selected Class", component)
        self.assertIn("courseLabel(row", component)

    def test_exact_existing_records_and_primary_responsibility_conflicts_are_checked(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "def _classify",
            "def _primary_conflicts",
            "UNIQUE_PRIMARY_ASSIGNMENT_TYPES",
            "another active primary Instructor",
            "if conflicts:",
        ):
            self.assertIn(token, api)
        self.assertIn("_validate_primary_responsibility", controller)
        self.assertNotIn("ignore_permissions", api)
        self.assertNotIn("frappe.db.set_value", api)

    def test_live_page_calls_only_authoritative_instructor_assignment_endpoints(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("eduedge.api.instructor_assignments.get_instructor_assignments_page", component)
        self.assertIn("eduedge.api.instructor_assignments.preview_instructor_assignment_batch", component)
        self.assertIn("eduedge.api.instructor_assignments.save_instructor_assignment_batch", component)
        self.assertNotIn("eduedge.api.teacher_assignments", component)

    def test_branch_eligibility_keeps_disjoint_periods_separate(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        branch_controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_branch_assignment"
            / "eduedge_instructor_branch_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "def _save_branch_period",
            "def _ensure_academic_branch_access",
            'action": "extended"',
            "academic_results, seen",
            '"academic_branch_periods_ensured"',
        ):
            self.assertIn(token, api)
        self.assertIn("overlapping Branch eligibility", branch_controller)
        self.assertIn("_date_ranges_overlap", branch_controller)
        self.assertNotIn("is already assigned to School Branch / Campus", branch_controller)

    def test_disabled_academic_rows_do_not_create_active_branch_access(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        self.assertIn("if not row.enabled:", api)
        self.assertIn("return None", api)
        self.assertIn('"not-found-disabled"', api)
        self.assertIn('doc.enabled = cint(row["requested_enabled"])', api)

    def test_assignment_manager_and_my_teaching_assignments_are_separated(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        permissions = (APP / "education" / "people_permissions.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "def _can_manage_assignments",
            "def _require_assignment_manager",
            "current_user_instructors",
            '"can_manage": _can_manage_assignments()',
        ):
            self.assertIn(token, api)
        self.assertIn("My Teaching Assignments", component)
        self.assertIn('v-if="canManage"', component)
        self.assertIn("Only authorised academic managers", api)
        self.assertIn("current_user_instructors", permissions)
        self.assertIn("_is_assignment_manager", permissions)

    def test_assignment_dates_default_to_and_stay_inside_class_period(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "period_start_date",
            "period_end_date",
            "Valid From cannot be earlier than the selected Class academic period",
            "Valid To cannot be later than the selected Class academic period",
        ):
            self.assertIn(token, api)
        self.assertIn("offering.period_start_date", component)
        self.assertIn("offering.period_end_date", component)

    def test_assignment_scope_and_subject_instructor_migration_are_idempotent(self):
        metadata = json.loads(
            (
                APP
                / "eduedge"
                / "doctype"
                / "eduedge_instructor_assignment"
                / "eduedge_instructor_assignment.json"
            ).read_text(encoding="utf-8")
        )
        service = (APP / "education" / "teaching_assignments.py").read_text(encoding="utf-8")
        install = (APP / "install.py").read_text(encoding="utf-8")
        fields = {row.get("fieldname"): row for row in metadata["fields"]}
        self.assertIn("Class / Programme Offering", fields["assignment_scope"]["options"])
        self.assertIn("Class Arm", fields["assignment_scope"]["options"])
        self.assertIn("Subject Instructor", fields["assignment_type"]["options"])
        self.assertNotIn("Subject Teacher\n", fields["assignment_type"]["options"])
        self.assertIn("set assignment_type = %s", service)
        self.assertIn("LEGACY_SUBJECT_TEACHER", service)
        self.assertIn("ensure_teaching_assignment_foundation()", install)

    def test_class_and_class_arm_links_preserve_row_context(self):
        loader = (
            APP
            / "eduedge"
            / "page"
            / "eduedge_instructor_assignments"
            / "eduedge_instructor_assignments.js"
        ).read_text(encoding="utf-8")
        class_arms = (
            APP
            / "public"
            / "js"
            / "eduedge_class_arms"
            / "EduEdgeClassArms.vue"
        ).read_text(encoding="utf-8")
        offerings = (
            APP
            / "eduedge"
            / "page"
            / "eduedge_program_offerings"
            / "eduedge_program_offerings.js"
        ).read_text(encoding="utf-8")
        for token in (
            'params.get("offering") || params.get("program_offering")',
            'params.get("student_group")',
            'params.get("course")',
            "proxy.applyRoutePreset?.(preset)",
        ):
            self.assertIn(token, loader)
        self.assertIn(
            "params = new URLSearchParams({ branch: this.draft.branch, offering: this.draft.offering, student_group: this.draft.name })",
            class_arms,
        )
        self.assertIn("/app/eduedge-instructor-assignments", class_arms)
        # Class Intake is now a setup-only surface. Instructor/curriculum links
        # preserve exact context from their dedicated workflows rather than a
        # competing Desk toolbar on the Intake page.
        self.assertIn("clear_inner_toolbar", offerings)
        self.assertIn("programme_offering_session_options.get_programme_offering_session_options", offerings)
        self.assertNotIn("open_offering_operation", offerings)
        self.assertNotIn('__("Class Operations")', offerings)


if __name__ == "__main__":
    unittest.main()
