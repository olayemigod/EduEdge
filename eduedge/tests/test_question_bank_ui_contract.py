from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestQuestionBankUIContract(unittest.TestCase):
	def test_question_bank_page_and_bundle_are_registered(self):
		page_root = APP / "eduedge/page/eduedge_question_bank"
		for filename in ("__init__.py", "eduedge_question_bank.json", "eduedge_question_bank.js"):
			self.assertTrue((page_root / filename).exists(), filename)
		page = json.loads((page_root / "eduedge_question_bank.json").read_text(encoding="utf-8"))
		self.assertEqual(page["name"], "eduedge-question-bank")
		self.assertEqual(page["roles"], [])

		bundle = (APP / "public/js/eduedge_question_bank.bundle.js").read_text(encoding="utf-8")
		loader = (page_root / "eduedge_question_bank.js").read_text(encoding="utf-8")
		self.assertIn("createEduEdgeQuestionBankApp", bundle)
		self.assertIn("window.EduEdgeQuestionBank", bundle)
		self.assertIn("EdgeLinkField", loader)
		self.assertLess(loader.index("edgesuite_ui.bundle.js"), loader.index("eduedge_question_bank.bundle.js"))

	def test_question_bank_component_is_filterable_clickable_and_paginated(self):
		component = (
			APP / "public/js/eduedge_question_bank/EduEdgeQuestionBank.vue"
		).read_text(encoding="utf-8")
		for expected in (
			"<EdgeAppShell",
			"<EdgePageLayout",
			"<EdgeFilterBar",
			"<EdgeLinkField",
			"Institution",
			"Branch / Campus",
			"Subject / Course",
			"Question Type",
			"Exam Body / Source",
			"question_preview",
			"pagination.has_previous",
			"pagination.has_next",
			"/app/eduedge-question-builder?question=",
			"/app/eduedge-question-batch",
		):
			self.assertIn(expected, component)
		self.assertNotIn("answer_key", component)
		self.assertNotIn("marking_guide", component)
		self.assertNotIn("reviewed_by", component)

	def test_list_api_uses_permission_aware_question_queries_and_safe_payload(self):
		api = (APP / "api/question_bank.py").read_text(encoding="utf-8")
		for expected in (
			"frappe.has_permission(QUESTION_DOCTYPE, \"read\")",
			"frappe.get_list(\n\t\tQUESTION_DOCTYPE",
			"get_allowed_school_branches",
			"can_author_public_exams",
			"question_preview",
			"row.pop(\"question_text\"",
			"limit_start=resolved_start",
			"limit_page_length=resolved_page_length",
			"def _status_counts",
			"frappe.db.count(QUESTION_DOCTYPE",
		):
			self.assertIn(expected, api)
		for forbidden in (
			'"answer_key"',
			'"marking_guide"',
			'"reviewed_by"',
			'"notes"',
			"ignore_permissions=True",
			"frappe.db.sql(",
		):
			self.assertNotIn(forbidden, api)

	def test_navigation_and_access_manifest_expose_read_only_question_bank_route(self):
		navigation = (APP / "public/js/eduedge_ui/navigation.js").read_text(encoding="utf-8")
		access = (APP / "access_control.py").read_text(encoding="utf-8")
		for source in (navigation, access):
			self.assertIn("/app/eduedge-question-bank", source)
		self.assertIn('"/app/eduedge-question-bank": (("cbt_question", "read"),)', access)

	def test_cbt_operations_native_question_route_is_redirected_to_edgesuite_list(self):
		bundle = (APP / "public/js/eduedge_cbt_operations.bundle.js").read_text(encoding="utf-8")
		self.assertIn('route === "/app/eduedge-cbt-question"', bundle)
		self.assertIn('"/app/eduedge-question-bank"', bundle)
		self.assertIn("resolveCBTOperationsRoute", bundle)
		self.assertIn("openEduEdgeRoute", bundle)

	def test_ci_validates_question_bank_frontend_entries(self):
		workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
		self.assertIn("node --check eduedge/public/js/eduedge_question_bank.bundle.js", workflow)
		self.assertIn("node --check eduedge/eduedge/page/eduedge_question_bank/eduedge_question_bank.js", workflow)


if __name__ == "__main__":
	unittest.main()
