from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentLifecycleContract(unittest.TestCase):
    def test_assignment_metadata_tracks_manual_end_without_deleting_history(self):
        metadata = json.loads(
            (
                APP
                / "eduedge"
                / "doctype"
                / "eduedge_instructor_assignment"
                / "eduedge_instructor_assignment.json"
            ).read_text(encoding="utf-8")
        )
        fields = {row.get("fieldname"): row for row in metadata["fields"]}
        for fieldname in ("ended_on", "ended_by", "end_reason"):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)
        self.assertEqual(metadata.get("track_changes"), 1)

    def test_end_action_is_post_only_permission_aware_and_does_not_touch_branch_access(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def end_instructor_assignment",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="end_instructor_assignment")',
            'doc.check_permission("write")',
            "assert_branch_access(doc.school_branch)",
            "End Date cannot be earlier than today",
            "cannot extend it",
            "branch_eligibility_changed",
            "doc.ended_on = resolved_end",
            "doc.ended_by = frappe.session.user",
            "doc.end_reason = resolved_reason",
            "frappe.flags.in_eduedge_assignment_lifecycle = True",
        ):
            self.assertIn(token, lifecycle)
        self.assertNotIn("doc.enabled = 0", lifecycle)
        self.assertNotIn(".delete(", lifecycle)
        self.assertNotIn("rename_doc", lifecycle)
        self.assertNotIn("EduEdge Instructor Branch Assignment", lifecycle)

    def test_existing_responsibility_identity_and_lifecycle_audit_are_protected(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            "IMMUTABLE_RESPONSIBILITY_FIELDS",
            "LIFECYCLE_AUDIT_FIELDS",
            "def _validate_existing_responsibility",
            "def _validate_lifecycle_audit",
            "cannot be edited in place",
            "Use End Assignment to shorten an existing responsibility period",
            "Lifecycle audit fields are maintained by EduEdge assignment actions",
            "Ended On must match the final Valid To date",
        ):
            self.assertIn(token, controller)

    def test_request_boundary_knows_end_actions_are_mutations(self):
        source = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"end_",', source)


if __name__ == "__main__":
    unittest.main()
