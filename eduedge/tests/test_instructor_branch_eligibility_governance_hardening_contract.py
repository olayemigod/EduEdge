from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
CONTROLLER = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.py"
)
DOCTYPE_JSON = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.json"
)


class TestInstructorBranchEligibilityGovernanceHardeningContract(unittest.TestCase):
    def test_eligibility_permissions_are_manager_only_and_audited(self):
        definition = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))
        roles = {row.get("role") for row in definition.get("permissions", [])}

        self.assertNotIn("Academics User", roles)
        for role in (
            "EduEdge Administrator",
            "School Administrator",
            "Academic Administrator",
            "Education Manager",
        ):
            self.assertIn(role, roles)
        self.assertEqual(definition.get("track_changes"), 1)

    def test_identity_history_and_delete_safety_are_server_side(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        for token in (
            "def _validate_identity",
            "Existing Instructor Branch Eligibility identity cannot be changed",
            "def on_trash",
            "has started or has no future start date cannot be deleted",
            "with linked academic responsibilities cannot be deleted",
            "def _has_linked_academic_responsibility",
        ):
            self.assertIn(token, source)

    def test_concurrent_overlap_and_primary_checks_are_serialized(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        self.assertIn("def _lock_instructor_scope", source)
        self.assertIn("for update", source.lower())
        self.assertLess(
            source.index("self._lock_instructor_scope()"),
            source.index("self._validate_duplicate()"),
        )
        self.assertLess(
            source.index("self._lock_instructor_scope()"),
            source.index("self._validate_primary()"),
        )

    def test_eligibility_respects_instructor_and_institution_status(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        for token in (
            "Instructor Branch Eligibility can be enabled only for an active Instructor",
            "Instructor Branch Eligibility can be enabled only for an enabled School Branch / Campus",
            "Cross-campus eligibility is allowed within the same Institution; cross-Institution eligibility is not",
            "INSTITUTION_FIELD",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
