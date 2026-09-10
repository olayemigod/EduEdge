from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestScheduleOverlapHardeningContract(unittest.TestCase):
	def test_course_schedule_uses_complete_interval_overlap_rule(self):
		source = (APP / "education" / "schedule_conflicts.py").read_text(encoding="utf-8")
		for token in (
			"def validate_course_schedule_conflicts",
			"and from_time < %(to_time)s",
			"and to_time > %(from_time)s",
			'(\"student_group\", \"Class Arm / Student Group\")',
			'(\"instructor\", \"Instructor\")',
			'(\"room\", \"Room\")',
			'(\"supervisor\", doc.get(\"instructor\")',
		):
			self.assertIn(token, source)

	def test_course_schedule_doc_event_runs_hardening_server_side(self):
		branching = (APP / "education" / "branching.py").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("from eduedge.education.schedule_conflicts import validate_course_schedule_conflicts", branching)
		self.assertIn("validate_course_schedule_conflicts(doc)", branching)
		self.assertIn('"Course Schedule": {"before_validate": "eduedge.education.branching.before_validate_course_schedule"}', hooks)

	def test_back_to_back_periods_are_not_defined_as_overlap(self):
		source = (APP / "education" / "schedule_conflicts.py").read_text(encoding="utf-8")
		self.assertIn("existing_start < new_end AND existing_end > new_start", source)
		self.assertNotIn("from_time <= %(to_time)s", source)
		self.assertNotIn("to_time >= %(from_time)s", source)


if __name__ == "__main__":
	unittest.main()
