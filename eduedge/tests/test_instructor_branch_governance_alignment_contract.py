from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorBranchGovernanceAlignmentContract(unittest.TestCase):
    def test_eligibility_history_uses_all_user_permitted_branches_not_header_default(self):
        source = (APP / "api" / "instructor_assignment_register.py").read_text(encoding="utf-8")
        self.assertIn("eligibility_branches = allowed_names", source)
        self.assertIn(
            '"branch_assignments": core._branch_assignment_rows(instructor, eligibility_branches)',
            source,
        )
        self.assertNotIn("register_branches = selected or allowed_names", source)
        self.assertIn("can_manage_branch_eligibility", source)

    def test_instructor_assignment_flow_does_not_write_user_branch_access(self):
        for relative in (
            "api/instructor_assignments.py",
            "api/instructor_assignment_register.py",
            "api/instructor_assignment_governance.py",
            "api/instructor_assignment_lifecycle.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            self.assertNotIn("EduEdge User Branch Access", source, relative)
            self.assertNotIn("save_branch_access", source, relative)
            self.assertNotIn("set_branch_access_enabled", source, relative)

    def test_visible_instructor_language_calls_eligibility_not_user_access(self):
        runtime = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "branch_alignment.js"
        ).read_text(encoding="utf-8")
        for token in (
            "Add Branch Eligibility Row",
            "Branch Eligibility Only",
            "Branch eligibility changes",
            "Branch eligibility",
            "Instructor Branch Eligibility is not User Branch Access.",
            "User access, Branch switching and security scope are managed separately under Branch Governance.",
            "The header Branch is navigation context and does not narrow this Instructor's eligibility history.",
        ):
            self.assertIn(token, runtime)

    def test_alignment_runtime_is_loaded_with_instructor_assignment_bundle(self):
        helper = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "replacement_dialog.js"
        ).read_text(encoding="utf-8")
        self.assertIn('import "./branch_alignment";', helper)


if __name__ == "__main__":
    unittest.main()
