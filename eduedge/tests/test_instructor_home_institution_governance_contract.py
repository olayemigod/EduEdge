from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorHomeInstitutionGovernanceContract(unittest.TestCase):
    def test_new_assignment_authoring_requires_home_institution_alignment(self):
        source = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")

        for token in (
            "def instructor_home_institution",
            "def branch_matches_instructor_home_institution",
            "def assignment_eligibility_covers_period",
            "require_home=True",
            "Instructor Home Institution is required before creating a new academic responsibility",
            "The selected Branch is outside the Instructor Home Institution",
        ):
            self.assertIn(token, source)

        # Historical runtime truth remains separate from stricter new-authoring checks.
        self.assertIn("def eligibility_covers_period", source)
        self.assertIn(
            "return eligibility_covers_period(instructor, branch, valid_from, valid_to)",
            source,
        )

    def test_assignment_planner_filters_out_unclassified_or_cross_institution_branches(self):
        source = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")

        self.assertIn("def eligible_branch_names", source)
        self.assertIn("branch_matches_instructor_home_institution(", source)
        self.assertIn("require_home=True", source)

    def test_session_launch_uses_strict_assignment_authoring_eligibility(self):
        source = (APP / "api" / "session_launch_delivery.py").read_text(encoding="utf-8")

        self.assertIn("assignment_eligibility_covers_period", source)
        self.assertNotIn(
            "from eduedge.services.instructor_branch_governance import eligibility_covers_period",
            source,
        )

    def test_eligibility_doc_allows_safe_narrowing_of_invalid_legacy_history(self):
        source = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_branch_assignment"
            / "eduedge_instructor_branch_assignment.py"
        ).read_text(encoding="utf-8")

        for token in (
            "def _is_narrowing_update",
            "new_start < old_start or new_end > old_end",
            "cint(self.is_primary) > cint(before.is_primary)",
            "Legacy Instructor profiles must be classified before receiving new academic responsibilities",
            "Existing historical eligibility may be shortened or disabled, but cannot be widened",
        ):
            self.assertIn(token, source)

    def test_branch_governance_surfaces_home_institution_data_quality_blockers(self):
        service = (APP / "services" / "branch_governance.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_branch_governance"
            / "EduEdgeBranchGovernance.vue"
        ).read_text(encoding="utf-8")

        for token in (
            "Needs Home Institution",
            "Institution Mismatch",
            "governance_note",
            "instructor_fields",
            "has_field(INSTITUTION_FIELD)",
        ):
            self.assertIn(token, service)

        for token in (
            "eligibility.governance_note",
            "Needs Home Institution",
            "Institution Mismatch",
        ):
            self.assertIn(token, component)

    def test_runtime_consumers_keep_historical_eligibility_semantics(self):
        for relative in (
            "education/teaching_assignments.py",
            "education/instructor_assignment_capabilities.py",
            "education/instructor_assignments.py",
        ):
            source = (APP / relative).read_text(encoding="utf-8")
            self.assertIn(
                "eligibility_covers_period",
                source,
                f"{relative} should preserve historical runtime compatibility",
            )


if __name__ == "__main__":
    unittest.main()
