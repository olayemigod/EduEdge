from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorBranchGovernanceFlowContract(unittest.TestCase):
    def test_single_governance_service_requires_full_period_coverage(self):
        source = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")
        for token in (
            "def eligibility_covers_period",
            "def assert_instructor_branch_eligibility",
            "def eligible_branch_names",
            "def primary_branch",
            "start <= target_start and end >= target_end",
            "timedelta(days=1)",
            "Update Branch Governance first",
        ):
            self.assertIn(token, source)

    def test_assignment_controller_has_no_matrix_bypass(self):
        source = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        self.assertIn("assert_instructor_branch_eligibility", source)
        self.assertNotIn("in_eduedge_assignment_matrix_save", source)
        self.assertNotIn("def _has_branch_eligibility", source)

    def test_planner_never_mutates_instructor_eligibility(self):
        source = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "eligible_branch_names",
            "assert_instructor_branch_eligibility",
            "get_instructor_branch_eligibility_rows",
            "governance_verified_count",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "class PlannedBranchAccess",
            "def _save_branch_period",
            "def _ensure_academic_branch_access",
            'frappe.new_doc("EduEdge Instructor Branch Assignment")',
            'frappe.get_doc("EduEdge Instructor Branch Assignment"',
        ):
            self.assertNotIn(forbidden, source)

    def test_register_splits_governed_planner_from_historical_scope(self):
        source = (APP / "api" / "instructor_assignment_register.py").read_text(encoding="utf-8")
        for token in (
            "governed_names = eligible_branch_names",
            '"allowed_branches": governed',
            '"permitted_branches": permitted',
            '"register_offerings": register_offerings',
            '"register_groups": register_groups',
            '"register_courses": register_courses',
            "withdrawing eligibility never hides academic history",
        ):
            self.assertIn(token, source)
        self.assertNotIn("can_manage_branch_eligibility", source)
        self.assertNotIn("can_manage_branch_access", source)

    def test_legacy_teacher_matrix_cannot_mutate_eligibility(self):
        source = (APP / "api" / "teacher_assignments.py").read_text(encoding="utf-8")
        self.assertIn("The legacy Teacher Assignment matrix cannot save assignments or Branch Eligibility", source)
        self.assertIn("The legacy Teacher Assignment matrix has been retired", source)
        self.assertNotIn("def _ensure_branch_assignment", source)
        self.assertNotIn('frappe.new_doc("EduEdge Instructor Branch Assignment")', source)

    def test_branch_governance_is_the_authoring_surface(self):
        service = (APP / "services" / "branch_governance.py").read_text(encoding="utf-8")
        api = (APP / "api" / "branch_governance.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_branch_governance"
            / "EduEdgeBranchGovernance.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "include_instructor_eligibility",
            "_get_instructor_eligibility_rows",
            "academic_assignment_count",
        ):
            self.assertIn(token, service)
        for token in (
            "can_read_instructor_eligibility",
            "can_manage_instructor_eligibility",
        ):
            self.assertIn(token, api)
        for token in (
            "Instructor Branch Eligibility",
            "Add Instructor Eligibility",
            "Edit Eligibility",
            "Academic Assignments",
            "openInstructorEligibilityDialog",
        ):
            self.assertIn(token, component)

    def test_instructor_profile_cannot_author_primary_branch(self):
        backend = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructors"
            / "EduEdgeInstructors.vue"
        ).read_text(encoding="utf-8")
        self.assertIn("primary_branch", backend)
        self.assertIn("managed by Instructor Branch Eligibility in Branch Governance", backend)
        self.assertNotIn("def _ensure_branch_eligibility", backend)
        self.assertIn("Derived from the current Primary Instructor Branch Eligibility", component)
        self.assertIn("openBranchGovernance", component)

    def test_legacy_primary_field_is_mirrored_from_governance_only(self):
        source = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_branch_assignment"
            / "eduedge_instructor_branch_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "def _sync_instructor_primary_branch",
            "primary_branch(name)",
            "def on_update",
            "def after_delete",
        ):
            self.assertIn(token, source)

    def test_assignment_flow_never_mutates_user_branch_access(self):
        for relative in (
            "api/instructor_assignments.py",
            "api/instructor_assignment_register.py",
            "api/instructor_assignment_governance.py",
            "api/instructor_assignment_lifecycle.py",
            "api/teacher_assignments.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            for forbidden in (
                'frappe.new_doc("EduEdge User Branch Access")',
                'frappe.get_doc("EduEdge User Branch Access"',
                "save_branch_access(",
                "set_branch_access_enabled(",
            ):
                self.assertNotIn(forbidden, source, f"{relative}: {forbidden}")


    def test_native_instructor_primary_branch_is_governance_mirror_only(self):
        fields = (APP / "education" / "people_fields.py").read_text(encoding="utf-8")
        governance = (APP / "education" / "people_governance.py").read_text(encoding="utf-8")
        profiles = (APP / "api" / "instructor_profiles.py").read_text(encoding="utf-8")

        self.assertIn('"read_only": 1', fields)
        self.assertIn(
            "Compatibility mirror of the current Primary Instructor Branch Eligibility",
            fields,
        )
        self.assertIn("from eduedge.services.instructor_branch_governance import primary_branch", governance)
        self.assertIn("governed_primary = primary_branch(doc.name)", governance)
        self.assertIn("doc.set(INSTRUCTOR_PRIMARY_BRANCH_FIELD, governed_primary)", governance)
        self.assertIn("Primary Branch is managed by Instructor Branch Eligibility in Branch Governance", profiles)
        self.assertNotIn("def _ensure_branch_eligibility", profiles)
        self.assertIn("governed_primary = primary_branch(instructor)", fields)
        self.assertIn('for instructor in frappe.get_all("Instructor", pluck="name", limit_page_length=0)', fields)
        self.assertIn("values[INSTRUCTOR_PRIMARY_BRANCH_FIELD] = governed_primary", fields)


if __name__ == "__main__":
    unittest.main()
