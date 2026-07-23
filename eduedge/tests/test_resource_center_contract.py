from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResourceCenterContract(unittest.TestCase):
	def test_sidebar_routes_use_dedicated_eduedge_pages(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		for route in (
			"/app/eduedge-admissions",
			"/app/eduedge-applicants",
			"/app/eduedge-students",
			"/app/eduedge-programs",
			"/app/eduedge-program-offerings",
			"/app/eduedge-school-branches",
			"/app/eduedge-settings-center",
		):
			self.assertIn(route, navigation)
		for native_route in (
			'route: "/app/student-admission"',
			'route: "/app/student-applicant"',
			'route: "/app/student"',
			'route: "/app/eduedge-program-offering"',
		):
			self.assertNotIn(native_route, navigation)

	def test_resource_api_is_allowlisted_branch_safe_permission_aware_and_platform_guarded(self):
		api = (APP / "api/resource_center.py").read_text(encoding="utf-8")
		safety = (APP / "api/resource_center_safe.py").read_text(encoding="utf-8")
		for expected in (
			"RESOURCE_CONFIG",
			'"school_branches"',
			'"admissions"',
			'"applicants"',
			'"students"',
			'"programs"',
			'"program_offerings"',
			"get_resource_page",
			"get_resource_editor",
			"save_resource_record",
			"delete_resource_record",
			"get_allowed_school_branches",
			"frappe.get_list(",
			'doc.check_permission("write")',
			'doc.check_permission("delete")',
		):
			self.assertIn(expected, api)
		for expected in (
			"_smart_filters",
			"base._link_options",
			"not allowed_branches",
			"_empty_page",
			"nowdate()",
			"RESOURCE_FEATURES",
			"require_eduedge_access",
			' action="delete_resource_record"',
		):
			self.assertIn(expected.strip(), safety)
		for forbidden in (
			"ignore_permissions=True",
			"ignore_permissions = True",
			"frappe.db.sql(",
			'frappe.new_doc("Sales Invoice")',
			'frappe.new_doc("Payment Entry")',
			'frappe.new_doc("Journal Entry")',
		):
			self.assertNotIn(forbidden, api + safety)

	def test_resource_pages_use_native_frappe_dialog_crud(self):
		component = (APP / "public/js/eduedge_resource_center/EduEdgeResourceCenter.vue").read_text(encoding="utf-8")
		client = (APP / "public/js/eduedge_ui/resource_modal.js").read_text(encoding="utf-8")
		native = (APP / "public/js/eduedge_ui/native_frappe_dialog.js").read_text(encoding="utf-8")
		loader = (APP / "public/js/eduedge_resource_page_loader.bundle.js").read_text(encoding="utf-8")
		for expected in (
			"<EdgeAppShell",
			"openNativeResourceDialog",
			"new frappe.ui.Dialog",
			"get_resource_page",
			"get_resource_editor",
			"save_resource_record",
			"delete_resource_record",
			"search_resource_options",
			"frappe.confirm",
		):
			self.assertIn(expected, component + client + native)
		self.assertIn("registerEduEdgeResourcePage", loader)
		self.assertIn("eduedge_resource_center.bundle.js", loader)
		self.assertNotIn("<EdgeFormDialog", component)
		self.assertNotIn("<EdgeModal", component)

	def test_local_dialog_fallbacks_are_available_for_non_resource_pages(self):
		factory = (APP / "public/js/eduedge_ui/app_factory.js").read_text(encoding="utf-8")
		modal = APP / "public/js/eduedge_ui/components/EdgeModalFallback.vue"
		form = APP / "public/js/eduedge_ui/components/EdgeFormDialogFallback.vue"
		self.assertTrue(modal.exists())
		self.assertTrue(form.exists())
		self.assertIn('registerFallbackComponent(app, "EdgeModal"', factory)
		self.assertIn('registerFallbackComponent(app, "EdgeFormDialog"', factory)

	def test_quick_entry_mutations_are_platform_guarded(self):
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		safe_api = (APP / "api/modal_records_safe.py").read_text(encoding="utf-8")
		self.assertIn('"eduedge.api.modal_records.save_modal_record"', hooks)
		self.assertIn("require_eduedge_access", safe_api)
		self.assertIn("RESOURCE_FEATURES", safe_api)
		self.assertIn("reference_doctype", safe_api)

	def test_settings_center_is_tabbed_and_product_branding_is_not_tenant_editable(self):
		api = (APP / "api/settings_center.py").read_text(encoding="utf-8")
		component = (APP / "public/js/eduedge_settings_center/EduEdgeSettingsCenter.vue").read_text(encoding="utf-8")
		settings = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_settings"
			/ "eduedge_settings.json"
		).read_text(encoding="utf-8")
		for expected in (
			"TAB_CONFIG",
			'"defaults"',
			'"branch_access"',
			'"report_cards"',
			'"features"',
			"save_settings_tab",
			"get_default_branch_options",
			"eduedge-settings-tabs",
			"Open Branch Governance",
			"product_identity_managed_by",
			"get_product_identity",
			"require_eduedge_access",
		):
			self.assertIn(expected, api + component)
		self.assertNotIn('"branding"', api)
		self.assertNotIn('"eduedge_logo"', settings)
		self.assertNotIn('"enable_user_branch_access_enforcement", "label"', api)
		self.assertNotIn("ignore_permissions", api)

	def test_all_new_pages_are_standard_frappe_pages(self):
		page_root = APP / "eduedge/page"
		for page_name in (
			"eduedge_admissions",
			"eduedge_applicants",
			"eduedge_students",
			"eduedge_programs",
			"eduedge_program_offerings",
			"eduedge_school_branches",
			"eduedge_settings_center",
		):
			page = page_root / page_name
			self.assertTrue((page / "__init__.py").exists(), page_name)
			self.assertTrue(any(page.glob("*.js")), page_name)
			self.assertTrue(any(page.glob("*.json")), page_name)


if __name__ == "__main__":
	unittest.main()
