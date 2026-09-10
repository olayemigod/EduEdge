from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestSessionLaunchTimetableContract(unittest.TestCase):
    def test_session_timetable_is_preview_first_bounded_and_native(self):
        api = (APP / "api/session_launch_timetable.py").read_text(encoding="utf-8")
        for token in (
            "MAX_TIMETABLE_ROWS = 250",
            "def preview_session_timetable",
            "def create_session_timetable",
            "academic_operations.before_validate_course_schedule(candidate)",
            "assert_schedule_instructor_assignment(candidate)",
            'candidate.run_method("validate")',
            "validate_course_schedule_conflicts(candidate)",
            '"doctype": "Course Schedule"',
            "doc.insert()",
            '"status": "Existing"',
            '"status": "Blocked"',
            '"status": "Ready"',
        ):
            self.assertIn(token, api)
        self.assertNotIn("ignore_permissions=True", api)
        self.assertNotIn("frappe.db.commit", api)
        self.assertNotIn("frappe.db.set_value", api)

    def test_session_timetable_serialises_shared_resources_and_rechecks_before_write(self):
        api = (APP / "api/session_launch_timetable.py").read_text(encoding="utf-8")
        for token in (
            'RESOURCE_LOCK_ORDER = ("Student Group", "Instructor", "Room")',
            "for update",
            "_lock_planner_resources(parsed)",
            "preview = _preview(launch_doc, parsed)",
            'if preview["summary"]["blocked"]',
            "Duplicate timetable row inside this batch",
            "Conflicts inside this batch",
            "retry will not duplicate it",
        ):
            self.assertIn(token, api)

    def test_session_timetable_does_not_copy_historical_schedule_or_results(self):
        api = (APP / "api/session_launch_timetable.py").read_text(encoding="utf-8")
        for forbidden in (
            "Lesson Plan",
            "Assessment Result",
            "CBT Result",
            "copy_doc",
            "copy_doc(",
            "source_session",
        ):
            self.assertNotIn(forbidden, api)


if __name__ == "__main__":
    unittest.main()
