from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestLessonPlanSmartInstructorOptionsContract(unittest.TestCase):
    def test_instructor_options_start_from_exact_assignment_scope_not_all_instructors(self):
        source = (APP / "api" / "lesson_plans.py").read_text(encoding="utf-8")
        start = source.index("def _instructor_options")
        end = source.index("def _list_plans", start)
        block = source[start:end]
        self.assertIn('"EduEdge Instructor Assignment"', block)
        self.assertIn('"school_branch": branch', block)
        self.assertIn('"program_offering": offering', block)
        self.assertIn('"course": course', block)
        self.assertIn('"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)]', block)
        self.assertIn('"enabled": 1', block)
        self.assertIn("reference_date = getdate(lesson_date)", block)
        self.assertIn("exact_arm + class_wide", block)
        self.assertNotIn('frappe.get_all("Instructor"', block)
        self.assertNotIn('limit_page_length=0', block)

    def test_only_instructors_referenced_by_eligible_assignments_are_loaded(self):
        source = (APP / "api" / "lesson_plans.py").read_text(encoding="utf-8")
        start = source.index("def _instructor_options")
        end = source.index("def _list_plans", start)
        block = source[start:end]
        self.assertIn('filters={"name": ["in", instructor_names], "status": "Active"}', block)
        self.assertIn("first_assignment", block)
        self.assertIn('"assignment": assignment.name', block)
        self.assertIn('"assignment_title": assignment.assignment_title', block)

    def test_limited_instructor_options_resolve_exact_identity_and_capability(self):
        source = (APP / "api" / "lesson_plans.py").read_text(encoding="utf-8")
        start = source.index("def _instructor_options")
        end = source.index("def _list_plans", start)
        block = source[start:end]
        self.assertIn("resolve_exact_instructor_for_user(required=False)", block)
        self.assertIn("assignment_capability_enforcement_enabled()", block)
        self.assertIn("can_view_subject_content", block)


if __name__ == "__main__":
    unittest.main()
