from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestQuestionBuilderAssignmentCapabilityFiltersContract(unittest.TestCase):
    def _source(self):
        return (APP / "api" / "question_builder.py").read_text(encoding="utf-8")

    def test_builder_filtering_is_staged_and_limited_to_teacher_authoring(self):
        source = self._source()
        for token in (
            "def _assignment_author_filter_enabled",
            "is_teacher_user() and assignment_capability_enforcement_enabled()",
            "def _author_capability_rows",
            '"can_author_cbt"',
            "get_user_capability_assignment_rows",
        ):
            self.assertIn(token, source)

    def test_school_builder_branches_and_offerings_are_capability_scoped_when_enabled(self):
        source = self._source()
        for token in (
            "def _builder_allowed_branches",
            'question.get("ownership_scope") == PLATFORM_BANK',
            'row.get("school_branch") for row in _author_capability_rows()',
            "capability_rows = _author_capability_rows(branch=branch)",
            'assigned = {row.get("program_offering") for row in capability_rows',
            "offerings = [row for row in offerings if row.name in assigned]",
        ):
            self.assertIn(token, source)

    def test_class_arm_options_follow_exact_assignment_scope(self):
        source = self._source()
        for token in (
            "class_wide = any(row.get(\"assignment_scope\") == CLASS_SCOPE for row in relevant)",
            "if not class_wide:",
            'row.get("assignment_scope") == CLASS_ARM_SCOPE',
            'row.get("student_group")',
            "groups = [row for row in groups if row.name in allowed_groups]",
        ):
            self.assertIn(token, source)

    def test_course_search_intersects_program_curriculum_with_author_capability(self):
        source = self._source()
        for token in (
            "course_names = set(_program_courses(offering.program))",
            "capability_courses = {",
            "_author_capability_rows(",
            "program_offering=program_offering",
            "student_group=student_group",
            "course_names &= capability_courses",
        ):
            self.assertIn(token, source)

    def test_existing_school_question_write_and_version_actions_reflect_exact_author_context(self):
        source = self._source()
        for token in (
            "def _question_author_context_allowed",
            "user_has_instructor_assignment_capability(",
            '"can_author_cbt"',
            "if can_write and not _question_author_context_allowed(question):",
            "can_write = False",
            '"can_create_version": bool(',
            "and _question_author_context_allowed(question)",
        ):
            self.assertIn(token, source)

    def test_public_exam_bank_does_not_use_school_assignment_author_filter(self):
        source = self._source()
        self.assertGreaterEqual(source.count('question.get("ownership_scope") == PLATFORM_BANK'), 2)
        self.assertIn("get_public_exam_capability_summary", source)
        self.assertIn("_question_scope_options", source)

    def test_default_off_retains_existing_assigned_course_and_offering_behavior(self):
        source = self._source()
        for token in (
            "else:",
            '"instructor": ["in", _current_instructors()]',
            "assigned_courses(branch=offering.school_branch, program_offering=program_offering, student_group=student_group)",
            "assigned_courses(branch=branch)",
        ):
            self.assertIn(token, source)

    def test_backend_question_validation_remains_authoritative(self):
        source = self._source()
        self.assertIn("doc.insert()", source)
        self.assertIn("doc.save()", source)
        lifecycle = (APP / "cbt" / "master_lifecycle.py").read_text(encoding="utf-8")
        self.assertIn("validate_question_authoring_capability(doc)", lifecycle)


if __name__ == "__main__":
    unittest.main()
