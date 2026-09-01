from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestTerminologyIdempotencyContract(unittest.TestCase):
	def test_product_menu_has_no_dom_wide_friendly_name_rewriter(self):
		bundle = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
		for forbidden in (
			"function friendlyPairs",
			"function replaceValue",
			"function applyVisibleFriendlyNames",
			"function scheduleVisibleFriendlyNames",
			"__eduedgeFriendlyNameObserver = new MutationObserver",
		):
			self.assertNotIn(forbidden, bundle)
		self.assertIn("buildEduEdgeProductMenu", bundle)
		self.assertIn("registerEduEdgeProductMenu", bundle)
		self.assertIn('term("programme", { plural: true', bundle)
		self.assertIn('term("programme_offering", { plural: true', bundle)
		self.assertIn('item("School Branches"', bundle)

	def test_product_menu_disconnects_any_stale_observer_from_old_assets(self):
		bundle = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text(encoding="utf-8")
		self.assertIn("window.__eduedgeFriendlyNameObserver?.disconnect?.()", bundle)
		self.assertIn("delete window.__eduedgeFriendlyNameObserver", bundle)

	def test_edgesuite_surfaces_are_marked_as_terminology_managed(self):
		shell = (APP / "public" / "js" / "eduedge_shell_identity.bundle.js").read_text(encoding="utf-8")
		for token in (
			'".edge-app-shell"',
			'".edge-sidebar"',
			'".edge-product-menu"',
			'"[data-edge-product-menu]"',
			"markManagedTerminologySurfaces",
			'element.setAttribute("data-eduedge-terminology-managed", "1")',
			"processShellMutations",
		):
			self.assertIn(token, shell)

	def test_native_terminology_observer_respects_managed_surfaces(self):
		terminology = (APP / "public" / "js" / "eduedge_terminology.bundle.js").read_text(encoding="utf-8")
		self.assertIn('"[data-eduedge-terminology-managed]"', terminology)
		self.assertIn("isProtectedTerminologySurface(parent)", terminology)
		self.assertIn("isProtectedTerminologySurface(element)", terminology)

	def test_programme_page_keeps_selected_institution_context(self):
		component = (APP / "public" / "js" / "eduedge_programmes" / "EduEdgeProgrammes.vue").read_text(encoding="utf-8")
		for token in (
			"pageContext()",
			"draftContext()",
			"this.filters.institution",
			"institution.institution_type",
			"mixedInstitutionView",
		):
			self.assertIn(token, component)

	def test_academic_operations_renders_terms_from_component_context(self):
		component = (APP / "public" / "js" / "eduedge_academic_operations" / "EduEdgeAcademicOperations.vue").read_text(encoding="utf-8")
		self.assertIn("<EdgeAppShell", component)
		self.assertIn("term('student_group'", component)
		self.assertIn("term('programme'", component)
		self.assertIn("term('programme_offering'", component)


if __name__ == "__main__":
	unittest.main()
