from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicFoundationOperationsAlignmentContract(unittest.TestCase):
	def test_calendar_context_fails_closed_for_institution_branches(self):
		service = (APP / "services" / "academic_calendar.py").read_text()
		self.assertIn('"source": "institution_calendar_missing"', service)
		self.assertIn('"source": "education_settings_legacy"', service)
		self.assertIn("if institution:", service)
		self.assertIn("assert_institution_calendar_context", service)
		self.assertIn("Configure an enabled Institution Academic Calendar", service)

	def test_first_enabled_calendar_becomes_current_and_existing_data_is_repaired(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_institution_academic_calendar"
			/ "eduedge_institution_academic_calendar.py"
		).read_text()
		editor = (APP / "api" / "academic_foundation_editor.py").read_text()
		patches = (APP / "patches.txt").read_text()
		patch = (APP / "patches" / "v0_9" / "ensure_current_academic_calendars.py").read_text()
		self.assertIn("The first enabled calendar becomes current automatically", controller)
		self.assertIn("self.is_current = 1", controller)
		self.assertIn("_has_enabled_current_calendar", editor)
		self.assertIn("doc.is_current = int(not _has_enabled_current_calendar", editor)
		self.assertIn("eduedge.patches.v0_9.ensure_current_academic_calendars", patches)
		self.assertIn("_preferred_calendar", patch)
		self.assertIn('"is_current",\n\t\t\t\t1', patch)

	def test_readiness_uses_effective_calendar_without_false_missing_error(self):
		wrapper = (APP / "api" / "academic_foundation_safe.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("_effective_calendar", wrapper)
		self.assertIn('issue.get("code") != "no_current_calendar"', wrapper)
		self.assertIn('"effective_calendar_is_explicit_current"', wrapper)
		self.assertIn(
			'"eduedge.api.academic_foundation.get_academic_foundation": "eduedge.api.academic_foundation_safe.get_academic_foundation"',
			hooks,
		)

	def test_hierarchy_terminology_distinguishes_section_class_and_class_arm(self):
		context = (APP / "services" / "institution_context.py").read_text()
		self.assertIn('resolved["academic_section"] = _term_row("School Section", "School Sections"', context)
		self.assertIn('resolved["academic_level"] = _term_row("Class", "Classes"', context)
		self.assertIn('resolved["programme"] = _term_row("Programme", "Programmes"', context)
		self.assertIn('resolved.setdefault("class_level", dict(resolved["academic_level"]))', context)
		self.assertIn('"student_group"', (APP / "education" / "institution_types.py").read_text())

	def test_programmes_require_section_when_institution_hierarchy_exists(self):
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("has_sections", hierarchy)
		self.assertIn("Select the Programme's Academic Section", hierarchy)
		self.assertIn("Select an enabled Academic Section", hierarchy)
		self.assertIn(
			'"Program": {"before_validate": "eduedge.education.academic_hierarchy.before_validate_program"}',
			hooks,
		)

	def test_programme_offerings_use_only_institution_sessions_and_classes(self):
		api = (APP / "api" / "programme_offerings_safe.py").read_text()
		validation = (APP / "education" / "offering_calendar_validation.py").read_text()
		cascade = (APP / "public" / "js" / "eduedge_programme_offerings" / "level_cascade.js").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("_institution_academic_years", api)
		self.assertIn('filters={"institution": institution, "enabled": 1}', api)
		self.assertIn("assert_institution_calendar_context", validation)
		self.assertIn("if (!section) return levels.filter((row) => !row.academic_section)", cascade)
		self.assertIn("return levels.filter((row) => row.academic_section === section)", cascade)
		self.assertIn("programme_offerings_safe.save_programme_offering", hooks)
		self.assertIn("offering_calendar_validation.validate_programme_offering_calendar", hooks)

	def test_student_group_and_schedule_validate_calendar_context_server_side(self):
		operations = (APP / "education" / "academic_operations.py").read_text()
		self.assertIn("assert_institution_calendar_context", operations)
		self.assertIn("branch=doc.get(BRANCH_FIELD)", operations)
		self.assertIn("academic_year=group_context.academic_year", operations)
		self.assertIn("reference_date=doc.schedule_date", operations)
		self.assertIn("The selected Student Group has no Academic Session", operations)

	def test_operations_fail_closed_and_explain_the_calendar_block(self):
		review = (APP / "api" / "academic_operations_review.py").read_text()
		component = (
			APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue"
		).read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('payload["student_groups"] = []', review)
		self.assertIn("No enabled Institution Academic Calendar covers the selected date", review)
		self.assertIn("student_group_query", review)
		self.assertIn("Institution calendar required", component)
		self.assertIn("calendarReady", component)
		self.assertIn("academic_level_name", component)
		self.assertIn("academic_operations_review.get_operations_context", hooks)
		self.assertIn("academic_operations_review.student_group_query", hooks)

	def test_native_forms_clear_invalid_dependent_context(self):
		group_js = (APP / "public" / "js" / "education" / "student_group.js").read_text()
		schedule_js = (APP / "public" / "js" / "education" / "course_schedule.js").read_text()
		for fieldname in (
			"eduedge_program_offering",
			"program",
			"academic_year",
			"academic_term",
			"batch",
			"course",
			"eduedge_academic_level",
		):
			self.assertIn(fieldname, group_js)
		self.assertIn("clearStudentGroupContext", group_js)
		self.assertIn("reference_date: frm.doc.schedule_date", schedule_js)
		self.assertIn("schedule_date(frm)", schedule_js)

	def test_offering_page_translates_session_and_period_labels(self):
		bundle = (APP / "public" / "js" / "eduedge_programme_offerings.bundle.js").read_text()
		terminology = (
			APP / "public" / "js" / "eduedge_programme_offerings" / "terminology.js"
		).read_text()
		ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
		self.assertIn("applyProgrammeOfferingTerminology", bundle)
		self.assertIn('term(vm, "academic_year"', terminology)
		self.assertIn('term(vm, "academic_term"', terminology)
		self.assertIn("eduedge_programme_offerings/terminology.js", ci)


if __name__ == "__main__":
	unittest.main()
