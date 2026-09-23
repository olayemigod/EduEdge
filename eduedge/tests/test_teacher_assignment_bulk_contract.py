from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentBulkContract(unittest.TestCase):
    def test_unified_page_uses_explicit_governed_assignment_rows(self):
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
            "Assignment Row",
            "Duplicate",
            "Preview Exact Plan",
            "Each row owns one governed Branch and one Class",
            "rows: this.rows.map",
            "newRow(",
            "duplicateRow(row)",
            "InstructorAssignmentSearchFields",
            ':row="row"',
            "Open Branch Governance",
            "Instructor Assignments cannot create or widen Branch eligibility",
        ):
            self.assertIn(token, component)
        for retired in (
            "Add Branch Access Row",
            "addBranchAccessRow",
            "Branch Eligibility Only",
            "form.branches.includes",
            "form.program_offerings.includes",
            "form.student_groups.includes",
            "form.courses.includes",
        ):
            self.assertNotIn(retired, component)

    def test_row_planner_blocks_retired_cartesian_and_branch_only_payloads(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "class PlannedAssignment",
            "def _rows",
            "previous global Class × Class Arm × Subject assignment format has been retired",
            "use explicit Assignment Rows",
            "Branch Eligibility is managed only in Branch Governance",
            "def _validate_batch_duplicates",
            "Institution Subject will be added to the selected Class curriculum",
            "curriculum_change_count",
            "curriculum_changes",
            '"row_summaries"',
            '"academic_record_count"',
            '"conflict_count"',
        ):
            self.assertIn(token, api)
        self.assertNotIn("class PlannedBranchAccess", api)
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
        search_fields = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "InstructorAssignmentSearchFields.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "program_courses.get(offering.program",
            "course_institution",
            "selected Class belongs to another Branch or Institution",
            "Class Arm does not belong to the selected Programme Offering",
        ):
            self.assertIn(token, api)
        self.assertIn("Multiple Subjects or Class Arms selected inside that row apply only to that row", component)
        self.assertIn("courseLabel(row", component)
        self.assertIn("EduEdgeMultiLinkField", search_fields)
        self.assertIn(':context="{ branch: row.branch, program_offering: row.program_offering }"', search_fields)

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

    def test_branch_governance_coverage_is_required_and_never_created_by_planner(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        service = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")
        branch_controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_branch_assignment"
            / "eduedge_instructor_branch_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "assert_instructor_branch_eligibility",
            "eligible_branch_names",
            "get_instructor_branch_eligibility_rows",
            "governance_verified_count",
        ):
            self.assertIn(token, api)
        for forbidden in (
            "def _save_branch_period",
            "def _ensure_academic_branch_access",
            'frappe.new_doc("EduEdge Instructor Branch Assignment")',
            "academic_branch_periods_ensured",
        ):
            self.assertNotIn(forbidden, api)
        self.assertIn("start <= target_start and end >= target_end", service)
        self.assertIn("overlapping Branch eligibility", branch_controller)
        self.assertIn("_date_ranges_overlap", branch_controller)

    def test_disabled_academic_rows_do_not_widen_branch_governance(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        self.assertIn("assert_instructor_branch_eligibility", api)
        self.assertNotIn("branch_access_changed", api)
        self.assertNotIn("academic_branch_eligibility", api)
        self.assertNotIn("def _save_branch_period", api)

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

    def test_assignment_dates_stay_inside_class_and_governance_periods(self):
        api = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        search_api = (APP / "api" / "instructor_assignment_link_search.py").read_text(encoding="utf-8")
        for token in (
            "period_start_date",
            "period_end_date",
            "Valid From cannot be earlier than the selected Class academic period",
            "Valid To cannot be later than the selected Class academic period",
            "assert_instructor_branch_eligibility",
        ):
            self.assertIn(token, api)
        self.assertIn('row["period_start_date"], row["period_end_date"]', search_api)
        self.assertIn("option?.period_start_date", component)
        self.assertIn("option?.period_end_date", component)

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


if __name__ == "__main__":
    unittest.main()
