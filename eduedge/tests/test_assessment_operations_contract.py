from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentOperationsContract(unittest.TestCase):
	def test_assessment_records_receive_branch_context(self):
		text = (APP / "education" / "custom_fields.py").read_text()
		self.assertIn('"Assessment Plan": [', text)
		self.assertIn('"Assessment Result": [', text)
		self.assertIn("_backfill_assessment_plans", text)
		self.assertIn("_backfill_assessment_results", text)

	def test_hooks_scope_assessment_records_and_publications(self):
		text = (APP / "hooks.py").read_text()
		for doctype in (
			"Assessment Plan",
			"Assessment Result",
			"EduEdge Result Publication",
			"EduEdge Result Publication Log",
		):
			self.assertIn(f'"{doctype}"', text)
		self.assertIn("before_validate_assessment_plan", text)
		self.assertIn("before_validate_assessment_result", text)

	def test_result_publication_has_approval_and_readiness_fields(self):
		path = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_result_publication"
			/ "eduedge_result_publication.json"
		)
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in (
			"school_branch",
			"student_group",
			"assessment_group",
			"status",
			"expected_results",
			"submitted_results",
			"draft_results",
			"missing_results",
			"report_card_ready",
		):
			self.assertIn(fieldname, fields)

	def test_publication_api_does_not_mutate_submitted_results(self):
		text = (APP / "api" / "assessment_operations.py").read_text()
		self.assertNotIn('db_set("Assessment Result"', text)
		self.assertNotIn("frappe.db.set_value(\n\t\t\t\"Assessment Result\"", text)
		self.assertIn("request_result_approval", text)
		self.assertIn("approve_results", text)
		self.assertIn("publish_results", text)
		self.assertIn("get_report_card_readiness", text)

	def test_publication_log_is_append_only(self):
		text = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_result_publication_log"
			/ "eduedge_result_publication_log.py"
		).read_text()
		self.assertIn("append-only", text)
		self.assertIn("if not self.is_new()", text)

	def test_assessment_operations_page_uses_edgesuite_shell(self):
		vue = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_assessment_operations"
			/ "EduEdgeAssessmentOperations.vue"
		).read_text()
		loader = (
			APP
			/ "eduedge"
			/ "page"
			/ "eduedge_assessment_operations"
			/ "eduedge_assessment_operations.js"
		).read_text()
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("edgesuite_ui.bundle.js", loader)
		self.assertLess(
			loader.index("edgesuite_ui.bundle.js"),
			loader.index("eduedge_assessment_operations.bundle.js"),
		)
		self.assertNotIn('frappe.require("edgeui.bundle.js"', loader)
		self.assertIn("Result publication control", vue)


if __name__ == "__main__":
	unittest.main()
