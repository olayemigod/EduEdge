from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicPageReviewFixes(unittest.TestCase):
	def test_attendance_readiness_follows_course_schedule_identity(self):
		api = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")
		command = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
		attendance = (APP / "public" / "js" / "eduedge_attendance" / "EduEdgeAttendance.vue").read_text(encoding="utf-8")
		self.assertIn('"course_schedule": ["in", schedule_names]', api)
		self.assertIn('group_by="course_schedule, status"', api)
		self.assertIn('"course_schedule": schedule["name"]', api)
		self.assertIn(':key="row.course_schedule"', command)
		self.assertIn('course_schedule: row.course_schedule', command)
		self.assertIn('this.filters.course_schedule = row.course_schedule', attendance)
		self.assertIn("course_schedule: this.filters.course_schedule", attendance)
		self.assertIn("attendance_complete_registers", command)
		self.assertIn("attendance_missing_registers", command)

	def test_offering_terms_are_institution_calendar_scoped(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text(encoding="utf-8")
		calendar = (APP / "services" / "academic_calendar.py").read_text(encoding="utf-8")
		self.assertIn("_institution_calendar_terms", api)
		self.assertIn('CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"', api)
		self.assertIn('"parenttype": CALENDAR_DOCTYPE', api)
		self.assertIn("assert_institution_calendar_context", controller)
		self.assertIn("Academic Period {0} is not configured", calendar)
		self.assertIn("academic_term=academic_term or None", api)

	def test_closed_disabled_and_full_offerings_do_not_show_false_availability(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		self.assertIn('status not in {"Disabled", "Closed"}', api)
		self.assertIn('status not in {"Disabled", "Closed", "Full"}', api)
		self.assertLess(api.index('row["operational_status"] = status'), api.index('row["application_open"]'))

	def test_native_department_is_derived_from_programme(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text(encoding="utf-8")
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text(encoding="utf-8")
		self.assertIn('self.department = frappe.db.get_value("Program", self.program, "department")', controller)
		self.assertIn("draftDepartmentName", component)
		self.assertIn("draftProgramChanged", component)
		self.assertNotIn("academic_level", component)


if __name__ == "__main__":
	unittest.main()
