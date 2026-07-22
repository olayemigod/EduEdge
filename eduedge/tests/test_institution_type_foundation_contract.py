from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class InstitutionTypeFoundationContractTest(unittest.TestCase):
	def test_seeded_registry_and_terms_exist(self):
		registry = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_institution_type" / "eduedge_institution_type.json").read_text()
		)
		term = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_institution_type_term" / "eduedge_institution_type_term.json").read_text()
		)
		self.assertEqual(registry["autoname"], "field:institution_type_code")
		self.assertEqual(term["istable"], 1)
		self.assertTrue(all(not permission.get("write") for permission in registry["permissions"]))

		seed = (APP / "education" / "institution_types.py").read_text()
		defaults = (APP / "education" / "institution_type_defaults.py").read_text()
		for code in ("PRIMARY", "SECONDARY", "TERTIARY", "TRAINING_CENTRE"):
			self.assertIn(f'"{code}"', seed)
		for key in (
			"academic_year", "academic_term", "programme", "programme_offering",
			"course", "student_batch", "student_group", "class_level",
			"class_session", "instructor", "room",
		):
			self.assertIn(f'"{key}"', seed)
		for key in (
			"program_enrollment", "student", "assessment", "assessment_group",
			"assessment_plan", "assessment_result",
		):
			self.assertIn(f'"{key}"', defaults)

	def test_company_institution_branch_hierarchy_is_explicit(self):
		seed = (APP / "education" / "institution_types.py").read_text()
		institution = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_institution" / "eduedge_institution.json").read_text()
		)
		branch = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_school_branch" / "eduedge_school_branch.json").read_text()
		)
		institution_fields = {field["fieldname"]: field for field in institution["fields"]}
		branch_fields = {field["fieldname"]: field for field in branch["fields"]}
		self.assertIn('DEFAULT_INSTITUTION_TYPE = "SECONDARY"', seed)
		self.assertEqual(institution_fields["company"]["options"], "Company")
		self.assertEqual(institution_fields["institution_type"]["options"], "EduEdge Institution Type")
		self.assertEqual(branch_fields["institution"]["options"], "EduEdge Institution")
		self.assertEqual(branch_fields["institution"]["reqd"], 1)
		self.assertEqual(branch_fields["institution_type"]["read_only"], 1)
		self.assertEqual(branch_fields["institution_type"]["fetch_from"], "institution.institution_type")

	def test_branch_quick_editor_exposes_company_filtered_institution(self):
		resource_api = (APP / "api" / "resource_center_safe.py").read_text()
		resource_modal = (APP / "public" / "js" / "eduedge_ui" / "resource_modal.js").read_text()
		self.assertIn('"fieldname": "institution"', resource_api)
		self.assertIn('"options_doctype": "EduEdge Institution"', resource_api)
		self.assertIn('_institution_options(company=parsed_values.get("company")', resource_api)
		self.assertIn('company_field["refresh_fields"]', resource_api)
		self.assertIn("field?.clear_fields", resource_modal)

	def test_school_period_and_visible_terminology_defaults(self):
		defaults = (APP / "education" / "institution_type_defaults.py").read_text()
		install = (APP / "install.py").read_text()
		home = (APP / "public" / "js" / "eduedge_home" / "EduEdgeHome.vue").read_text()
		resource_api = (APP / "api" / "resource_center_safe.py").read_text()
		self.assertIn('"class_session": ("Period", "Periods")', defaults)
		self.assertGreaterEqual(defaults.count('"class_session": ("Period", "Periods")'), 2)
		self.assertIn('"assessment": ("Examination", "Examinations")', defaults)
		self.assertGreaterEqual(defaults.count('"assessment": ("Examination", "Examinations")'), 2)
		self.assertIn('"assessment_plan": ("Examination Plan", "Examination Plans")', defaults)
		self.assertIn('"program_enrollment": ("Class Enrollment", "Class Enrollments")', defaults)
		self.assertIn('"student": ("Pupil", "Pupils")', defaults)
		self.assertIn('"student": ("Trainee", "Trainees")', defaults)
		self.assertGreaterEqual(install.count("apply_institution_type_defaults()"), 2)
		self.assertIn("term('class_session'", home)
		self.assertIn("_apply_terminology", resource_api)

	def test_migration_groups_without_guessing_from_branch_names(self):
		seed = (APP / "education" / "institution_types.py").read_text()
		self.assertIn("backfill_institutions_and_branches", seed)
		self.assertIn("groups.setdefault((row.company, code)", seed)
		self.assertIn("generated_from_legacy", seed)
		self.assertIn("requires_review", seed)
		self.assertNotIn("branch_name", seed)

	def test_institution_first_runtime_context_is_available_to_edgeui(self):
		service = (APP / "services" / "institution_context.py").read_text()
		boot = (APP / "boot.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		bundle = (APP / "public" / "js" / "eduedge_terminology.bundle.js").read_text()
		shell_identity = (APP / "public" / "js" / "eduedge_shell_identity.bundle.js").read_text()
		branch_api = (APP / "api" / "branch_context.py").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertLess(service.index("institution_type = normalize_institution_type_code"), service.index("company_type ="))
		self.assertIn('"institution": (institution_row or {}).get("name")', service)
		self.assertIn('bootinfo["eduedge_institution_context"]', boot)
		self.assertIn('"eduedge_terminology.bundle.js"', hooks)
		self.assertIn("frappe.eduedge.term", bundle)
		self.assertIn("applyInstitutionContext", bundle)
		self.assertIn("syncInstitutionContext", bundle)
		self.assertIn("installBranchSwitchContextBridge", bundle)
		self.assertIn("eduedge:institution-context-changed", bundle)
		self.assertIn('selected["institution_context"]', branch_api)
		self.assertIn('payload["institution_context"]', branch_api)
		self.assertIn("Institution", shell_identity)
		self.assertIn("Branch", shell_identity)
		self.assertIn("eduedge-active-context", shell_identity)
		self.assertIn("eduedge-page-context-fallback", shell_identity)
		self.assertIn('document.querySelectorAll(".edge-topbar, .edge-app-shell__topbar")', shell_identity)
		self.assertIn('term("assessment", { plural: true', navigation)
		self.assertIn("applyVisibleTerminology", bundle)
		self.assertIn("terminologyFamilyPairs", bundle)
		self.assertIn('"Examination Operations"', bundle)
		self.assertIn('"Evaluation Operations"', bundle)
		self.assertIn('getEduEdgeTerm("student"', bundle)
		self.assertIn('["Students", "Pupils", "Trainees"]', bundle)
		self.assertIn('["Student", "Pupil", "Trainee"]', bundle)
		self.assertIn('getEduEdgeTerm("student_group"', bundle)
		self.assertIn('getEduEdgeTerm("student_batch"', bundle)
		self.assertIn("pairs.sort", bundle)

	def test_edgesuite_institution_structure_owns_hierarchy_configuration(self):
		institution_api = (APP / "api" / "institution_types.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_institution_structure" / "EduEdgeInstitutionStructure.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_institution_structure" / "eduedge_institution_structure.js").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn("save_company_institution_type", institution_api)
		self.assertIn("save_institution", institution_api)
		self.assertIn("assign_branch_institution", institution_api)
		self.assertNotIn("save_branch_institution_type", institution_api)
		self.assertIn("edgeui.bundle.js", loader)
		self.assertLess(loader.index("edgeui.bundle.js"), loader.index("eduedge_institution_structure.bundle.js"))
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("Company → Institution → Branch", vue)
		self.assertIn("Terminology preview", vue)
		self.assertIn("Assign Branches to Institutions", vue)
		self.assertIn("/app/eduedge-institution-structure", navigation)
		self.assertNotIn("import coreedge", vue.lower())

	def test_install_is_idempotent_entrypoint(self):
		install = (APP / "install.py").read_text()
		self.assertGreaterEqual(install.count("ensure_institution_type_foundation()"), 2)
		self.assertIn("after_install", install)
		self.assertIn("after_migrate", install)


if __name__ == "__main__":
	unittest.main()
