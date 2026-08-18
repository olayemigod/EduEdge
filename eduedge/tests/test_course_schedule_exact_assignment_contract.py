from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestCourseScheduleExactAssignmentContract(unittest.TestCase):
    def test_backend_requires_exact_subject_assignment_context(self):
        source = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
        for token in (
            "def assert_schedule_instructor_assignment",
            '"program_offering": program_offering',
            '"course": course',
            '"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]',
            '"enabled": 1',
            "scope == CLASS_SCOPE",
            "scope == CLASS_ARM_SCOPE and row.student_group == student_group",
            "row.valid_from",
            "row.valid_to",
            "Class responsibilities without a",
            "Subject never authorise a Subject lesson",
        ):
            self.assertIn(token, source)

    def test_backend_keeps_branch_eligibility_as_separate_migration_safe_layer(self):
        branching = (APP / "education" / "branching.py").read_text(encoding="utf-8")
        operations = (APP / "education" / "academic_operations.py").read_text(encoding="utf-8")
        exact = (APP / "education" / "instructor_assignments.py").read_text(encoding="utf-8")
        self.assertIn("_before_validate_course_schedule(doc, method)", branching)
        self.assertIn("assert_schedule_instructor_assignment(doc)", branching)
        self.assertIn("assert_instructor_assignment(", operations)
        self.assertIn('if not frappe.db.exists(ASSIGNMENT_DOCTYPE, {"school_branch": branch}):', exact)

    def test_instructor_link_options_are_exact_and_effective_date_aware(self):
        source = (APP / "api" / "teaching_assignment_options.py").read_text(encoding="utf-8")
        for token in (
            "def course_schedule_instructor_query",
            "assignment.school_branch = %(branch)s",
            "assignment.program_offering = %(program_offering)s",
            "assignment.course = %(course)s",
            "assignment.assignment_type in %(assignment_types)s",
            "assignment.valid_from is null",
            "assignment.valid_to is null",
            "assignment.assignment_scope = %(class_scope)s",
            "assignment.student_group = %(student_group)s",
            "instructor.status = 'Active'",
            "assert_branch_access(branch)",
            "legacy_branch_instructor_query",
        ):
            self.assertIn(token, source)

    def test_course_schedule_form_cascades_subject_context_into_instructor_options(self):
        source = (APP / "public" / "js" / "education" / "course_schedule.js").read_text(encoding="utf-8")
        self.assertIn("eduedge.api.teaching_assignment_options.course_schedule_instructor_query", source)
        for token in (
            "student_group: frm.doc.student_group",
            "course: frm.doc.course",
            "reference_date: frm.doc.schedule_date",
            "async course(frm)",
            'await frm.set_value("instructor", null)',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
