from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicOperationsRefactorContract(unittest.TestCase):
    def test_focused_pages_are_installed_and_navigable(self):
        navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
        product_menu = (APP / "public/js/eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
        access = (APP / "access_control.py").read_text(encoding="utf-8")
        for route in ("/app/eduedge-teaching-schedule", "/app/eduedge-attendance"):
            self.assertIn(route, navigation)
            self.assertIn(route, product_menu)
            self.assertIn(route, access)
        for page in ("eduedge_teaching_schedule", "eduedge_attendance"):
            page_dir = APP / "eduedge/page" / page
            self.assertTrue((page_dir / "__init__.py").exists())
            self.assertTrue((page_dir / f"{page}.json").exists())
            self.assertTrue((page_dir / f"{page}.js").exists())

    def test_academic_operations_is_command_centre_not_editor(self):
        source = (APP / "public/js/eduedge_academic_operations/EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
        self.assertIn("Daily academic command centre", source)
        self.assertIn("/app/eduedge-teaching-schedule", source)
        self.assertIn("/app/eduedge-attendance", source)
        self.assertIn("Scheduled attendance coverage", source)
        self.assertIn("Room usage", source)
        self.assertNotIn("saveRegister(submit)", source)
        self.assertNotIn("/app/course-schedule/new-course-schedule", source)

    def test_teaching_schedule_wraps_native_course_schedule(self):
        source = (APP / "public/js/eduedge_teaching_schedule/EduEdgeTeachingSchedule.vue").read_text(encoding="utf-8")
        api = (APP / "api/teaching_schedule.py").read_text(encoding="utf-8")
        for token in ("Day", "Week", "Upcoming", "Rooms", "TeachingScheduleCreateDialog"):
            self.assertIn(token, source)
        self.assertNotIn('/app/course-schedule/new-course-schedule', source)
        self.assertIn('window.open("/app/course-schedule", "_blank", "noopener")', source)
        self.assertIn('params.get("date")', source)
        self.assertIn('params.get("view")', source)
        self.assertIn('frappe.has_permission("Course Schedule", "read")', api)
        self.assertIn('frappe.has_permission("Course Schedule", "create")', api)
        self.assertIn('"Course Schedule"', api)
        self.assertIn("is_limited_instructor_user", api)
        self.assertIn("BRANCH_FIELD", api)
        self.assertIn("doc.insert()", api)

    def test_attendance_requires_exact_schedule_for_take_attendance(self):
        source = (APP / "public/js/eduedge_attendance/EduEdgeAttendance.vue").read_text(encoding="utf-8")
        self.assertIn("Take Attendance", source)
        self.assertIn("Missing Registers", source)
        self.assertIn("course_schedule: this.filters.course_schedule", source)
        self.assertIn('params.get("course_schedule")', source)
        self.assertIn("get_attendance_register", source)
        self.assertIn("save_attendance_register", source)
        self.assertIn("Submitted attendance remains immutable", source)

    def test_refactor_does_not_create_parallel_schedule_or_attendance_doctypes(self):
        doctype_root = APP / "eduedge/doctype"
        self.assertFalse((doctype_root / "eduedge_teaching_schedule").exists())
        self.assertFalse((doctype_root / "eduedge_attendance").exists())


if __name__ == "__main__":
    unittest.main()
