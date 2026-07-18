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
			'icon: "graduation"',
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

	def test_hooks_load_product_menu_globally(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('app_include_js = ["eduedge_product_menu.bundle.js"]', hooks)

	def test_professional_menu_does_not_replace_backend_permissions(self):
		bundle = (APP / "public/js/eduedge_product_menu.bundle.js").read_text()
		permissions = (APP / "education/permissions.py").read_text()
		self.assertIn("roles:", bundle)
		self.assertIn("get_allowed_school_branches", permissions)
		self.assertIn("has_school_branch_permission", permissions)


if __name__ == "__main__":
	unittest.main()
