from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
RUNTIME = APP / "public" / "js" / "eduedge_academic_operations_schedule_action.bundle.js"
LOADER = APP / "eduedge" / "page" / "eduedge_academic_operations" / "eduedge_academic_operations.js"
PERMISSIONS = APP / "permissions_baseline.py"


class TestAcademicOperationsScheduleActionVisibilityContract(unittest.TestCase):
    def test_schedule_action_is_permission_visible_but_calendar_guarded(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn('this.permissions?.can_create_course_schedule', source)
        self.assertIn('!this.calendarReady', source)
        self.assertIn('Academic Calendar required', source)
        self.assertIn('/app/course-schedule/new-course-schedule', source)
        self.assertIn('calendar.blocking_issue', source)

    def test_schedule_action_runtime_loads_before_academic_operations_mount(self):
        source = LOADER.read_text(encoding="utf-8")
        self.assertIn('eduedge_academic_operations_schedule_action.bundle.js', source)
        self.assertLess(
            source.index('eduedge_academic_operations_schedule_action.bundle.js'),
            source.index('window.createEduEdgeAcademicOperationsApp'),
        )

    def test_academic_administrator_has_course_schedule_create_baseline(self):
        source = PERMISSIONS.read_text(encoding="utf-8")
        self.assertIn('"Course Schedule"', source)
        self.assertIn('SCHOOL_MANAGERS = (', source)
        self.assertIn('"Academic Administrator"', source)
        self.assertIn('_grant(matrix, doctype, managers, MANAGE)', source)


if __name__ == "__main__":
    unittest.main()
