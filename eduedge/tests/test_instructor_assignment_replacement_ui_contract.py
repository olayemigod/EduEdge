from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentReplacementUIContract(unittest.TestCase):
    def test_lifecycle_state_exposes_server_authoritative_replace_capability_and_links(self):
        lifecycle = (APP / "api" / "instructor_assignment_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            'return "Replaced"',
            '"can_replace"',
            "has_successor_period",
            'status == "Current"',
            '"replaced_by_assignment"',
            '"replaced_by"',
            '"replaces_assignment"',
            '"replaces"',
            '"replacement_reason"',
            "def _relation_summaries",
            'frappe.get_list(\n        "EduEdge Instructor Assignment"',
        ):
            self.assertIn(token, lifecycle)

    def test_register_surfaces_replace_action_and_relationship_history(self):
        bundle = (APP / "public" / "js" / "eduedge_instructor_assignments.bundle.js").read_text(encoding="utf-8")
        for token in (
            'openInstructorAssignmentReplacementDialog',
            'item.can_replace',
            '"Replace / Handover"',
            'item?.lifecycle_status === "Replaced"',
            '"Replaced by ${person}"',
            '"Replaces ${person}"',
            '"Open linked assignment"',
            "syncReplacementRegister",
            "installReplacementRegisterEnhancer",
        ):
            self.assertIn(token, bundle)

    def test_dialog_previews_before_confirming_and_uses_permission_filtered_active_instructor_link(self):
        dialog = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "replacement_dialog.js"
        ).read_text(encoding="utf-8")
        for token in (
            'title: __("Replace / Handover Instructor Assignment")',
            'fieldname: "replacement_instructor"',
            'options: "Instructor"',
            'filters: { status: "Active", name: ["!=", item.instructor] }',
            'fieldname: "handover_date"',
            'fieldname: "reason"',
            '__("Preview Replacement")',
            'preview_instructor_assignment_replacement',
            '__("Confirm Replacement")',
            'replace_instructor_assignment',
            'type: "POST"',
            'sameArgs(currentArgs, previewedArgs)',
            'Replacement details changed after preview',
            'Branch Eligibility impact',
            "The outgoing Instructor's Branch Eligibility is not changed",
            "successor.valid_from",
            "successor.valid_to",
            "plan?.conflicts",
        ):
            self.assertIn(token, dialog)

    def test_dialog_does_not_bypass_backend_lifecycle_write_path(self):
        dialog = (
            APP
            / "public"
            / "js"
            / "eduedge_instructor_assignments"
            / "replacement_dialog.js"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "frappe.db.set_value",
            "frappe.client.set_value",
            "frappe.db.insert",
            "frappe.client.insert",
            "frappe.client.save",
        ):
            self.assertNotIn(forbidden, dialog)

    def test_replace_actions_are_covered_by_global_post_only_boundary(self):
        request_guard = (APP / "security" / "request_method.py").read_text(encoding="utf-8")
        self.assertIn('"replace_",', request_guard)


if __name__ == "__main__":
    unittest.main()
