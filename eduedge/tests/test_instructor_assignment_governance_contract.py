from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentGovernanceContract(unittest.TestCase):
    def _api(self):
        return (APP / "api" / "instructor_assignment_governance.py").read_text(encoding="utf-8")

    def _controller(self):
        return (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_instructor_assignment"
            / "eduedge_instructor_assignment.py"
        ).read_text(encoding="utf-8")

    def test_disable_reenable_delete_are_manager_post_actions_with_feature_and_branch_checks(self):
        source = self._api()
        for token in (
            '@frappe.whitelist(methods=["POST"])',
            "def disable_instructor_assignment",
            "def reenable_instructor_assignment",
            "def delete_unused_instructor_assignment",
            "_require_assignment_manager()",
            'require_eduedge_access(feature_key="academics", action="disable_instructor_assignment")',
            'require_eduedge_access(feature_key="academics", action="reenable_instructor_assignment")',
            'require_eduedge_access(feature_key="academics", action="delete_unused_instructor_assignment")',
            "doc.check_permission(permission_type)",
            "assert_branch_access(doc.school_branch)",
            "for update",
            "frappe.db.savepoint(savepoint)",
            "frappe.db.rollback(save_point=savepoint)",
        ):
            self.assertIn(token, source)

    def test_disable_is_future_only_and_started_history_uses_end(self):
        source = self._api()
        for token in (
            "def _disable_capability",
            "if not cint(row.enabled)",
            "OUTGOING_HISTORY_FIELDS",
            "getdate(row.valid_from) <= today",
            "Started responsibilities must use End Assignment so academic history is preserved.",
            '"branch_eligibility_changed": False',
        ):
            self.assertIn(token, source)

    def test_reenable_revalidates_full_doctype_rules(self):
        source = self._api()
        for token in (
            "def _reenable_capability",
            "The Instructor must be active before this future responsibility can be re-enabled.",
            "_save_enabled(doc, 1)",
            "doc.save()",
            "Duplicate/primary",
            "Branch Eligibility",
        ):
            self.assertIn(token, source)

    def test_delete_is_disabled_future_unused_unreferenced_only(self):
        source = self._api()
        for token in (
            "def _delete_capability",
            "Disable the unused future assignment before deleting it.",
            "Started or historical Instructor Assignments cannot be deleted.",
            "ANY_LIFECYCLE_FIELDS",
            "Assignments with lifecycle or preparation history cannot be deleted.",
            "This assignment is referenced by another record and cannot be deleted.",
            "EduEdge could not prove that this assignment is unreferenced, so deletion is blocked.",
            "def _incoming_references",
            '"DocField"',
            '"Custom Field"',
            'fields=["dt", "fieldname"]',
            "frappe.delete_doc(ASSIGNMENT_DOCTYPE, doc.name)",
        ):
            self.assertIn(token, source)

    def test_controller_blocks_direct_enabled_mutation_and_direct_delete(self):
        source = self._controller()
        for token in (
            'before.get("enabled")',
            'self.get("enabled")',
            "Use Disable Assignment or Re-enable Assignment",
            "def on_trash(self)",
            '"in_eduedge_assignment_delete"',
            "Instructor Assignments cannot be deleted directly.",
        ):
            self.assertIn(token, source)

    def test_governed_disable_can_narrow_access_even_if_instructor_or_branch_access_changed(self):
        source = self._controller()
        for token in (
            "governed_disable = bool(",
            "in_eduedge_assignment_lifecycle",
            "instructor.status != \"Active\" and not governed_disable",
            "if governed_disable:",
            "narrows access rather than granting it",
        ):
            self.assertIn(token, source)

    def test_governance_actions_write_a_durable_reason_log(self):
        source = self._api()
        metadata = json.loads(
            (
                APP
                / "eduedge"
                / "doctype"
                / "eduedge_instructor_assignment_governance_log"
                / "eduedge_instructor_assignment_governance_log.json"
            ).read_text(encoding="utf-8")
        )
        for token in (
            "def _record_governance_log",
            "GOVERNANCE_LOG_DOCTYPE",
            "log.assignment_name = doc.name",
            "log.assignment_title = doc.assignment_title or doc.name",
            "log.reason = reason",
            "log.acted_by = frappe.session.user",
            "log.acted_on = now_datetime()",
            "log.insert(ignore_permissions=True)",
        ):
            self.assertIn(token, source)
        fields = {row["fieldname"]: row for row in metadata["fields"]}
        for fieldname in (
            "assignment_name",
            "assignment_title",
            "instructor",
            "school_branch",
            "action",
            "reason",
            "acted_by",
            "acted_on",
        ):
            self.assertIn(fieldname, fields)
        self.assertEqual(fields["action"]["options"], "Disable\nRe-enable\nDelete")
        self.assertFalse(any(row.get("delete") for row in metadata["permissions"]))

    def test_mutation_boundary_includes_disable_and_reenable(self):
        source = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"disable_",', source)
        self.assertIn('"reenable_",', source)
        self.assertIn('"delete_",', source)


if __name__ == "__main__":
    unittest.main()
