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
            'doc.check_permission("write")',
            "Primary Instructor Branch Eligibility cannot be disabled",
            "still supported by {0} Instructor Assignment record(s)",
            "doc.enabled = 0",
            "doc.is_primary = 0",
            "doc.add_comment",
        ):
            self.assertIn(token, source)
        self.assertNotIn("doc.delete", source)
        self.assertNotIn("frappe.delete_doc", source)

    def test_branch_governance_surfaces_support_counts_and_status(self):
        service = (APP / "services" / "branch_governance.py").read_text(encoding="utf-8")
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_branch_governance"
            / "EduEdgeBranchGovernance.vue"
        ).read_text(encoding="utf-8")
        for token in (
            "_get_instructor_eligibility_rows",
            "academic_assignment_count",
            '"status": status',
            "Instructor Inactive",
        ):
            self.assertIn(token, service)
        for token in (
            "Instructor Branch Eligibility",
            "academic_assignment_count",
            "linked assignment",
            "Manage",
        ):
            self.assertIn(token, component)

    def test_primary_branch_rollover_is_daily_batched_and_idempotent(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        people = (APP / "education" / "people_fields.py").read_text(encoding="utf-8")
        governance = (APP / "services" / "instructor_branch_governance.py").read_text(encoding="utf-8")

        self.assertIn('"daily": [', hooks)
        self.assertIn(
            '"eduedge.education.people_fields.reconcile_instructor_primary_branches"',
            hooks,
        )

        start = people.index("def reconcile_instructor_primary_branches")
        end = people.index("def _backfill_instructor_primary_branches", start)
        reconcile = people[start:end]
        for token in (
            'filters={"enabled": 1, "is_primary": 1}',
            'fields=["instructor", "school_branch", "valid_from", "valid_to"]',
            "current_by_instructor",
            'fields=["name", INSTRUCTOR_PRIMARY_BRANCH_FIELD]',
            "candidates[0] if len(candidates) == 1 else None",
            "if (current or None) == (governed_primary or None)",
            "update_modified=False",
            '"checked": len(instructors)',
            '"updated": updated',
        ):
            self.assertIn(token, reconcile)
        self.assertNotIn("INSTITUTION_FIELD", reconcile)
        self.assertNotIn("primary_branch(", reconcile)

        for token in (
            "def primary_branch(instructor: str, *, on_date=None)",
            "day = getdate(on_date or nowdate())",
            "_start(row.get(\"valid_from\")) <= day <= _end(row.get(\"valid_to\"))",
        ):
            self.assertIn(token, governance)

    def test_reconciliation_remains_history_safe_and_not_assignment_side_authoring(self):
        alignment = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "branch_alignment.js"
        ).read_text(encoding="utf-8")
        planner = (APP / "api" / "instructor_assignments.py").read_text(encoding="utf-8")
        self.assertNotIn("disable_unused_instructor_branch_eligibility", alignment)
        self.assertNotIn("def _save_branch_period", planner)
        self.assertNotIn("def _ensure_academic_branch_access", planner)


if __name__ == "__main__":
    unittest.main()
