from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCBTAssignmentCapabilityEnforcementContract(unittest.TestCase):
    def _source(self):
        return (APP / "cbt" / "assignment_capabilities.py").read_text(encoding="utf-8")

    def test_school_question_authoring_requires_exact_assignment_capability_when_enabled(self):
        source = self._source()
        for token in (
            "def validate_question_authoring_capability",
            "assignment_capability_enforcement_enabled()",
            "is_limited_instructor_user(user)",
            'doc.get("ownership_scope") != SCHOOL_BANK',
            'doc.get("school_branch")',
            'doc.get("program_offering")',
            'doc.get("student_group")',
            'doc.get("course")',
            'require_instructor_assignment_capability(\n        "can_author_cbt"',
            "verify the exact Instructor Assignment",
        ):
            self.assertIn(token, source)

    def test_public_exam_bank_keeps_separate_public_exam_governance(self):
        source = self._source()
        self.assertIn('if doc.get("ownership_scope") != SCHOOL_BANK:', source)
        self.assertIn("Public examination-bank questions", source)
        self.assertNotIn("can_author_public_exams", source)

    def test_subject_review_and_final_approval_do_not_require_author_capability(self):
        source = self._source()
        for token in (
            'REVIEW_ONLY_ACTIONS = {"request_changes", "recommend", "approve", "retire"}',
            "if governance_action in REVIEW_ONLY_ACTIONS:",
            "return",
            "Review and approval actions remain governed by Question Responsibility",
        ):
            self.assertIn(token, source)
        self.assertNotIn("can_subject_review", source)
        self.assertNotIn("can_final_approve", source)

    def test_author_governance_actions_and_normal_draft_saves_remain_subject_to_author_capability(self):
        source = self._source()
        for token in (
            'AUTHOR_ACTIONS = {"submit_for_review", "return_to_draft"}',
            'getattr(frappe.flags, "eduedge_question_governance_action"',
            "governance_action and governance_action not in AUTHOR_ACTIONS",
            "Question governance action is not available through Instructor authoring capability",
        ):
            self.assertIn(token, source)

    def test_existing_cbt_master_validate_hook_runs_author_capability_without_replacing_governance(self):
        lifecycle = (APP / "cbt" / "master_lifecycle.py").read_text(encoding="utf-8")
        for token in (
            "validate_question_governance_transition",
            "validate_question_authoring_capability",
            "validate_question_governance_transition(doc)",
            "validate_question_authoring_capability(doc)",
        ):
            self.assertIn(token, lifecycle)

    def test_rollout_is_backward_compatible_until_setting_is_enabled(self):
        source = self._source()
        self.assertIn("if not assignment_capability_enforcement_enabled()", source)
        settings = (
            APP
            / "eduedge"
            / "doctype"
            / "eduedge_settings"
            / "eduedge_settings.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"default":"0","fieldname":"enforce_instructor_assignment_capabilities"', settings)


if __name__ == "__main__":
    unittest.main()
