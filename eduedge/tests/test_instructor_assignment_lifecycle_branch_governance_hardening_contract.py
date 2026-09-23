from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"

REPLACEMENT = APP / "api" / "instructor_assignment_replacement.py"
TRANSFER = APP / "api" / "instructor_assignment_transfer.py"
PREPARATION = APP / "api" / "instructor_assignment_preparation.py"
LIFECYCLE = APP / "api" / "instructor_assignment_lifecycle.py"

REPLACEMENT_UI = (
    APP / "public" / "js" / "eduedge_ui" / "components"
    / "InstructorAssignmentReplacementDialog.vue"
)
TRANSFER_UI = (
    APP / "public" / "js" / "eduedge_ui" / "components"
    / "InstructorAssignmentTransferDialog.vue"
)
PREPARATION_UI = (
    APP / "public" / "js" / "eduedge_ui" / "components"
    / "InstructorAssignmentPreparationDialog.vue"
)


class TestInstructorAssignmentLifecycleBranchGovernanceHardeningContract(unittest.TestCase):
    def test_replacement_reads_and_requires_branch_governance_without_mutating_it(self):
        source = REPLACEMENT.read_text(encoding="utf-8")

        for token in (
            "assignment_eligibility_covers_period",
            "assert_instructor_branch_eligibility",
            "def _branch_access_preview",
            "def _branch_governance_conflict",
            "def _require_incoming_branch_access",
            '"action": "existing" if covered else "required"',
            '"changed": False',
            '"branch-governance-required"',
        ):
            self.assertIn(token, source)

        for forbidden in (
            "_save_branch_period",
            "_branch_periods",
            "_ensure_incoming_branch_access",
        ):
            self.assertNotIn(forbidden, source)

        self.assertLess(
            source.index("branch_result = _require_incoming_branch_access"),
            source.index("source.valid_to = handover"),
        )

    def test_transfer_requires_destination_governance_before_mutating_source(self):
        source = TRANSFER.read_text(encoding="utf-8")

        for token in (
            "_branch_governance_conflict",
            "_require_incoming_branch_access",
            '"source_branch_eligibility_changed": False',
        ):
            self.assertIn(token, source)
        self.assertNotIn("_ensure_incoming_branch_access", source)
        self.assertLess(
            source.index("branch_result = _require_incoming_branch_access"),
            source.index("source.valid_to = transfer"),
        )

    def test_preparation_requires_destination_governance_before_creating_successor(self):
        source = PREPARATION.read_text(encoding="utf-8")

        for token in (
            "_branch_governance_conflict",
            "_require_incoming_branch_access",
            '"source_branch_eligibility_changed": False',
        ):
            self.assertIn(token, source)
        self.assertNotIn("_ensure_incoming_branch_access", source)
        self.assertLess(
            source.index("branch_result = _require_incoming_branch_access"),
            source.index('prepared = frappe.new_doc("EduEdge Instructor Assignment")'),
        )

    def test_previews_block_confirmation_when_branch_governance_is_missing(self):
        for path in (REPLACEMENT, TRANSFER, PREPARATION):
            source = path.read_text(encoding="utf-8")
            self.assertIn("_branch_governance_conflict", source)
            self.assertIn('"conflict_count": len(conflicts)', source)

        for path in (REPLACEMENT_UI, TRANSFER_UI, PREPARATION_UI):
            source = path.read_text(encoding="utf-8")
            self.assertIn("branch-governance-required", source)
            self.assertIn('action === "required"', source)
            self.assertNotIn('action === "create"', source)
            self.assertNotIn('action === "extend"', source)
            self.assertNotIn('action === "enable"', source)

    def test_end_action_is_row_locked_and_atomic(self):
        source = LIFECYCLE.read_text(encoding="utf-8")

        for token in (
            'savepoint = "eduedge_instructor_assignment_end"',
            "frappe.db.savepoint(savepoint)",
            "for update",
            "frappe.db.rollback(save_point=savepoint)",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
