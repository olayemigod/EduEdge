from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultAttendanceDayContract(unittest.TestCase):
	def test_report_attendance_is_scoped_to_published_class_and_collapsed_by_day(self):
		text = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn('"student_group": publication_doc.student_group', text)
		self.assertIn('fields=["student", "date", "status", "course_schedule"]', text)
		self.assertIn("by_student_date", text)
		self.assertIn("if not row.course_schedule", text)
		self.assertIn('if "Present" in statuses:', text)
		self.assertIn('"school_opened": school_opened', text)


if __name__ == "__main__":
	unittest.main()
