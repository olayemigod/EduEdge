from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicPageReviewFixes(unittest.TestCase):
	def test_attendance_readiness_follows_course_schedule_identity(self):
		api = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_academic_operations"
			/ "EduEdgeAcademicOperations.vue"
		).read_text(encoding="utf-8")
		self.assertIn('"course_schedule": ["in", schedule_names]', api)
		self.assertIn('group_by="course_schedule, status"', api)
		self.assertIn('"course_schedule": schedule["name"]', api)
		self.assertIn(':key="row.course_schedule"', component)
		self.assertIn('this.filters.course_schedule = row.course_schedule', component)
		self.assertIn("attendance_complete_registers", component)
		self.assertIn("attendance_missing_registers", component)

	def test_offering_periods_are_institution_calendar_scoped(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_program_offering"
			/ "eduedge_program_offering.py"
		).read_text(encoding="utf-8")
		self.assertIn("_list_institution_calendar_terms", api)
		self.assertIn('"parenttype": "EduEdge Institution Academic Calendar"', api)
		self.assertIn("_validate_institution_calendar_period", controller)
		self.assertIn("Legacy Offerings are not blocked", controller)
		self.assertIn("Academic Period {0} is not configured", controller)

	def test_closed_disabled_and_full_offerings_do_not_show_false_availability(self):
		api = (APP / "api" / "programme_offerings.py").read_text(encoding="utf-8")
		self.assertIn('status not in {"Disabled", "Closed"}', api)
		self.assertIn('status not in {"Disabled", "Closed", "Full"}', api)
		self.assertLess(api.index('row["operational_status"] = status'), api.index('row["application_open"]'))


if __name__ == "__main__":
	unittest.main()
