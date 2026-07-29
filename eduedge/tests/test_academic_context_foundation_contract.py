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
		section_controller = (APP / "eduedge" / "doctype" / "eduedge_academic_section" / "eduedge_academic_section.py").read_text()
		level_controller = (APP / "eduedge" / "doctype" / "eduedge_academic_level" / "eduedge_academic_level.py").read_text()
		self.assertIn("for update", section_controller)
		self.assertIn("for update", level_controller)
		self.assertIn("progression cannot contain a cycle", level_controller)

	def test_programme_offering_is_a_protected_delivery_identity(self):
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
		self.assertIn("IDENTITY_FIELDS", controller)
		self.assertIn("_has_operational_references", controller)
		self.assertIn("for update", controller)
		self.assertIn("count_capacity_consuming_enrollments", controller)
		self.assertIn("coalesce(academic_term, '')", controller)

	def test_applicant_enrollment_and_group_link_exact_offering(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		validation = (APP / "education" / "academic_validation.py").read_text()
		branching = (APP / "education" / "branching.py").read_text()
		operations = (APP / "education" / "academic_operations.py").read_text()
		group_query = (APP / "api" / "academic_group_context.py").read_text()
		for doctype in ("Student Applicant", "Program Enrollment", "Student Group"):
			self.assertIn(f'"{doctype}"', fields)
		self.assertIn('OFFERING_FIELD = "eduedge_program_offering"', fields)
		self.assertIn("resolve_exact_offering", validation)
		self.assertIn("More than one Programme Offering matches", validation)
		self.assertIn("primary/home responsibility context", branching)
		self.assertNotIn("Program Enrollment Branch must match the selected Student Branch", branching)
		self.assertIn("matching this Programme Offering and Branch", operations)
		self.assertIn("enrollment.docstatus = 1", group_query)
		self.assertIn("filters.get(OFFERING_FIELD)", group_query)

	def test_cross_branch_student_lookup_is_controlled_and_institution_bound(self):
		api = (APP / "api" / "education.py").read_text()
		enrollment_js = (APP / "public" / "js" / "education" / "program_enrollment.js").read_text()
		self.assertIn("CROSS_BRANCH_ENROLLMENT_ROLES", api)
		self.assertIn("home_branch.institution = %(institution)s", api)
		self.assertIn("allow_cross_branch: 1", enrollment_js)
		self.assertIn("student_batch_name", enrollment_js)
		self.assertNotIn("frm.set_value('eduedge_school_branch', branch)", enrollment_js)

	def test_primary_secondary_program_is_class_and_enrollment_is_class_enrollment(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		self.assertGreaterEqual(fields.count('"programme": ("Class", "Classes")'), 2)
		self.assertGreaterEqual(fields.count('"program_enrollment": ("Class Enrollment", "Class Enrollments")'), 2)
		self.assertIn('"program_enrollment": ("Programme Enrollment", "Programme Enrollments")', fields)
		self.assertIn('"program_enrollment": ("Trainee Enrollment", "Trainee Enrollments")', fields)

	def test_fee_context_is_derived_without_mutating_accounting_truth(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		validation = (APP / "education" / "academic_validation.py").read_text()
		wrapper = (APP / "education" / "academic_fee_context.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		for doctype in ("Fee Structure", "Fee Schedule", "Fees", "Student Leave Application", "Student Log"):
			self.assertIn(f'"{doctype}"', fields)
		self.assertIn("clear_context(doc)", validation)
		self.assertIn("selected_offering", wrapper)
		self.assertIn("academic_fee_context.before_validate_fee_schedule", hooks)
		self.assertNotIn("on_submit", hooks)

	def test_migration_backfills_only_unambiguous_master_context_and_visibility_fails_closed(self):
		fields = (APP / "education" / "academic_fields.py").read_text()
		permissions = (APP / "education" / "academic_permissions.py").read_text()
		self.assertIn("backfill_unambiguous_academic_master_context", fields)
		self.assertGreaterEqual(fields.count("having institution_count = 1"), 4)
		self.assertIn("LEGACY_OPTIONAL_DOCTYPES", permissions)
		self.assertIn("Fail closed for restricted users", permissions)
		self.assertNotIn("coalesce(`tab{doctype}`.`{fieldname}`, '') = ''", permissions)

	def test_institution_calendar_is_active_and_safe(self):
		calendar = json.loads((APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.json").read_text())
		self.assertEqual(next(field for field in calendar["fields"] if field["fieldname"] == "periods")["options"], "EduEdge Academic Calendar Period")
		controller = (APP / "eduedge" / "doctype" / "eduedge_institution_academic_calendar" / "eduedge_institution_academic_calendar.py").read_text()
		resolver = (APP / "services" / "academic_calendar.py").read_text()
		safe_api = (APP / "api" / "academic_operations_safe.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("for update", controller)
		self.assertIn("overlaps with", controller)
		self.assertIn("before_save", controller)
		self.assertIn("academic_term = period.academic_term if period else None", resolver)
		self.assertIn("not row.academic_term or row.academic_term == academic_term", safe_api)
		self.assertIn("academic_operations_safe.get_operations_context", hooks)

	def test_enrollment_lifecycle_is_append_only_serialized_and_releases_capacity(self):
		status_log = json.loads((APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.json").read_text())
		self.assertEqual(next(field for field in status_log["fields"] if field["fieldname"] == "target_program_offering")["options"], "EduEdge Program Offering")
		controller = (APP / "eduedge" / "doctype" / "eduedge_enrollment_status_log" / "eduedge_enrollment_status_log.py").read_text()
		lifecycle = (APP / "services" / "enrollment_lifecycle.py").read_text()
		capacity = (APP / "education" / "enrollment_capacity.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("append-only", controller)
		self.assertIn("for update", controller)
		self.assertIn("configured next Academic Level", controller)
		self.assertNotIn("frappe.db.set_value", controller)
		self.assertIn('CAPACITY_CONSUMING_STATUSES = {"Active", "Suspended"}', lifecycle)
		self.assertIn("count_capacity_consuming_enrollments", capacity)
		self.assertIn("before_submit_program_enrollment", hooks)

	def test_academic_lookup_api_is_allowlisted_and_permission_aware(self):
		api = (APP / "api" / "academic_context.py").read_text()
		self.assertIn("ALLOWED_SCOPED_QUERY_DOCTYPES", api)
		self.assertIn("This academic lookup is not permitted", api)
		self.assertIn('doc.check_permission("read")', api)
		self.assertIn("coalesce(offering.academic_term, '')", api)

	def test_offering_ui_updates_do_not_clear_selected_offering(self):
		applicant = (APP / "public" / "js" / "education" / "student_applicant.js").read_text()
		group = (APP / "public" / "js" / "education" / "student_group.js").read_text()
		for script in (applicant, group):
			self.assertIn("__eduedge_applying_offering", script)
			self.assertIn("selectedOffering", script)

	def test_edgesuite_academic_foundation_and_offering_editor_are_wired(self):
		vue = (APP / "public" / "js" / "eduedge_academic_foundation" / "EduEdgeAcademicFoundation.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_academic_foundation" / "eduedge_academic_foundation.js").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		contract = (APP / "api" / "academic_resource_contract.py").read_text()
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("save_academic_section", vue)
		self.assertIn("save_academic_level", vue)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_academic_foundation.bundle.js"))
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertIn("/app/eduedge-academic-foundation", navigation)
		for fieldname in ("study_mode", "delivery_mode", "academic_level", "student_batch"):
			self.assertIn(f'"fieldname": "{fieldname}"', contract)


if __name__ == "__main__":
	unittest.main()
