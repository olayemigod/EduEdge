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
		for code in ("PRIMARY", "SECONDARY", "TERTIARY", "TRAINING_CENTRE"):
			self.assertIn(f'"{code}"', seed)
		for key in (
			"academic_year", "academic_term", "programme", "programme_offering",
			"course", "student_batch", "student_group", "class_level",
			"class_session", "instructor", "room",
		):
			self.assertIn(f'"{key}"', seed)

	def test_company_fallback_and_required_branch_type(self):
		seed = (APP / "education" / "institution_types.py").read_text()
		branch = json.loads(
			(APP / "eduedge" / "doctype" / "eduedge_school_branch" / "eduedge_school_branch.json").read_text()
		)
		fields = {field["fieldname"]: field for field in branch["fields"]}
		self.assertIn('DEFAULT_INSTITUTION_TYPE = "SECONDARY"', seed)
		self.assertIn('COMPANY_INSTITUTION_TYPE_FIELD = "eduedge_institution_type"', seed)
		self.assertEqual(fields["institution_type"]["options"], "EduEdge Institution Type")
		self.assertEqual(fields["institution_type"]["reqd"], 1)

	def test_branch_first_runtime_context_is_available_to_edgeui(self):
		service = (APP / "services" / "institution_context.py").read_text()
		boot = (APP / "boot.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		bundle = (APP / "public" / "js" / "eduedge_terminology.bundle.js").read_text()
		self.assertLess(service.index("branch_type"), service.index("company_type"))
		self.assertIn('bootinfo["eduedge_institution_context"]', boot)
		self.assertIn('"eduedge_terminology.bundle.js"', hooks)
		self.assertIn("frappe.eduedge.term", bundle)
		self.assertIn("applyInstitutionContext", bundle)

	def test_edgesuite_institution_structure_owns_configuration_ui(self):
		institution_api = (APP / "api" / "institution_types.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_institution_structure" / "EduEdgeInstitutionStructure.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_institution_structure" / "eduedge_institution_structure.js").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		self.assertIn("save_company_institution_type", institution_api)
		self.assertIn("save_branch_institution_type", institution_api)
		self.assertIn("edgeui.bundle.js", loader)
		self.assertLess(loader.index("edgeui.bundle.js"), loader.index("eduedge_institution_structure.bundle.js"))
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("Terminology preview", vue)
		self.assertIn("School Branch institution types", vue)
		self.assertIn("/app/eduedge-institution-structure", navigation)
		self.assertNotIn("import coreedge", vue.lower())

	def test_install_is_idempotent_entrypoint(self):
		install = (APP / "install.py").read_text()
		self.assertGreaterEqual(install.count("ensure_institution_type_foundation()"), 2)
		self.assertIn("after_install", install)
		self.assertIn("after_migrate", install)


if __name__ == "__main__":
	unittest.main()
