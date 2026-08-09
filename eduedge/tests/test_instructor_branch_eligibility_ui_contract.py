from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (
    ROOT
    / "eduedge"
    / "public"
    / "js"
    / "eduedge_instructor_assignments"
    / "EduEdgeInstructorAssignments.vue"
)


class TestInstructorBranchEligibilityUIContract(unittest.TestCase):
    def test_branch_periods_group_by_branch_without_collapsing_history(self):
        source = COMPONENT.read_text(encoding="utf-8")
        for token in (
            "branchEligibilityGroups",
            "group.periods",
            "eligibility period",
            "Branch{{ branchEligibilityGroups.length === 1 ? '' : 'es' }}",
            "Period{{ data.branch_assignments.length === 1 ? '' : 's' }}",
        ):
            self.assertIn(token, source)
        self.assertNotIn('v-for="item in data.branch_assignments"', source)

    def test_branch_period_status_is_effective_date_aware(self):
        source = COMPONENT.read_text(encoding="utf-8")
        for token in (
            "branchPeriodStatus(item)",
            'label: "Disabled"',
            'label: "Scheduled"',
            'label: "Ended"',
            'label: "Current"',
            "frappe.datetime?.get_today?.()",
        ):
            self.assertIn(token, source)
        self.assertNotIn(':label="item.enabled ? \'Active\' : \'Disabled\'"', source)


if __name__ == "__main__":
    unittest.main()
