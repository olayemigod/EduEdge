from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorBranchGovernanceAlignmentContract(unittest.TestCase):
    def test_branch_governance_is_upstream_of_assignment_planner(self):
        source = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "eligible_branch_names",
            "get_instructor_branch_eligibility_rows",
            "assert_instructor_branch_eligibility",
            '"permitted_branches": permitted',
            '"route": "/app/eduedge-branch-governance"',
            "Branch Eligibility is managed only in Branch Governance",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "class PlannedBranchAccess",
            "def _save_branch_period",
            "def _ensure_academic_branch_access",
            "in_eduedge_assignment_matrix_save",
        ):
            self.assertNotIn(forbidden, source)

    def test_instructor_assignment_flow_does_not_write_user_branch_access(self):
        forbidden_writes = (
            'frappe.new_doc("EduEdge User Branch Access")',
            'frappe.get_doc("EduEdge User Branch Access"',
            'frappe.db.set_value("EduEdge User Branch Access"',
            'frappe.db.delete("EduEdge User Branch Access"',
            "save_branch_access(",
            "set_branch_access_enabled(",
        )
        for relative in (
            "api/instructor_assignments.py",
            "api/instructor_assignment_register.py",
            "api/instructor_assignment_governance.py",
            "api/instructor_assignment_lifecycle.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            for token in forbidden_writes:
                self.assertNotIn(token, source, f"{relative}: {token}")

    def test_assignment_ui_consumes_governance_without_eligibility_authoring(self):
        source = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "Open Branch Governance",
            "Manage in Branch Governance",
            "Branch options come only from this Instructor",
            "Instructor Assignments cannot create or widen Branch eligibility",
            "Instructor Branch Eligibility",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "Add Branch Access Row",
            "Add Branch Eligibility Row",
            "Branch Eligibility Only",
            "addBranchAccessRow",
        ):
            self.assertNotIn(forbidden, source)

    def test_branch_governance_owns_instructor_eligibility_surface(self):
        source = (
            APP
            / "public"
            / "js"
            / "eduedge_branch_governance"
            / "EduEdgeBranchGovernance.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "Instructor Branch Eligibility",
            "Add Instructor Eligibility",
            "Edit Eligibility",
            "Academic Assignments",
            "can_manage_instructor_eligibility",
            "can_view_instructor_eligibility",
        ):
            self.assertIn(token, source)

    def test_compatibility_alignment_runtime_is_read_only_noop(self):
        source = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "branch_alignment.js"
        ).read_text(encoding="utf-8")
        self.assertIn("Branch Governance", source)
        self.assertIn("must not add Branch Eligibility authoring controls", source)
        self.assertNotIn("get_instructor_branch_eligibility_review", source)
        self.assertNotIn("Add Branch Eligibility Row", source)


if __name__ == "__main__":
    unittest.main()
