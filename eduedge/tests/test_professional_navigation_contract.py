from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestProfessionalNavigationContract(unittest.TestCase):
	def test_product_sidebar_uses_grouped_semantic_svg_icon_names(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		for expected in (
			"section:",
			"sectionIcon:",
			"description:",
			'icon: "home"',
			'sectionIcon: "graduation"',
			'icon: "assessment"',
			'icon: "report"',
			'icon: "shield"',
			'icon: "settings"',
		):
			self.assertIn(expected, navigation)
		for forbidden in ('icon: "⌂"', 'icon: "⚙"', 'icon: "C"', 'icon: "R"'):
			self.assertNotIn(forbidden, navigation)

	def test_global_product_menu_uses_shared_edgesuite_renderer(self):
		bundle = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		for expected in (
			'frappe.require("edgeui.bundle.js"',
			"window.EdgeSuiteUI || window.EdgeUI",
			"registerProductMenu",
			"School Operations",
			"Academics and Outcomes",
			"Administration",
			"roles: GOVERNANCE_VIEW_ROLES",
			"roles: ADMIN_ROLES",
		):
			self.assertIn(expected, bundle)
		self.assertNotIn("import coreedge", bundle.lower())
		self.assertNotIn("from coreedge", bundle.lower())

	def test_hooks_use_shared_edgesuite_identity_and_notifications(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"eduedge_product_menu.bundle.js"', hooks)
		self.assertIn('extend_bootinfo = "eduedge.boot.extend_bootinfo"', hooks)
		self.assertIn('"route": "/desk/eduedge-home"', hooks)
		self.assertNotIn('"eduedge_shell_identity.bundle.js"', hooks)
		self.assertNotIn('"/assets/eduedge/css/eduedge_shell_identity.css"', hooks)

	def test_non_eduedge_desk_routes_open_in_new_tab(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text()
		self.assertIn("EDUEDGE_UI_ROUTES", navigation)
		self.assertIn("isEduEdgeUIRoute", navigation)
		self.assertIn('window.open(route, "_blank", "noopener,noreferrer")', navigation)
		self.assertIn('window.location.href = route', navigation)

	def test_school_product_and_user_identity_use_shared_contract(self):
		boot = (APP / "boot.py").read_text()
		settings = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_settings"
			/ "eduedge_settings.json"
		).read_text()
		self.assertIn('"company_logo"', boot)
		self.assertIn('"eduedge_logo"', boot)
		self.assertIn('"user_image"', boot)
		self.assertIn('"user": _get_user_identity()', boot)
		self.assertIn('"product_name": "EduEdge"', boot)
		self.assertIn('"product_icon": "graduation"', boot)
		self.assertIn('shared["eduedge"] = identity', boot)
		self.assertIn('bootinfo["edgesuite_ui_identity"] = shared', boot)
		self.assertIn('bootinfo["eduedge_ui_identity"] = identity', boot)
		self.assertIn('"eduedge_logo"', settings)

	def test_professional_menu_does_not_replace_backend_permissions(self):
		bundle = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		permissions = (APP / "education/permissions.py").read_text()
		self.assertIn("roles:", bundle)
		self.assertIn("get_allowed_school_branches", permissions)
		self.assertIn("has_school_branch_permission", permissions)


if __name__ == "__main__":
	unittest.main()
