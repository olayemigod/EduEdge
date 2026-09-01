from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAcademicOperationsAndResourceSingularTerminologyContract(unittest.TestCase):
	def test_academic_operations_payload_includes_selected_branch_terms(self):
		api = (APP / "api" / "integration_qa_hardening.py").read_text()
		ast.parse(api)
		for token in (
			"get_effective_institution_context",
			"resolved_branch = _preferred_operational_branch(branch)",
			'institution_context = get_effective_institution_context(branch=resolved_branch)',
			'payload["institution_context"] = institution_context',
			'payload["terms"] = institution_context.get("terms") or {}',
		):
			self.assertIn(token, api)

	def test_resource_api_returns_explicit_singular_titles(self):
		api = (APP / "api" / "resource_center_safe.py").read_text()
		ast.parse(api)
		for token in (
			'"school_branches": _("School Branch")',
			'"programs": "programme"',
			'"program_offerings": "programme_offering"',
			'result["singular_title"] = _term_label',
			'RESOURCE_SINGULAR_TITLES.get(resource)',
		):
			self.assertIn(token, api)

	def test_resource_ui_does_not_guess_singular_grammar(self):
		component = (APP / "public" / "js" / "eduedge_resource_center" / "EduEdgeResourceCenter.vue").read_text()
		self.assertIn('singular_title: ""', component)
		self.assertIn('return String(this.page.singular_title || "Record")', component)
		self.assertNotIn('title.endsWith("ies")', component)
		self.assertNotIn('title.endsWith("s")', component)
		self.assertNotIn('title.slice(0, -1)', component)


if __name__ == "__main__":
	unittest.main()
