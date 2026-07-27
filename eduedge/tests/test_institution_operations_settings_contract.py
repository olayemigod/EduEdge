from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestInstitutionOperationsSettingsContract(unittest.TestCase):
	def test_company_and_institution_schema_keep_the_settings_small(self):
		company_settings = APP / "eduedge/doctype/eduedge_company_operations_settings/eduedge_company_operations_settings.json"
		institution = APP / "eduedge/doctype/eduedge_institution/eduedge_institution.json"
		self.assertTrue(company_settings.exists())
		company_payload = json.loads(company_settings.read_text(encoding="utf-8"))
		institution_payload = json.loads(institution.read_text(encoding="utf-8"))

		company_fields = {row["fieldname"] for row in company_payload["fields"]}
		institution_fields = {row["fieldname"] for row in institution_payload["fields"]}
		for fieldname in (
			"question_approval_mode",
			"allow_bulk_question_approval",
			"max_bulk_question_approval",
			"require_separate_question_approver",
			"allow_academic_admin_override",
		):
			self.assertIn(fieldname, company_fields)
			self.assertIn(fieldname, institution_fields)
		self.assertIn("use_company_question_governance_defaults", institution_fields)
		self.assertNotIn("school_branch", company_fields)
		self.assertNotIn("school_branch", institution_fields)

	def test_resolver_has_type_defaults_and_explicit_precedence(self):
		policy = (APP / "education/operations_policy.py").read_text(encoding="utf-8")
		for expected in (
			'"PRIMARY":',
			'"SECONDARY":',
			'"TERTIARY":',
			'"TRAINING_CENTRE":',
			'"question_approval_mode": "Simple"',
			'"question_approval_mode": "Standard"',
			'"Company Default"',
			'"Institution Preference"',
			'"Recommended Default"',
			"resolve_company_question_governance",
			"resolve_question_governance",
			"MAX_BULK_QUESTIONS = 100",
		):
			self.assertIn(expected, policy)
		self.assertNotIn("school_branch", policy)

	def test_api_is_permission_aware_and_does_not_bypass_frappe(self):
		api = (APP / "api/institution_operations_settings.py").read_text(encoding="utf-8")
		for expected in (
			"get_settings_context",
			"save_settings",
			"frappe.has_permission",
			'doc.check_permission("read")',
			'doc.check_permission("write")',
			"require_eduedge_access",
			"get_list(",
			"MAX_BULK_QUESTIONS",
			'COMPANY_SCOPE = "Company Default"',
			'INSTITUTION_SCOPE = "Institution Preference"',
			'_("Assessment and Results")',
			'_("Attendance and Timetable")',
		):
			self.assertIn(expected, api)
		for forbidden in (
			"ignore_permissions=True",
			"ignore_permissions = True",
			"frappe.db.sql(",
			".submit()",
			".cancel()",
		):
			self.assertNotIn(forbidden, api)

	def test_edgesuite_page_and_bundle_are_registered(self):
		page_root = APP / "eduedge/page/eduedge_institution_operations_settings"
		for filename in (
			"__init__.py",
			"eduedge_institution_operations_settings.json",
			"eduedge_institution_operations_settings.js",
		):
			self.assertTrue((page_root / filename).exists(), filename)
		page = json.loads((page_root / "eduedge_institution_operations_settings.json").read_text(encoding="utf-8"))
		self.assertEqual(page["roles"], [])
		self.assertEqual(page["name"], "eduedge-institution-operations-settings")

		component = (
			APP
			/ "public/js/eduedge_institution_operations_settings/EduEdgeInstitutionOperationsSettings.vue"
		).read_text(encoding="utf-8")
		bundle = (APP / "public/js/eduedge_institution_operations_settings.bundle.js").read_text(encoding="utf-8")
		loader = (page_root / "eduedge_institution_operations_settings.js").read_text(encoding="utf-8")
		for expected in (
			"<EdgeAppShell",
			"<EdgePageLayout",
			"<EdgeFilterBar",
			"Institution Preference",
			"Use Company Question Governance Defaults",
			"Planned module settings",
			"saveSettings",
		):
			self.assertIn(expected, component)
		self.assertIn("createEduEdgeInstitutionOperationsSettingsApp", bundle)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_institution_operations_settings.bundle.js"))

	def test_navigation_and_access_manifest_expose_the_page(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		for source in (navigation, access):
			self.assertIn("/app/eduedge-institution-operations-settings", source)
		self.assertIn('"institution": "EduEdge Institution"', access)
		self.assertIn('"company_operations_settings": "EduEdge Company Operations Settings"', access)
		self.assertIn('("institution", "read")', access)
		self.assertIn('("company_operations_settings", "read")', access)


if __name__ == "__main__":
	unittest.main()
