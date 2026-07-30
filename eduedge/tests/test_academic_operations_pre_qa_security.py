from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicOperationsPreQASecurity(unittest.TestCase):
	def test_unclassified_native_and_legacy_masters_fail_closed_for_scoped_users(self):
		permissions = (APP / "education" / "academic_permissions.py").read_text(encoding="utf-8")
		self.assertIn('"EduEdge Super Administrator"', permissions)
		self.assertIn("return False", permissions)
		self.assertIn("Fail closed for restricted users", permissions)
		self.assertIn("department_query", permissions)
		self.assertNotIn("or coalesce(`tab{doctype}`.`{fieldname}`, '') = ''", permissions)

	def test_attendance_http_paths_use_secure_overrides_and_specialised_permissions(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"eduedge.api.academic_operations.get_attendance_register": "eduedge.api.academic_operations_safe.get_attendance_register"', hooks)
		self.assertIn('"eduedge.api.academic_operations.save_attendance_register": "eduedge.api.academic_operations_safe.save_attendance_register"', hooks)
		for token in (
			'"Student Admission": "eduedge.education.permissions.has_student_admission_permission"',
			'"Student Applicant": "eduedge.education.permissions.has_student_applicant_permission"',
			'"Student": "eduedge.education.permissions.has_student_permission"',
			'"Program Enrollment": "eduedge.education.permissions.has_program_enrollment_permission"',
			'"Student Group": "eduedge.education.permissions.has_student_group_permission"',
			'"Course Schedule": "eduedge.education.permissions.has_course_schedule_permission"',
			'"Student Attendance": "eduedge.education.permissions.has_student_attendance_permission"',
		):
			self.assertIn(token, hooks)

	def test_secure_attendance_api_enforces_real_permissions(self):
		safe = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")
		for token in (
			'frappe.has_permission("Student Attendance", "read")',
			'frappe.has_permission("Student Attendance", "create")',
			'frappe.has_permission("Student Attendance", "write")',
			'frappe.has_permission("Student Attendance", "submit")',
			'doc.check_permission("write")',
			'doc.check_permission("submit")',
		):
			self.assertIn(token, safe)
		self.assertNotIn("ignore_permissions", safe)
		self.assertIn("More than one Course Schedule exists", safe)

	def test_teacher_scope_resolves_user_employee_instructor_and_owned_records(self):
		scope = (APP / "education" / "instructor_scope.py").read_text(encoding="utf-8")
		permissions = (APP / "education" / "permissions.py").read_text(encoding="utf-8")
		safe = (APP / "api" / "academic_operations_safe.py").read_text(encoding="utf-8")
		self.assertIn('filters={"user_id": resolved_user, "status": "Active"}', scope)
		self.assertIn('filters={"employee": ["in", employees], "status": "Active"}', scope)
		self.assertIn("is_limited_instructor_user", permissions)
		self.assertIn("schedule.student_group = `tabStudent Group`.name", permissions)
		self.assertIn('schedule_filters["instructor"] = ["in", instructor_names]', safe)
		self.assertIn("Attendance can only be recorded against a Course Schedule assigned", safe)

	def test_native_attendance_enforces_schedule_identity_and_serialised_duplicate_check(self):
		operations = (APP / "education" / "academic_operations.py").read_text(encoding="utf-8")
		self.assertIn("Student Attendance Student Group must match the selected Course Schedule", operations)
		self.assertIn("Student Attendance Date must match the selected Course Schedule date", operations)
		self.assertIn("def _validate_attendance_duplicate", operations)
		self.assertIn("for update", operations)
		self.assertIn("Student Attendance already exists for this Student", operations)

	def test_academic_operations_ui_hides_unauthorised_actions(self):
		component = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
		for token in (
			"canCreateStudentGroup", "canCreateCourseSchedule", "canReadRooms",
			"canReadInstructorAssignments", "canManageAttendance", "canSubmitAttendance",
			"frappe.datetime?.get_today?.()", "this.register.course_schedule?.name",
		):
			self.assertIn(token, component)
		self.assertIn(':disabled="student.locked || saving || !canManageAttendance"', component)

	def test_offering_context_rejects_unclassified_native_links(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text(encoding="utf-8")
		self.assertIn("Assign the selected Programme / Class to an Institution", controller)
		self.assertIn("Assign the selected Programme / Class to a Department", controller)
		self.assertIn("Student Batch / Cohort must belong to the same Institution", controller)
		self.assertIn("_validate_department", controller)
		self.assertNotIn("Select an enabled Academic Level", controller)

	def test_student_group_and_schedule_validate_native_hierarchy_server_side(self):
		operations = (APP / "education" / "academic_operations.py").read_text(encoding="utf-8")
		self.assertIn("Programme / Class must belong to the Student Group's Institution", operations)
		self.assertIn("Student Group Programme / Class must match its Programme Offering", operations)
		self.assertIn("Course / Subject {0} is not configured on Programme / Class", operations)
		self.assertIn("Course Schedule Course must match the selected Course-based Student Group", operations)

	def test_offering_list_avoids_per_row_capacity_queries(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text(encoding="utf-8")
		lifecycle = (APP / "services" / "enrollment_lifecycle.py").read_text(encoding="utf-8")
		self.assertIn("get_capacity_consuming_enrollment_counts(names)", api)
		self.assertNotIn("count_capacity_consuming_enrollments(row.name)", api)
		self.assertIn("def get_capacity_consuming_enrollment_counts", lifecycle)


if __name__ == "__main__":
	unittest.main()
