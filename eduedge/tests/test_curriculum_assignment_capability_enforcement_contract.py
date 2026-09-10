from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCurriculumAssignmentCapabilityEnforcementContract(unittest.TestCase):
    def _source(self):
        return (APP / "education" / "curriculum_permissions.py").read_text(encoding="utf-8")

    def test_course_visibility_uses_view_content_capability_only_when_enforcement_is_on(self):
        source = self._source()
        for token in (
            "def _teacher_visible_courses",
            "if not assignment_capability_enforcement_enabled()",
            "set(assigned_courses(user))",
            '_teacher_capability_rows(user, "can_view_subject_content")',
            "def course_query",
            "def has_course_permission",
        ):
            self.assertIn(token, source)

    def test_topic_read_query_uses_exact_capability_assignment_rows_when_enforced(self):
        source = self._source()
        for token in (
            "def _topic_assignment_conditions",
            "if assignment_capability_enforcement_enabled():",
            '_teacher_capability_rows(user, "can_view_subject_content")',
            "def _topic_conditions_for_rows",
            "row.get(\"program_offering\")",
            "row.get(\"assignment_scope\") == CLASS_SCOPE",
            "row.get(\"assignment_scope\") == CLASS_ARM_SCOPE",
            "TOPIC_SCOPE_CLASS_ARM",
        ):
            self.assertIn(token, source)

    def test_manage_topic_capability_controls_teacher_create_and_write_not_delete(self):
        source = self._source()
        for token in (
            "def _topic_capability_match",
            'capability = "can_manage_subject_topics" if writable else "can_view_subject_content"',
            "writable = permission_type in {\"write\", \"create\"}",
            'permission_type in {"delete", "submit", "cancel", "amend", "share", "import"}',
            "return False",
        ):
            self.assertIn(token, source)

    def test_institution_wide_topics_remain_read_only_for_limited_instructors(self):
        source = self._source()
        for token in (
            "if scope == TOPIC_SCOPE_INSTITUTION:",
            "return bool(matching) and not writable",
            "do not edit institution-wide Topic truth",
        ):
            self.assertIn(token, source)

    def test_class_scope_capability_covers_class_arm_topics_but_class_arm_scope_is_exact(self):
        source = self._source()
        for token in (
            "if row.get(\"assignment_scope\") == CLASS_SCOPE:",
            "return True",
            "if row.get(\"assignment_scope\") == CLASS_ARM_SCOPE and row.get(\"student_group\") == doc.get(TOPIC_GROUP_FIELD):",
        ):
            self.assertIn(token, source)

    def test_default_off_preserves_existing_assignment_based_curriculum_permissions(self):
        source = self._source()
        for token in (
            "active_assignment_rows(user)",
            "assigned_courses(user)",
            "_topic_assignment_match",
            "if not assignment_capability_enforcement_enabled()",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
