from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentReplacementContract(unittest.TestCase):
    def test_assignment_metadata_records_predecessor_successor_relationship(self):
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
        for fieldname in (
            "replaces_assignment",
            "replaced_by_assignment",
            "replacement_reason",
        ):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)
        self.assertEqual(fields["replaces_assignment"].get("options"), "EduEdge Instructor Assignment")
        self.assertEqual(fields["replaced_by_assignment"].get("options"), "EduEdge Instructor Assignment")
        self.assertEqual(metadata.get("track_changes"), 1)

    def test_replacement_preview_and_save_are_permission_aware_and_post_only(self):
        source = (APP / "api" / "instructor_assignment_replacement.py").read_text(encoding="utf-8")
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def preview_instructor_assignment_replacement",
            "def replace_instructor_assignment",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_replacement")',
            'require_eduedge_access(feature_key="academics", action="replace_instructor_assignment")',
            'doc.check_permission("write")',
            'doc.check_permission("read")',
            "assert_branch_access(doc.school_branch)",
        ):
            self.assertIn(token, source)

    def test_handover_semantics_have_no_same_day_overlap(self):
        source = (APP / "api" / "instructor_assignment_replacement.py").read_text(encoding="utf-8")
        for token in (
            "Handover Date cannot be earlier than today",
            "successor_start = getdate(add_days(handover, 1))",
            "source.valid_to = handover",
            "source.ended_on = handover",
            "successor.valid_from = successor_start",
            "No responsibility period remains after the Handover Date",
            "Replacement responsibility would start after the selected Class academic period",
        ):
            self.assertIn(token, source)

    def test_replacement_is_atomic_audited_and_idempotent(self):
        source = (APP / "api" / "instructor_assignment_replacement.py").read_text(encoding="utf-8")
        for token in (
            'savepoint = "eduedge_instructor_assignment_replace"',
            "frappe.db.savepoint(savepoint)",
            "for update",
            "frappe.db.rollback(save_point=savepoint)",
            '"action": "already-replaced"',
            "handover_date or source.ended_on or nowdate()",
            "successor.replaces_assignment = source.name",
            "successor.replacement_reason = resolved_reason",
            "source.replaced_by_assignment = successor.name",
            "source.ended_by = frappe.session.user",
            "source.end_reason = resolved_reason",
        ):
            self.assertIn(token, source)

    def test_replacement_preserves_outgoing_branch_access_and_only_ensures_incoming(self):
        source = (APP / "api" / "instructor_assignment_replacement.py").read_text(encoding="utf-8")
        self.assertIn("_ensure_incoming_branch_access", source)
        self.assertIn('"outgoing_branch_eligibility_changed": False', source)
        self.assertIn("_branch_access_preview(incoming.name, source.school_branch", source)
        self.assertNotIn("_save_branch_period(\n        source.instructor", source)

    def test_existing_identity_stays_immutable_during_lifecycle_actions(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"replaces_assignment"', controller)
        self.assertIn('"replaced_by_assignment"', controller)
        self.assertIn('"replacement_reason"', controller)
        self.assertNotIn('lifecycle_action and fieldname == "valid_from"', controller)
        self.assertIn("An Instructor Assignment cannot replace itself", controller)
        self.assertIn("Replacement assignments require a Replacement Reason", controller)

    def test_request_boundary_knows_replace_actions_are_mutations(self):
        source = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"replace_",', source)


if __name__ == "__main__":
    unittest.main()
