from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class AcademicContextFoundationContractTest(unittest.TestCase):
	def test_legacy_section_and_level_masters_remain_preserved_for_migration(self):
		section = json.loads((APP / "eduedge" / "doctype" / "eduedge_academic_section" / "eduedge_academic_section.json").read_text())
		level = json.loads((APP / "eduedge" / "doctype" / "eduedge_academic_level" / "eduedge_academic_level.json").read_text())
		self.assertEqual(next(field for field in section["fields"] if field["fieldname"] == "institution")["options"], "EduEdge Institution")
		self.assertEqual(next(field for field in level["fields"] if field["fieldname"] == "institution")["options"], "EduEdge Institution")
		migration = (APP / "patches" / "v0_9" / "migrate_native_academic_hierarchy.py").read_text()
		self.assertIn("SCHOOL_TYPES", migration)
		self.assertIn("_section_department_map", migration)
		self.assertIn("Tertiary Levels are deliberately not auto-created", migration)
		self.assertNotIn("delete_doc", migration)

	def test_native_department_program_student_group_hierarchy_is_authoritative(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		hierarchy = (APP / "education" / "academic_hierarchy.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"Department": [', fields)
		self.assertIn('"Program": [', fields)
		self.assertIn('"Student Group": [', fields)
		self.assertIn('"hidden": 1', fields)
		self.assertIn("before_validate_department", hierarchy)
		self.assertIn("Select the Programme's Department, Faculty, School, or School Section", hierarchy)
		self.assertIn('"Department": {"before_validate": "eduedge.education.academic_hierarchy.before_validate_department"}', hooks)
		self.assertIn('"Program": {"before_validate": "eduedge.education.academic_hierarchy.before_validate_program"}', hooks)

	def test_programme_offering_is_a_protected_native_delivery_identity(self):
		offering = json.loads((APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.json").read_text())
		fields = {field["fieldname"]: field for field in offering["fields"]}
		for fieldname in (
			"institution", "program", "department", "academic_year", "academic_term", "student_batch",
			"offering_title", "offering_code", "study_mode", "delivery_mode", "start_date", "end_date",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["institution"]["fetch_from"], "school_branch.institution")
		self.assertEqual(fields["department"]["fetch_from"], "program.department")
		self.assertTrue(fields["academic_section"]["hidden"])
		self.assertTrue(fields["academic_level"]["hidden"])
		controller = (APP / "eduedge" / "doctype" / "eduedge_program_offering" / "eduedge_program_offering.py").read_text()
		self.assertIn("IDENTITY_FIELDS", controller)
		self.assertIn("_has_operational_references", controller)
		self.assertIn("_validate_department", controller)
		self.assertIn("assert_institution_calendar_context", controller)
		self.assertIn("count_capacity_consuming_enrollments", controller)

	def test_applicant_enrollment_and_group_link_exact_offering(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		validation = (APP / "education" / "academic_validation.py").read_text()
		operations = (APP / "education" / "academic_operations.py").read_text()
		group_query = (APP / "api" / "academic_group_context.py").read_text()
		for doctype in ("Student Applicant", "Program Enrollment", "Student Group"):
			self.assertIn(f'"{doctype}"', fields)
		self.assertIn('OFFERING_FIELD = "eduedge_program_offering"', fields)
		self.assertIn("resolve_exact_offering", validation)
		self.assertIn("More than one Programme Offering matches", validation)
		self.assertIn("matching this Programme Offering and Branch", operations)
		self.assertIn("enrollment.docstatus = 1", group_query)

	def test_primary_secondary_native_labels_distinguish_section_class_and_arm(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		self.assertGreaterEqual(fields.count('"department": ("School Section", "School Sections")'), 2)
		self.assertGreaterEqual(fields.count('"programme": ("Class", "Classes")'), 2)
		self.assertGreaterEqual(fields.count('"student_group": ("Class Arm", "Class Arms")'), 2)
		self.assertIn('"department": ("Faculty / School", "Faculties / Schools")', fields)
		self.assertIn('"student_group": ("Level / Lecture Group", "Levels / Lecture Groups")', fields)

	def test_fee_context_is_derived_without_mutating_accounting_truth(self):
		validation = (APP / "education" / "academic_validation.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("clear_context(doc)", validation)
		self.assertIn("academic_fee_context.before_validate_fee_schedule", hooks)
		self.assertNotIn("on_submit", hooks)

	def test_migration_backfills_only_unambiguous_context_and_permissions_fail_closed(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		permissions = (APP / "education" / "academic_permissions.py").read_text()
		patches = (APP / "patches.txt").read_text()
		self.assertIn("backfill_unambiguous_academic_master_context", fields)
		self.assertGreaterEqual(fields.count("having institution_count = 1"), 4)
		self.assertIn("Fail closed for restricted users", permissions)
		self.assertIn("department_query", permissions)
		self.assertIn("eduedge.patches.v0_9.migrate_native_academic_hierarchy", patches)

	def test_institution_calendar_is_active_and_safe(self):
		controller = (APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.py").read_text()
		resolver = (APP / "services" / "academic_calendar.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("for update", controller)
		self.assertIn("overlaps with", controller)
		self.assertIn("self.is_current = 1", controller)
		self.assertIn('"source": "institution_calendar" if calendar else "institution_calendar_missing"', resolver)
		self.assertIn('"academic_term": period.academic_term if period else None', resolver)
		self.assertIn("assert_institution_calendar_context", resolver)
		self.assertIn("integration_qa_hardening.get_operations_context", hooks)

	def test_academic_lookup_api_is_allowlisted_and_permission_aware(self):
		api = (APP / "api" / "academic_context.py").read_text()
		self.assertIn("ALLOWED_SCOPED_QUERY_DOCTYPES", api)
		self.assertIn('"Department"', api)
		self.assertIn("This academic lookup is not permitted", api)
		self.assertIn('doc.check_permission("read")', api)
		self.assertIn("offering.department", api)

	def test_edgesuite_foundation_and_offering_editor_use_native_hierarchy(self):
		foundation = (APP / "public" / "js" / "eduedge_academic_foundation" / "EduEdgeAcademicFoundation.vue").read_text()
		offering = (APP / "public" / "js" / "eduedge_programme_offerings" / "EduEdgeProgrammeOfferings.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_academic_foundation" / "eduedge_academic_foundation.js").read_text()
		self.assertIn("Frappe Education's native", foundation)
		self.assertIn("save_department", foundation)
		self.assertIn("eduedge.api.programmes.save_programme", foundation)
		self.assertIn("departmentSingular", offering)
		self.assertIn("draftProgramChanged", offering)
		self.assertNotIn("academicLevel", offering)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_academic_foundation.bundle.js"))


if __name__ == "__main__":
	unittest.main()
