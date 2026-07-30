from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicProgressionModelContract(unittest.TestCase):
	def test_program_is_reusable_master_with_explicit_progression(self):
		progression = (APP / "education" / "academic_progression.py").read_text()
		program_js = (APP / "public" / "js" / "education" / "program.js").read_text()
		programmes = (APP / "api" / "programmes_progression.py").read_text()
		self.assertIn('PROGRAM_PROMOTION = "Program Promotion"', progression)
		self.assertIn('LEVEL_PROGRESSION = "Level Progression"', progression)
		self.assertIn('PROGRAM_NEXT_FIELD = "eduedge_next_program"', progression)
		self.assertIn("Program / Class progression cannot contain a cycle", progression)
		self.assertIn("Next Program / Class must belong to the same Institution", progression)
		self.assertIn("Academic Level on Program Course is only valid", progression)
		self.assertIn("Manage Academic Levels", program_js)
		self.assertIn("eduedge_progression_mode", programmes)
		self.assertIn("eduedge_allow_repetition", programmes)

	def test_academic_level_is_program_owned_not_an_operational_group(self):
		level_json = json.loads((APP / "eduedge" / "doctype" / "eduedge_academic_level" / "eduedge_academic_level.json").read_text())
		fields = {field["fieldname"]: field for field in level_json["fields"]}
		controller = (APP / "eduedge" / "doctype" / "eduedge_academic_level" / "eduedge_academic_level.py").read_text()
		self.assertEqual(fields["program"]["options"], "Program")
		self.assertTrue(fields["academic_section"]["hidden"])
		self.assertIn("is_terminal", fields)
		self.assertIn("Academic Level requires a Programme", controller)
		self.assertIn("Academic Level Programme must belong to the selected Institution", controller)
		self.assertIn("Academic Level progression cannot contain a cycle", controller)
		self.assertIn("LEVEL_PROGRESSION", controller)

	def test_primary_secondary_and_tertiary_offering_identity_differ(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text()
		api = (APP / "api" / "programme_offerings_progression.py").read_text()
		component = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text()
		self.assertIn("Level-progression Programme Offering", controller)
		self.assertIn("Primary and Secondary Class Offerings are Academic-Session-wide", controller)
		self.assertIn("coalesce(academic_level, '')", controller)
		self.assertIn("academic_level", api)
		self.assertIn("draftRequiresLevel", component)
		self.assertIn("draftUsesClassPromotion", component)
		self.assertIn("full Academic Session", component)

	def test_program_course_curriculum_is_level_and_period_aware(self):
		progression = (APP / "education" / "academic_progression.py").read_text()
		operations = (APP / "education" / "academic_operations.py").read_text()
		lookup = (APP / "api" / "academic_operations_review.py").read_text()
		for fieldname in ("eduedge_academic_level", "eduedge_period_number", "eduedge_course_type", "eduedge_credit_units"):
			self.assertIn(fieldname, progression)
		self.assertIn("get_programme_course_rows", operations)
		self.assertIn("_curriculum_period_number", operations)
		self.assertIn("get_programme_course_rows", lookup)
		self.assertIn("filters.get(ACADEMIC_LEVEL_FIELD)", lookup)

	def test_progression_creates_target_enrollment_without_mutating_source(self):
		service = (APP / "api" / "progression.py").read_text()
		wrapper = (APP / "api" / "progression_workflow.py").read_text()
		fields = (APP / "education" / "enrollment_progression_fields.py").read_text()
		status = (APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.py").read_text()
		self.assertIn('target = frappe.new_doc("Program Enrollment")', service)
		self.assertIn("target.insert()", service)
		self.assertNotIn("source.save", service)
		self.assertNotIn("source.submit", service)
		self.assertIn("PROGRESSION_SOURCE_FIELD", wrapper)
		self.assertIn("existing progression draft", wrapper)
		self.assertIn("Target enrollment does not belong to this progression plan", wrapper)
		self.assertIn("eduedge_progression_source_enrollment", fields)
		self.assertIn("Target Program Enrollment must be submitted", status)
		self.assertIn("Enrollment Status Logs are append-only", status)

	def test_promotion_repeat_transfer_and_completion_rules_are_explicit(self):
		service = (APP / "api" / "progression.py").read_text()
		status = (APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.py").read_text()
		self.assertIn('DRAFT_OUTCOMES = {"Promote", "Repeat", "Transfer"}', service)
		self.assertIn("Target Offering does not match the configured next Class or Academic Level", service)
		self.assertIn("Repeat target must retain the same Programme / Class and Academic Level", service)
		self.assertIn("Automatic transfer is limited to Branches within the same Institution", service)
		self.assertIn("Held for Review", status)
		self.assertIn("Graduated", status)
		self.assertIn("configured next Class or Academic Level", status)

	def test_student_group_rollover_is_period_specific_and_does_not_copy_membership(self):
		service = (APP / "api" / "progression.py").read_text()
		wrapper = (APP / "api" / "progression_workflow.py").read_text()
		group_js = (APP / "public" / "js" / "education" / "student_group.js").read_text()
		self.assertIn("def rollover_student_group", service)
		self.assertIn("Students and instructors will not be copied", group_js)
		self.assertIn("Student and instructor rows are deliberately not copied", service)
		self.assertNotIn('target.set("students"', service)
		self.assertNotIn('target.set("instructors"', service)
		self.assertIn("suggested_group_name", wrapper)
		self.assertIn("Rollover Group", group_js)

	def test_legacy_records_are_preserved_until_context_is_deliberately_changed(self):
		offering = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text()
		operations = (APP / "education" / "academic_operations.py").read_text()
		self.assertIn("Existing legacy Offerings remain editable for non-identity fields", offering)
		self.assertIn("context_changed", offering)
		self.assertIn("strict_context", operations)
		self.assertIn("_context_changed", operations)
		self.assertIn("Legacy Student Group context detected", (APP / "public" / "js" / "education" / "student_group.js").read_text())

	def test_assessment_fees_and_report_cards_carry_formal_level_without_rewriting_accounting(self):
		assessment = (APP / "education" / "assessment_operations.py").read_text()
		validation = (APP / "education" / "academic_validation.py").read_text()
		report_api = (APP / "api" / "report_cards_profiled.py").read_text()
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("_assign_level", assessment)
		self.assertIn('doc.academic_level = group.get(ACADEMIC_LEVEL_FIELD)', assessment)
		self.assertIn("ACADEMIC_LEVEL_FIELD", validation)
		self.assertIn("academic_level_name", report_api)
		self.assertIn("Academic Level", template)
		self.assertNotIn("on_submit", validation)

	def test_canonical_routes_use_progression_aware_services(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("academic_foundation_progression.get_academic_foundation", hooks)
		self.assertIn("programmes_progression.get_programmes_page", hooks)
		self.assertIn("programmes_progression.save_programme", hooks)
		self.assertIn("programme_offerings_progression.get_programme_offerings_page", hooks)
		self.assertIn("programme_offerings_progression.save_programme_offering", hooks)


if __name__ == "__main__":
	unittest.main()
