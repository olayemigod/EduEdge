from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationOperationsAlignmentContract(unittest.TestCase):
	def test_calendar_context_fails_closed_for_institution_branches(self):
		service = (APP / "services" / "academic_calendar.py").read_text()
		self.assertIn('"institution_calendar_missing"', service)
		self.assertIn('"education_settings_legacy"', service)
		self.assertIn("if institution:", service)
		self.assertIn("assert_institution_calendar_context", service)
		self.assertIn("Configure an enabled Institution Academic Calendar", service)

	def test_first_enabled_calendar_becomes_current_and_existing_data_is_repaired(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.py").read_text()
		editor = (APP / "api" / "academic_foundation_editor.py").read_text()
		patches = (APP / "patches.txt").read_text()
		patch = (APP / "patches" / "v0_9" / "ensure_current_academic_calendars.py").read_text()
		self.assertIn("The first enabled calendar becomes current automatically", controller)
		self.assertIn("self.is_current = 1", controller)
		self.assertIn("_has_enabled_current_calendar", editor)
		self.assertIn("doc.is_current = int(not _has_enabled_current_calendar", editor)
		self.assertIn("eduedge.patches.v0_9.ensure_current_academic_calendars", patches)
		self.assertIn("_preferred_calendar", patch)

	def test_readiness_uses_effective_calendar_without_false_missing_error(self):
		api = (APP / "api" / "academic_foundation_safe.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("def _effective_calendar", api)
		self.assertIn("covering =", api)
		self.assertIn('"current_calendar": effective.get("name") if effective else None', api)
		self.assertIn('"eduedge.api.academic_foundation.get_academic_foundation": "eduedge.api.integration_qa_hardening.get_academic_foundation"', hooks)

	def test_native_hierarchy_terminology_distinguishes_section_class_and_arm(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		self.assertGreaterEqual(fields.count('"department": ("School Section", "School Sections")'), 2)
		self.assertGreaterEqual(fields.count('"programme": ("Class", "Classes")'), 2)
		self.assertGreaterEqual(fields.count('"student_group": ("Class Arm", "Class Arms")'), 2)
		self.assertIn('"department": ("Faculty / School", "Faculties / Schools")', fields)
		self.assertIn('"student_group": ("Level / Lecture Group", "Levels / Lecture Groups")', fields)

	def test_programmes_require_native_department_owned_by_institution(self):
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("Select the Programme's Department, Faculty, School, or School Section", hierarchy)
		self.assertIn("Department / School Section must belong to the selected Institution", hierarchy)
		self.assertIn("before_validate_department", hierarchy)
		self.assertIn('"Department": {"before_validate": "eduedge.education.academic_hierarchy.before_validate_department"}', hooks)

	def test_programme_offerings_use_only_institution_sessions_and_native_programmes(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text()
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text()
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("_institution_academic_years", api)
		self.assertIn("_institution_calendar_terms", api)
		self.assertIn("assert_institution_calendar_context", controller)
		self.assertIn("_enforce_sessional_scope", controller)
		self.assertIn('self.department = frappe.db.get_value("Program", self.program, "department")', controller)
		self.assertIn("draftProgramChanged", component)
		self.assertIn("Not part of Programme Offering identity", component)
		self.assertNotIn("academicLevel", component)
		self.assertIn("programme_offerings_safe.save_programme_offering", hooks)

	def test_student_group_and_schedule_validate_native_calendar_and_programme_context(self):
		operations = (APP / "education" / "academic_operations.py").read_text()
		self.assertIn("assert_institution_calendar_context", operations)
		self.assertIn("_validate_group_program_context", operations)
		self.assertIn("_validate_group_course_context", operations)
		self.assertIn("Course / Subject {0} is not configured on Programme / Class", operations)
		self.assertIn("academic_year=group_context.academic_year", operations)
		self.assertIn("reference_date=doc.schedule_date", operations)

	def test_operations_fail_closed_and_explain_calendar_block(self):
		review = (APP / "api" / "academic_operations_review.py").read_text()
		component = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('payload["student_groups"] = []', review)
		self.assertIn("No enabled Institution Academic Calendar covers the selected date", review)
		self.assertIn("student_group_query", review)
		self.assertIn("calendarReady", component)
		self.assertIn("hierarchy_label", component)
		self.assertNotIn("academic_level_name", component)
		self.assertIn("integration_qa_hardening.get_operations_context", hooks)

	def test_native_forms_clear_invalid_dependent_context(self):
		group_js = (APP / "public" / "js" / "education" / "student_group.js").read_text()
		schedule_js = (APP / "public" / "js" / "education" / "course_schedule.js").read_text()
		for fieldname in ("eduedge_program_offering", "program", "academic_year", "academic_term", "batch", "course"):
			self.assertIn(fieldname, group_js)
		self.assertIn("clearStudentGroupContext", group_js)
		self.assertIn("academic_operations_review.course_query", group_js)
		self.assertIn("applyStudentGroupContext", schedule_js)
		self.assertIn("schedule_date(frm)", schedule_js)

	def test_offering_page_uses_direct_institution_terminology_but_no_term_identity(self):
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text()
		bundle = (APP / "public" / "js" / "eduedge_programme_offerings.bundle.js").read_text()
		self.assertIn('term("academic_year"', component)
		self.assertIn('term("department"', component)
		self.assertNotIn('term("academic_term"', component)
		self.assertIn("Terms / Semesters", component)
		self.assertIn("Not part of Programme Offering identity", component)
		self.assertIn("createEduEdgeProgrammeOfferingsApp", bundle)
		self.assertNotIn("applyProgrammeOfferingLevelCascade", bundle)


if __name__ == "__main__":
	unittest.main()
