from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentLifecycleBranchGovernanceContract(unittest.TestCase):
    def test_lifecycle_paths_never_mutate_instructor_branch_eligibility(self):
        forbidden = (
            "_save_branch_period",
            "_branch_periods",
            "_ensure_incoming_branch_access",
            "_branch_access_preview",
            'frappe.new_doc("EduEdge Instructor Branch Assignment")',
            'frappe.get_doc("EduEdge Instructor Branch Assignment"',
            'frappe.db.set_value("EduEdge Instructor Branch Assignment"',
        )
        for relative in (
            "api/instructor_assignment_replacement.py",
            "api/instructor_assignment_transfer.py",
            "api/instructor_assignment_preparation.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, source, f"{relative}: {token}")

    def test_lifecycle_paths_preview_and_assert_upstream_governance(self):
        for relative in (
            "api/instructor_assignment_replacement.py",
            "api/instructor_assignment_transfer.py",
            "api/instructor_assignment_preparation.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            for token in (
                "assignment_eligibility_preview",
                "assert_instructor_branch_eligibility",
                '"type": "branch-eligibility-blocked"',
            ):
                self.assertIn(token, source, f"{relative}: {token}")

    def test_governance_validation_precedes_lifecycle_mutation(self):
        cases = (
            ("api/instructor_assignment_replacement.py", "source.valid_to = handover"),
            ("api/instructor_assignment_transfer.py", "source.valid_to = transfer"),
            ("api/instructor_assignment_preparation.py", 'prepared = frappe.new_doc("EduEdge Instructor Assignment")'),
        )
        for relative, mutation in cases:
            source = (APP / relative).read_text(encoding="utf-8")
            assert_at = source.index("assert_instructor_branch_eligibility(")
            mutation_at = source.index(mutation)
            self.assertLess(assert_at, mutation_at, relative)

    def test_service_preview_is_read_only_and_never_promises_mutation(self):
        source = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")
        for token in (
            "def assignment_eligibility_preview",
            '"action": "covered" if covered else "blocked"',
            '"changed": False',
            '"governance_route": "/app/eduedge-branch-governance"',
            "No eligibility record will be changed",
        ):
            self.assertIn(token, source)

    def test_lifecycle_dialogs_offer_covered_or_blocked_only(self):
        components = (
            "public/js/eduedge_ui/components/InstructorAssignmentReplacementDialog.vue",
            "public/js/eduedge_ui/components/InstructorAssignmentTransferDialog.vue",
            "public/js/eduedge_ui/components/InstructorAssignmentPreparationDialog.vue",
        )
        forbidden = (
            "A Branch Eligibility period will be created",
            "Branch Eligibility will be extended",
            "Branch Eligibility period will be re-enabled",
        )
        for relative in components:
            source = (APP / relative).read_text(encoding="utf-8")
            self.assertIn("Branch Eligibility check", source)
            self.assertIn('action === "covered"', source)
            self.assertIn('action === "blocked"', source)
            self.assertIn('conflict?.type === "branch-eligibility-blocked"', source)
            for token in forbidden:
                self.assertNotIn(token, source, f"{relative}: {token}")


if __name__ == "__main__":
    unittest.main()
