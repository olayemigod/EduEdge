from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestTeachingScheduleOwnershipContract(unittest.TestCase):
    def test_limited_instructor_schedule_access_requires_unique_identity_and_exact_assignment(self):
        source = (APP / "education" / "instructor_scope.py").read_text(encoding="utf-8")
        for token in (
            "def instructor_owns_schedule",
            "resolve_exact_instructor_for_user(resolved_user)",
            'if value("instructor") != exact_instructor',
            '"Course Schedule"',
            "assert_schedule_instructor_assignment(context)",
            "except (frappe.PermissionError, frappe.ValidationError)",
        ):
            self.assertIn(token, source)

    def test_teaching_schedule_context_requires_exact_instructor_identity(self):
        source = (APP / "api" / "teaching_schedule.py").read_text(encoding="utf-8")
        context = source.split("def get_teaching_schedule_context", 1)[1]
        self.assertIn("resolve_exact_instructor_for_user(required=True)", context)
        self.assertIn('filters["instructor"] = exact_instructor', context)
        self.assertNotIn("get_user_instructor_names", context)


    def test_existing_course_schedule_and_attendance_record_permissions_consume_schedule_ownership(self):
        source = (APP / "education" / "permissions.py").read_text(encoding="utf-8")
        self.assertIn("def has_course_schedule_permission", source)
        self.assertIn("return instructor_owns_schedule(doc, resolved_user)", source)
        self.assertIn("def has_student_attendance_permission", source)
        self.assertIn("return instructor_owns_schedule(schedule, resolved_user)", source)

    def test_attendance_safe_api_checks_course_schedule_record_permission(self):
        source = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")
        self.assertIn('doc = frappe.get_doc("Course Schedule", course_schedule)', source)
        self.assertIn('doc.check_permission("read")', source)
        self.assertIn("_resolve_register_schedule", source)


if __name__ == "__main__":
    unittest.main()
