from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicOperationsScheduleActionContract(unittest.TestCase):
    def test_bundle_installs_schedule_action_runtime(self):
        source = (APP / "public" / "js" / "eduedge_academic_operations.bundle.js").read_text(encoding="utf-8")
        self.assertIn('import { installAcademicOperationsScheduleAction } from "./eduedge_academic_operations/schedule_action";', source)
        self.assertIn("installAcademicOperationsScheduleAction(EduEdgeAcademicOperations);", source)

    def test_create_action_uses_server_permission_with_frappe_client_fallback(self):
        source = (APP / "public" / "js" / "eduedge_academic_operations" / "schedule_action.js").read_text(encoding="utf-8")
        self.assertIn('this.permissions?.can_create_course_schedule || clientCanCreateCourseSchedule()', source)
        self.assertIn('frappe.model.can_create("Course Schedule")', source)
        self.assertNotIn('return Boolean(this.calendarReady && this.permissions.can_create_course_schedule)', source)

    def test_schedule_route_remains_calendar_guarded(self):
        source = (APP / "public" / "js" / "eduedge_academic_operations" / "schedule_action.js").read_text(encoding="utf-8")
        self.assertIn('const COURSE_SCHEDULE_CREATE_ROUTE = "/app/course-schedule/new-course-schedule";', source)
        self.assertIn('String(route || "") === COURSE_SCHEDULE_CREATE_ROUTE && !this.calendarReady', source)
        self.assertIn('title: __("Academic Calendar required")', source)


if __name__ == "__main__":
    unittest.main()
