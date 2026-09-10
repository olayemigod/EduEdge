from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstructorAssignmentCapabilityEnforcementFoundation(unittest.TestCase):
    def _source(self):
        return (APP / "education" / "instructor_assignment_capabilities.py").read_text(encoding="utf-8")

    def test_rollout_switch_is_explicit_and_defaults_off(self):
        metadata = json.loads(
            (
                APP
                / "eduedge"
                / "doctype"
                / "eduedge_settings"
                / "eduedge_settings.json"
            ).read_text(encoding="utf-8")
        )
        fields = {row["fieldname"]: row for row in metadata["fields"]}
        setting = fields["enforce_instructor_assignment_capabilities"]
        self.assertEqual(setting.get("default"), "0")
        self.assertIn("Migration-safe rollout switch", setting.get("description", ""))
        self.assertIn("identity mappings", setting.get("description", ""))

    def test_missing_setting_or_schema_preserves_existing_behavior_during_migration(self):
        source = self._source()
        for token in (
            "def assignment_capability_enforcement_enabled",
            'meta.has_field("enforce_instructor_assignment_capabilities")',
            'frappe.db.get_single_value("EduEdge Settings", "enforce_instructor_assignment_capabilities")',
            "except Exception:",
            "return False",
            "Missing settings/schema intentionally fail open",
        ):
            self.assertIn(token, source)

    def test_enforcement_applies_only_to_limited_instructor_users(self):
        source = self._source()
        for token in (
            "def require_instructor_assignment_capability",
            "is_limited_instructor_user(resolved_user)",
            "if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user)",
            "return True",
            "Managers and privileged users keep their established role/permission paths.",
        ):
            self.assertIn(token, source)

    def test_enforcement_uses_exact_effective_assignment_state_and_fails_closed(self):
        source = self._source()
        for token in (
            "get_instructor_assignment_capability_state(",
            "school_branch=school_branch",
            "program_offering=program_offering",
            "course=course",
            "student_group=student_group",
            "if state.get(capability)",
            'state.get("identity_status") == "ambiguous"',
            "does not grant {0} for this Branch, Class, Class Arm and Subject context",
        ):
            self.assertIn(token, source)

    def test_capability_option_rows_are_exact_active_assignments_not_branch_access(self):
        source = self._source()
        for token in (
            "def get_user_capability_assignment_rows",
            "len(instructors) != 1",
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "capability: 1",
            '"program_offering"',
            '"assignment_scope"',
            '"student_group"',
            '"course"',
            "_effective(row, resolved_date)",
        ):
            self.assertIn(token, source)
        self.assertNotIn("EduEdge Instructor Branch Assignment", source)

    def test_enforcement_foundation_does_not_take_over_question_review_or_final_approval(self):
        source = self._source()
        for forbidden in (
            "can_subject_review",
            "can_final_approve",
            "EduEdge Question Responsibility Assignment",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
