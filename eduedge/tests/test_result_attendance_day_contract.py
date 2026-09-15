from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultAttendanceDayContract(unittest.TestCase):
	def test_daily_class_attendance_is_authoritative_with_controlled_course_fallback(self):
		text = (APP / "education" / "result_attendance.py").read_text()
		self.assertIn('"student_group": student_group', text)
		self.assertIn('fields=["student", "date", "status", "course_schedule"]', text)
		self.assertIn("daily_rows = [row for row in rows if not row.course_schedule]", text)
		self.assertIn("source_rows = daily_rows if daily_rows else rows", text)
		self.assertIn('"Daily Student Group"', text)
		self.assertIn('"Course Schedule Fallback"', text)
		self.assertIn("course_only_dates", text)
		self.assertIn("Attendance switches between daily class attendance and course-level attendance", text)

	def test_official_attendance_fails_closed_on_incomplete_or_conflicting_days(self):
		text = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn("def assert_official_attendance_complete", text)
		self.assertIn("missing_student_days", text)
		self.assertIn("conflicting_student_days", text)
		self.assertIn("duplicate_daily_student_days", text)
		self.assertIn("invalid_status_days", text)
		self.assertIn("Complete the attendance register before publishing official results.", text)
		self.assertIn('"coverage_complete": coverage_complete', text)
		self.assertIn('"school_opened": school_opened', text)
		readiness = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn("get_official_attendance_blockers", readiness)
		self.assertIn("profile_blockers.extend(get_official_attendance_blockers(attendance_meta))", readiness)


if __name__ == "__main__":
	unittest.main()
