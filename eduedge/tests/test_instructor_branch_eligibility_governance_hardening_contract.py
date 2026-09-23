from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
CONTROLLER = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.py"
)
DOCTYPE_JSON = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.json"
)
MODAL_RECORDS = APP / "api" / "modal_records.py"
NATIVE_FORM = (
    APP
    / "eduedge"
    / "doctype"
    / "eduedge_instructor_branch_assignment"
    / "eduedge_instructor_branch_assignment.js"
)


class TestInstructorBranchEligibilityGovernanceHardeningContract(unittest.TestCase):
    def test_eligibility_permissions_are_manager_only_and_audited(self):
        definition = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))
        roles = {row.get("role") for row in definition.get("permissions", [])}

        self.assertNotIn("Academics User", roles)
        for role in (
            "EduEdge Administrator",
            "School Administrator",
            "Academic Administrator",
            "Education Manager",
        ):
            self.assertIn(role, roles)
        self.assertEqual(definition.get("track_changes"), 1)

    def test_identity_history_and_delete_safety_are_server_side(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        for token in (
            "def _validate_identity",
            "Existing Instructor Branch Eligibility identity cannot be changed",
            "def on_trash",
            "has started or has no future start date cannot be deleted",
            "with linked academic responsibilities cannot be deleted",
            "def _has_linked_academic_responsibility",
        ):
            self.assertIn(token, source)

    def test_concurrent_overlap_and_primary_checks_are_serialized(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        self.assertIn("def _lock_instructor_scope", source)
        self.assertIn("for update", source.lower())
        self.assertLess(
            source.index("self._lock_instructor_scope()"),
            source.index("self._validate_duplicate()"),
        )
        self.assertLess(
            source.index("self._lock_instructor_scope()"),
            source.index("self._validate_primary()"),
        )

    def test_eligibility_respects_instructor_and_institution_status(self):
        source = CONTROLLER.read_text(encoding="utf-8")

        for token in (
            "Instructor Branch Eligibility can be enabled only for an active Instructor",
            "Instructor Branch Eligibility can be enabled only for an enabled School Branch / Campus",
            "Cross-campus eligibility is allowed within the same Institution; cross-Institution eligibility is not",
            "INSTITUTION_FIELD",
        ):
            self.assertIn(token, source)

    def test_quick_editor_cascades_instructor_to_valid_branch_options(self):
        source = MODAL_RECORDS.read_text(encoding="utf-8")

        for token in (
            '"clear_fields": ["school_branch"]',
            'is_instructor_eligibility = config.get("doctype") == "EduEdge Instructor Branch Assignment"',
            'frappe.db.get_value("Instructor", instructor, INSTITUTION_FIELD)',
            'if is_instructor_eligibility and not instructor:',
            'get_allowed_school_branches(company=company, institution=institution)',
            'filters[INSTITUTION_FIELD] = ["in", institution_names]',
        ):
            self.assertIn(token, source)

    def test_native_form_uses_same_cascading_governance(self):
        source = NATIVE_FORM.read_text(encoding="utf-8")

        for token in (
            'frm.set_query("school_branch"',
            'eduedge.api.education.school_branch_query',
            'eduedge_institution',
            'clearBranch: true',
            'frm.set_df_property("instructor", "read_only"',
            'frm.set_df_property("school_branch", "read_only"',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
