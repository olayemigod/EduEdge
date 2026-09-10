from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorBranchEligibilityReconciliationContract(unittest.TestCase):
    def test_review_api_flags_enabled_eligibility_without_assignment_support(self):
        source = (APP / "api" / "instructor_branch_eligibility.py").read_text(encoding="utf-8")
        for token in (
            "get_instructor_branch_eligibility_review",
            "supporting_assignment_count",
            "review_required",
            "review_reason",
            "No academic assignment supports this eligibility period",
            "active_branch_count",
            "review_required_count",
        ):
            self.assertIn(token, source)

    def test_cleanup_disables_only_no_support_non_primary_rows_and_preserves_history(self):
        source = (APP / "api" / "instructor_branch_eligibility.py").read_text(encoding="utf-8")
        for token in (
            'methods=["POST"]',
            "disable_unused_instructor_branch_eligibility",
            "doc.check_permission(\"write\")",
            "Primary Instructor Branch Eligibility cannot be disabled",
            "still supported by {0} Instructor Assignment record(s)",
            "doc.enabled = 0",
            "doc.is_primary = 0",
            "doc.add_comment",
        ):
            self.assertIn(token, source)
        self.assertNotIn("doc.delete", source)
        self.assertNotIn("frappe.delete_doc", source)

    def test_assignment_page_surfaces_review_required_branches(self):
        source = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "branch_alignment.js"
        ).read_text(encoding="utf-8")
        for token in (
            "get_instructor_branch_eligibility_review",
            "Review required",
            "have no supporting academic assignment",
            "will not remove it automatically",
            "enabled Branch",
            "review_required_count",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
