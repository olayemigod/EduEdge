from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProfessionalNavigationContract(unittest.TestCase):
	def test_product_sidebar_uses_grouped_semantic_svg_icon_names(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		for expected in (
			"menuGroup(",
			"defaultCollapsed: true",
			"items: items.filter",
			'__("Students & Admissions")',
			'__("Academic Setup")',
			'__("Assessments & Results")',
			'__("CBT Delivery")',
			'__("CBT Content")',
			'__("Institution & Access")',
			'"home"',
			'"graduation"',
			'"assessment"',
			'"report"',
			'"shield"',
			'"settings"',
		):
			self.assertIn(expected, navigation)
		for forbidden in ('icon: "⌂"', 'icon: "⚙"', 'icon: "C"', 'icon: "R"'):
			self.assertNotIn(forbidden, navigation)

	def test_compact_sidebar_density_is_product_scoped(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		styles = (APP / "public/css/eduedge_compact_navigation.css").read_text()
		self.assertIn("eduedge_compact_navigation.css", navigation)
		self.assertIn('data-edge-product="eduedge"', styles)
		self.assertIn("--edge-sidebar-width: 14.25rem", styles)
		self.assertIn(".edge-sidebar-item__description", styles)
		self.assertIn("display: none", styles)

	def test_global_product_menu_uses_shared_edgesuite_renderer_and_permissions(self):
		bundle = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		for expected in (
			'frappe.require("edgesuite_ui.bundle.js"',
			"window.EdgeSuiteUI || window.EdgeUI",
			"registerProductMenu",
			"Students & Admissions",
			"Academic Setup",
			"Assessments & Results",
			"CBT Delivery",
			"CBT Content",
			"Institution & Access",
			"accordion: true",
			"featureEnabled",
			"quick_action: true",
			"eduedge_access_manifest",
			"itemAllowed",
			"permissionFilteredMenu",
			'resource: "user_branch_access"',
			'permissions: ["read", "write"]',
		):
			self.assertIn(expected, bundle)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', bundle)
		self.assertNotIn("GOVERNANCE_VIEW_ROLES", bundle)
		self.assertNotIn("ADMIN_ROLES", bundle)
		self.assertNotIn("import coreedge", bundle.lower())
		self.assertNotIn("from coreedge", bundle.lower())

	def test_hooks_use_shared_edgesuite_identity_and_notifications(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"/assets/eduedge/js/eduedge_keyboard_shortcuts.js"', hooks)
		self.assertIn('"eduedge_product_menu.bundle.js"', hooks)
		self.assertIn('extend_bootinfo = "eduedge.boot.extend_bootinfo"', hooks)
		self.assertIn('"route": "/desk/eduedge-home"', hooks)
		self.assertIn("refresh_cached_runtime_context", hooks)
		self.assertIn("delete_resource_record", hooks)
		self.assertIn("save_modal_record", hooks)
		self.assertNotIn('"eduedge_shell_identity.bundle.js"', hooks)
		self.assertNotIn('"/assets/eduedge/css/eduedge_shell_identity.css"', hooks)

	def test_home_requires_edgesuite_ui_0_3_shared_contracts(self):
		loader = (APP / "eduedge/page/eduedge_home/eduedge_home.js").read_text()
		self.assertIn("supportsSharedShell", loader)
		self.assertIn("EdgeSuite UI 0.3 or newer", loader)
		self.assertIn("runtime.version", loader)
		self.assertLess(
			loader.index('frappe.require("edgesuite_ui.bundle.js"'),
			loader.index('frappe.require("eduedge_home.bundle.js"'),
		)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)

	def test_non_eduedge_desk_routes_open_in_new_tab(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		self.assertIn("EDUEDGE_UI_ROUTES", navigation)
		self.assertIn("isEduEdgeUIRoute", navigation)
		self.assertIn('window.open(route, "_blank", "noopener,noreferrer")', navigation)
		self.assertIn('window.location.href = route', navigation)
		self.assertIn("hasEduEdgeRouteAccess", navigation)
		self.assertIn("Access not available", navigation)

	def test_school_product_and_user_identity_use_shared_contract(self):
		boot = (APP / "boot.py").read_text()
		settings = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_settings"
			/ "eduedge_settings.json"
		).read_text()
		runtime = (APP / "platform" / "runtime_context.py").read_text()
		self.assertIn('"company_logo"', boot)
		self.assertIn("get_product_identity", boot)
		self.assertIn("product_identity_source", boot)
		self.assertIn("product_branding", runtime)
		self.assertIn("CoreEdge", runtime)
		self.assertNotIn('"eduedge_logo"', settings)
		self.assertNotIn('get_single_value("EduEdge Settings", "eduedge_logo")', boot)
		self.assertIn('"product_icon": "graduation"', boot)
		self.assertIn('"tenant_icon": "building"', boot)
		self.assertIn('shared["eduedge"] = identity', boot)
		self.assertIn('bootinfo["edgesuite_ui_identity"] = shared', boot)
		self.assertIn('bootinfo["eduedge_ui_identity"] = identity', boot)
		self.assertIn('bootinfo["eduedge_access_manifest"]', boot)

	def test_professional_menu_does_not_replace_backend_permissions(self):
		bundle = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		access = (APP / "access_control.py").read_text()
		permissions = (APP / "education/permissions.py").read_text()
		self.assertIn("eduedge_access_manifest", bundle)
		self.assertIn("RESOURCE_DOCTYPES", access)
		self.assertIn("ROUTE_REQUIREMENTS", access)
		self.assertIn("get_allowed_school_branches", permissions)
		self.assertIn("has_school_branch_permission", permissions)


if __name__ == "__main__":
	unittest.main()
