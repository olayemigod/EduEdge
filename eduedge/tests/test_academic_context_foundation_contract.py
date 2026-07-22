from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class AcademicContextFoundationContractTest(unittest.TestCase):
	def test_academic_section_and_level_masters_are_institution_owned(self):
		section = json.loads((APP / "eduedge" / "doctype" / "eduedge_academic_section" / "eduedge_academic_section.json").read_text())
		level = json.loads((APP / "eduedge" / "doctype" / "eduedge_academic_level" / "eduedge_academic_level.json").read_text())
		section_fields = {field["fieldname"]: field for field in section["fields"]}
		level_fields = {field["fieldname"]: field for field in level["fields"]}
		self.assertEqual(section_fields["institution"]["options"], "EduEdge Institution")
		self.assertEqual(level_fields["institution"]["options"], "EduEdge Institution")
		self.assertEqual(level_fields["academic_section"]["options"], "EduEdge Academic Section")
		self.assertEqual(section["autoname"], "hash")
		self.assertEqual(level["autoname"], "hash")
		self.assertNotIn("unique", section_fields["section_code"])
		self.assertNotIn("unique", level_fields["level_code"])

	def test_programme_offering_is_a_real_delivery_identity(self):
		offering = json.loads((APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.json").read_text())
		fields = {field["fieldname"]: field for field in offering["fields"]}
		for fieldname in (
			"institution", "academic_section", "academic_level", "student_batch",
			"offering_title", "offering_code", "study_mode", "delivery_mode", "start_date", "end_date",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["institution"]["fetch_from"], "school_branch.institution")
		self.assertEqual(fields["academic_section"]["fetch_from"], "program.eduedge_academic_section")
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text()
		self.assertIn("_validate_institution_context", controller)
		self.assertIn("study_mode", controller)
		self.assertIn("delivery_mode", controller)

	def test_applicant_enrollment_and_group_link_exact_offering(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		validation = (APP / "education" / "academic_validation.py").read_text()
		branching = (APP / "education" / "branching.py").read_text()
		for doctype in ("Student Applicant", "Program Enrollment", "Student Group"):
			self.assertIn(f'"{doctype}"', fields)
		self.assertIn('OFFERING_FIELD = "eduedge_program_offering"', fields)
		self.assertIn("resolve_exact_offering", validation)
		self.assertIn("More than one Programme Offering matches", validation)
		self.assertIn("The exact Programme Offering owns the enrollment Branch", branching)
		self.assertNotIn("Program Enrollment Branch must match the selected Student Branch", branching)

	def test_primary_secondary_program_is_class_and_enrollment_is_class_enrollment(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		self.assertGreaterEqual(fields.count('"programme": ("Class", "Classes")'), 2)
		self.assertGreaterEqual(fields.count('"program_enrollment": ("Class Enrollment", "Class Enrollments")'), 2)
		self.assertIn('"program_enrollment": ("Programme Enrollment", "Programme Enrollments")', fields)
		self.assertIn('"program_enrollment": ("Trainee Enrollment", "Trainee Enrollments")', fields)

	def test_fee_leave_and_log_context_fields_are_upgrade_safe(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		for doctype in ("Fee Structure", "Fee Schedule", "Fees", "Student Leave Application", "Student Log"):
			self.assertIn(f'"{doctype}"', fields)
		self.assertIn("create_custom_fields(available, update=True)", fields)
		install = (APP / "install.py").read_text()
		self.assertGreaterEqual(install.count("ensure_academic_context_foundation()"), 2)

	def test_institution_calendar_and_append_only_enrollment_log_exist(self):
		calendar = json.loads((APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.json").read_text())
		status_log = json.loads((APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.json").read_text())
		self.assertEqual(next(field for field in calendar["fields"] if field["fieldname"] == "periods")["options"], "EduEdge Academic Calendar Period")
		self.assertEqual(next(field for field in status_log["fields"] if field["fieldname"] == "target_program_offering")["options"], "EduEdge Program Offering")
		controller = (APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.py").read_text()
		self.assertIn("append-only", controller)
		self.assertIn("ALLOWED_TRANSITIONS", controller)

	def test_edgesuite_academic_foundation_and_offering_editor_are_wired(self):
		vue = (APP / "public" / "js" / "eduedge_academic_foundation" / "EduEdgeAcademicFoundation.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_academic_foundation" / "eduedge_academic_foundation.js").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		contract = (APP / "api" / "academic_resource_contract.py").read_text()
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("save_academic_section", vue)
		self.assertIn("save_academic_level", vue)
		self.assertLess(loader.index("edgeui.bundle.js"), loader.index("eduedge_academic_foundation.bundle.js"))
		self.assertIn("/app/eduedge-academic-foundation", navigation)
		for fieldname in ("study_mode", "delivery_mode", "academic_level", "student_batch"):
			self.assertIn(f'"fieldname": "{fieldname}"', contract)


if __name__ == "__main__":
	unittest.main()
