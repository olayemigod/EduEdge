from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestQuestionBankPhase3BContract(unittest.TestCase):
	def test_pagination_helpers_clamp_to_supported_page_boundaries(self):
		source = (APP / "api/question_bank.py").read_text(encoding="utf-8")
		tree = ast.parse(source)
		helpers = [
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name in {"_normalise_page_length", "_clamp_page_start"}
		]
		self.assertEqual({node.name for node in helpers}, {"_normalise_page_length", "_clamp_page_start"})
		namespace = {
			"cint": lambda value: int(value or 0),
			"PAGE_LENGTH_OPTIONS": (20, 50, 100),
			"DEFAULT_PAGE_LENGTH": 20,
		}
		exec(compile(ast.Module(body=helpers, type_ignores=[]), "question_bank_helpers", "exec"), namespace)
		self.assertEqual(namespace["_normalise_page_length"](50), 50)
		self.assertEqual(namespace["_normalise_page_length"](75), 20)
		self.assertEqual(namespace["_clamp_page_start"](999, 41, 20), 40)
		self.assertEqual(namespace["_clamp_page_start"](-20, 41, 20), 0)
		self.assertEqual(namespace["_clamp_page_start"](20, 0, 20), 0)

	def test_api_rejects_unpermitted_cascading_filter_values(self):
		api = (APP / "api/question_bank.py").read_text(encoding="utf-8")
		for expected in (
			"_require_allowed_selection",
			"_effective_institution",
			"_course_scope_filters",
			"_resolve_course",
			"_clamp_page_start",
			"PAGE_LENGTH_OPTIONS = (20, 50, 100)",
			"The selected Subject / Course is not available in the permitted Question Bank context.",
			'resolved_institution = _require_allowed_selection(institution, institution_values, _("Institution"))',
			'resolved_branch = _require_allowed_selection(branch, branch_values, _("Branch / Campus"))',
			"ownership_scope: str | None = None",
			"branch: str | None = None",
		):
			self.assertIn(expected, api)
		for forbidden in (
			"ignore_permissions=True",
			"frappe.db.sql(",
			"resolved_institution = _normalise_selection(institution",
			"resolved_branch = _normalise_selection(branch",
		):
			self.assertNotIn(forbidden, api)

	def test_frontend_sequences_requests_and_clears_subject_after_branch_change(self):
		bundle = (APP / "public/js/eduedge_question_bank.bundle.js").read_text(encoding="utf-8")
		for expected in (
			"questionBankRequestSerial",
			"const requestId = ++this.questionBankRequestSerial",
			"requestId !== this.questionBankRequestSerial",
			"questionBankLastBranch",
			'this.filters.course = ""',
			'this.courseLabel = ""',
			"ownership_scope: this.filters.ownership_scope",
			"institution: this.filters.institution",
			"branch: this.filters.branch",
			"!this.pagination.has_previous",
			"!this.pagination.has_next",
		):
			self.assertIn(expected, bundle)
		self.assertNotIn("if (this.loading) return;", bundle)

	def test_existing_questions_open_read_only_without_relaxing_write_actions(self):
		builder = (APP / "api/question_builder.py").read_text(encoding="utf-8")
		tree = ast.parse(builder)
		functions = {
			node.name: ast.get_source_segment(builder, node) or ""
			for node in tree.body
			if isinstance(node, ast.FunctionDef)
		}
		context = functions["get_question_builder_context"]
		self.assertIn("if question:", context)
		self.assertIn("_require_question_reader()", context)
		self.assertIn("_require_question_author()", context)
		self.assertLess(context.index("_require_question_reader()"), context.index("_require_question_author()"))
		self.assertIn("_require_question_reader()", functions["search_topics"])
		self.assertIn("_require_question_author()", functions["save_question"])
		self.assertIn("_require_question_author()", functions["create_question_version"])
		self.assertIn('source_doc.has_permission("write")', builder)
		self.assertIn('status in {"Approved", "Retired"}', builder)


if __name__ == "__main__":
	unittest.main()
