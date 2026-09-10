from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentLifecycleUIContract(unittest.TestCase):
    def test_register_uses_server_authoritative_lifecycle_state(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        api = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")

        for token in (
            "Instructor Assignment Register",
            "get_instructor_assignment_lifecycle_states",
            "assignmentStatus(item)",
            "Current",
            "Scheduled",
            "Ended",
            "Disabled",
            "Status unavailable",
        ):
            self.assertIn(token, component)

        for token in (
            "def get_instructor_assignment_lifecycle_states",
            "def _lifecycle_status",
            'status == "Current"',
            '"can_end"',
            '"ended_on"',
            '"ended_by"',
            '"end_reason"',
        ):
            self.assertIn(token, api)

        self.assertNotIn(":label=\"item.enabled ? 'Active' : 'Disabled'\"", component)

    def test_relation_enrichment_cannot_take_down_core_lifecycle_state(self):
        api = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            "def _readable_instructor_from_assignment",
            'title.split(" · ", 1)[0].strip()',
            "Relationship enrichment must never be required to calculate lifecycle state.",
            "relation_enrichment_available = True",
            "try:\n        relations = _relation_summaries(rows)",
            "except Exception:",
            "relations = {}",
            "relation_enrichment_available = False",
            '"relation_enrichment_available": relation_enrichment_available',
            "EduEdge Instructor Assignment relationship enrichment failed",
        ):
            self.assertIn(token, api)

        # Readable relationship labels should not depend on a denormalized assignment
        # column whose absence can take down the lifecycle endpoint.
        relation_block = api.split("def _relation_summaries", 1)[1].split("@frappe.whitelist()", 1)[0]
        self.assertNotIn('"instructor_name",', relation_block)

    def test_end_action_is_manager_only_and_uses_confirming_dialog(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")

        for token in (
            "canEndAssignment(item)",
            "this.canManage && item.can_end",
            "End Instructor Assignment",
            "End Assignment",
            "Final day on which this responsibility remains valid.",
            "Why is this responsibility ending?",
            "end_instructor_assignment",
            'type: "POST"',
            "Branch Eligibility history are preserved",
            "await this.load()",
        ):
            self.assertIn(token, component)

    def test_lifecycle_state_failure_is_fail_closed_for_end_action(self):
        component = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "EduEdgeInstructorAssignments.vue"
        ).read_text(encoding="utf-8")
        self.assertIn('lifecycle_status: "Unavailable", can_end: false', component)
        self.assertIn("Instructor Assignment lifecycle state could not load", component)

    def test_end_actions_are_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"end_",', request_guard)


if __name__ == "__main__":
    unittest.main()
