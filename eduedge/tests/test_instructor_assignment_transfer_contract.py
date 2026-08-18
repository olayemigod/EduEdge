from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentTransferContract(unittest.TestCase):
    def _api_source(self):
        return (APP / "api" / "instructor_assignment_transfer.py").read_text(encoding="utf-8")

    def test_assignment_metadata_records_transfer_chain(self):
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
            "transferred_from_assignment",
            "transferred_to_assignment",
            "transfer_reason",
        ):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)
        self.assertEqual(fields["transferred_from_assignment"].get("options"), "EduEdge Instructor Assignment")
        self.assertEqual(fields["transferred_to_assignment"].get("options"), "EduEdge Instructor Assignment")
        self.assertEqual(metadata.get("title_field"), "assignment_title")
        self.assertEqual(metadata.get("track_changes"), 1)

    def test_transfer_preview_and_commit_are_permission_aware_and_post_only(self):
        source = self._api_source()
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def preview_instructor_assignment_transfer",
            "def transfer_instructor_assignment",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_transfer")',
            'require_eduedge_access(feature_key="academics", action="transfer_instructor_assignment")',
            'doc.check_permission("write")',
            'branch.check_permission("read")',
            'offering.check_permission("read")',
            "assert_branch_access(branch_name)",
        ):
            self.assertIn(token, source)

    def test_transfer_preserves_instructor_type_scope_and_creates_new_context(self):
        source = self._api_source()
        for token in (
            "successor.instructor = source.instructor",
            "successor.assignment_type = _normalise_type(source.assignment_type)",
            "successor.assignment_scope = source.assignment_scope",
            'successor.school_branch = destination["school_branch"]',
            'successor.program_offering = destination["program_offering"]',
            'successor.student_group = destination.get("student_group")',
            'successor.course = destination.get("course")',
            "Transfer destination must differ from the current academic responsibility.",
        ):
            self.assertIn(token, source)
        for forbidden in (
            "source.school_branch =",
            "source.program_offering =",
            "source.student_group =",
            "source.course =",
            "source.instructor =",
        ):
            self.assertNotIn(forbidden, source)

    def test_transfer_date_and_destination_period_cannot_widen_history(self):
        source = self._api_source()
        for token in (
            "Transfer Date cannot be earlier than today",
            "return getdate(add_days(transfer, 1))",
            "source.valid_to = transfer",
            "source.ended_on = transfer",
            "successor.valid_from = successor_start",
            "end_candidates.append(getdate(source.valid_to))",
            "end_candidates.append(getdate(period_end))",
            "successor_end = min(end_candidates) if end_candidates else None",
            "No responsibility period remains in the destination after the Transfer Date.",
        ):
            self.assertIn(token, source)

    def test_destination_context_is_branch_class_group_and_curriculum_safe(self):
        source = self._api_source()
        for token in (
            "Destination Class / Programme Offering must belong to the selected Branch.",
            "Destination Class / Programme Offering must belong to the selected Institution.",
            "Destination Class Arm / Student Group must belong to the selected Branch.",
            "Destination Class Arm / Student Group Programme must match the selected Class.",
            "Destination Class Arm Academic Session must match the selected Class.",
            "Destination Class Arm Term must match the selected Class.",
            "Destination Subject / Course must belong to the selected Institution.",
            "Destination Subject / Course is not configured for the selected Class / Programme Offering.",
            'frappe.db.exists(\n            "Program Course"',
        ):
            self.assertIn(token, source)
        self.assertNotIn("_apply_curriculum_additions", source)

    def test_transfer_conflicts_cover_exact_overlap_and_primary_responsibility(self):
        source = self._api_source()
        for token in (
            "def _destination_conflicts",
            '"transferring-instructor-overlap"',
            '"primary-responsibility-overlap"',
            "UNIQUE_PRIMARY_ASSIGNMENT_TYPES",
            "_overlap(successor_start, successor_end",
            '"conflict_count": len(conflicts)',
            'Transfer plan has {0} conflict(s). Resolve them before saving.',
        ):
            self.assertIn(token, source)

    def test_transfer_is_atomic_idempotent_and_does_not_rewrite_history(self):
        source = self._api_source()
        for token in (
            'savepoint = "eduedge_instructor_assignment_transfer"',
            "frappe.db.savepoint(savepoint)",
            "for update",
            "frappe.db.rollback(save_point=savepoint)",
            '"action": "already-transferred"',
            "transfer_date or source.ended_on or nowdate()",
            "successor.transferred_from_assignment = source.name",
            "successor.transfer_reason = resolved_reason",
            "source.transferred_to_assignment = successor.name",
            "This Instructor Assignment was already transferred. Its transfer history will not be rewritten.",
        ):
            self.assertIn(token, source)

    def test_transfer_preserves_source_branch_access_and_only_ensures_destination(self):
        source = self._api_source()
        self.assertIn("_ensure_incoming_branch_access", source)
        self.assertIn('"source_branch_eligibility_changed": False', source)
        self.assertIn("_branch_access_preview(\n        source.instructor,\n        destination[\"school_branch\"]", source)
        self.assertNotIn("_save_branch_period(\n        source.instructor,\n        source.school_branch", source)

    def test_controller_protects_transfer_audit_without_blocking_lifecycle_chains(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            '"transferred_from_assignment"',
            '"transferred_to_assignment"',
            '"transfer_reason"',
            "An Instructor Assignment cannot transfer from itself",
            "An Instructor Assignment cannot transfer to itself",
            "Transferred assignments require a Transfer Reason",
            "Transfer Reason requires a Transferred From Assignment link",
            "only one incoming lifecycle origin",
            "only one outgoing lifecycle successor",
        ):
            self.assertIn(token, controller)
        self.assertNotIn('lifecycle_action and fieldname == "valid_from"', controller)

    def test_lifecycle_api_exposes_transfer_state_and_capability_without_weakening_end(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            'return "Transferred"',
            '"transferred_from_assignment"',
            '"transferred_to_assignment"',
            '"transfer_reason"',
            '"can_transfer": can_successor_action',
            '"transferred_to": relations.get(row.transferred_to_assignment or "")',
            '"transferred_from": relations.get(row.transferred_from_assignment or "")',
            "can_end = bool(",
            "can_successor_action = bool(can_end and has_successor_period)",
        ):
            self.assertIn(token, lifecycle)

    def test_request_boundary_knows_transfer_actions_are_mutations(self):
        source = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"transfer_",', source)


if __name__ == "__main__":
    unittest.main()
