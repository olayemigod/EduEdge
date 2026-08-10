from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentPreparationContract(unittest.TestCase):
    def _api_source(self):
        return (APP / "api" / "instructor_assignment_preparation.py").read_text(encoding="utf-8")

    def test_assignment_metadata_records_preparation_origin_without_single_reverse_link(self):
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
        for fieldname in ("prepared_from_assignment", "preparation_reason"):
            self.assertIn(fieldname, fields)
            self.assertEqual(fields[fieldname].get("read_only"), 1)
            self.assertEqual(fields[fieldname].get("no_copy"), 1)
        self.assertEqual(fields["prepared_from_assignment"].get("options"), "EduEdge Instructor Assignment")
        self.assertNotIn("prepared_to_assignment", fields)
        self.assertEqual(metadata.get("title_field"), "assignment_title")
        self.assertEqual(metadata.get("track_changes"), 1)

    def test_preview_and_prepare_are_permission_aware_and_post_only(self):
        source = self._api_source()
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def preview_instructor_assignment_preparation",
            "def prepare_instructor_assignment_for_next_period",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_preparation")',
            'require_eduedge_access(feature_key="academics", action="prepare_instructor_assignment_for_next_period")',
            'doc.check_permission("read")',
            'branch.check_permission("read")',
            'offering.check_permission("read")',
            "assert_branch_access(branch_name)",
            'frappe.has_permission("EduEdge Instructor Assignment", "create")',
        ):
            self.assertIn(token, source)

    def test_preparation_requires_a_later_bounded_academic_period(self):
        source = self._api_source()
        for token in (
            "source_end = period_end or doc.valid_to",
            "Destination Academic Session / Term must have both start and end dates",
            "if period_start <= source_period_end",
            "Destination Class must belong to a later academic period than the source assignment.",
            "prepared_start = getdate(valid_from)",
            "prepared_end = getdate(valid_to)",
            "Destination Valid From must fall inside the selected Class academic period.",
            "Destination Valid To must fall inside the selected Class academic period.",
        ):
            self.assertIn(token, source)

    def test_source_is_not_mutated_and_identity_rules_are_preserved(self):
        source = self._api_source()
        for token in (
            "prepared.instructor = source.instructor",
            "prepared.assignment_type = _normalise_type(source.assignment_type)",
            "prepared.assignment_scope = source.assignment_scope",
            'prepared.school_branch = destination["school_branch"]',
            'prepared.program_offering = destination["program_offering"]',
            'prepared.student_group = destination.get("student_group")',
            'prepared.course = destination.get("course")',
            "prepared.prepared_from_assignment = source.name",
            '"source_changed": False',
            '"source_branch_eligibility_changed": False',
        ):
            self.assertIn(token, source)
        for forbidden in (
            "source.valid_to =",
            "source.ended_on =",
            "source.ended_by =",
            "source.end_reason =",
            "source.prepared_to_assignment =",
        ):
            self.assertNotIn(forbidden, source)

    def test_destination_context_is_branch_group_and_curriculum_safe(self):
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

    def test_conflicts_branch_eligibility_and_atomicity_reuse_proven_foundations(self):
        source = self._api_source()
        for token in (
            "_destination_conflicts(source, destination, start, end)",
            "_branch_access_preview(source.instructor, destination[\"school_branch\"], start, end)",
            "_ensure_incoming_branch_access(",
            'savepoint = "eduedge_instructor_assignment_prepare"',
            "frappe.db.savepoint(savepoint)",
            "for update",
            "frappe.db.rollback(save_point=savepoint)",
        ):
            self.assertIn(token, source)

    def test_exact_preparation_is_idempotent_and_history_is_not_rewritten(self):
        source = self._api_source()
        for token in (
            "def _existing_preparation",
            '"prepared_from_assignment": source.name',
            '"action": "already-prepared"',
            "same_dates and same_reason",
            "already has a prepared responsibility for the selected destination",
            "instead of duplicating or rewriting preparation history",
        ):
            self.assertIn(token, source)

    def test_controller_protects_preparation_audit_and_incoming_origin(self):
        controller = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")
        for token in (
            '"prepared_from_assignment"',
            '"preparation_reason"',
            "An Instructor Assignment cannot be prepared from itself.",
            "Prepared assignments require a Preparation Reason.",
            "Preparation Reason requires a Prepared From Assignment link.",
            "only one incoming lifecycle origin",
            "Next Period Preparation",
        ):
            self.assertIn(token, controller)

    def test_prepare_action_is_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"prepare_",', request_guard)


if __name__ == "__main__":
    unittest.main()
