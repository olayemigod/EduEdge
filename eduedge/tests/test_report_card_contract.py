from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardContract(unittest.TestCase):
	def test_report_card_review_has_comments_metrics_and_progression(self):
		path = APP / "eduedge" / "doctype" / "eduedge_report_card_review" / "eduedge_report_card_review.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in ("result_publication", "school_branch", "student_group", "student", "average_percent", "attendance_percent", "class_teacher_comment", "principal_comment", "progression_recommendation", "progression_status"):
			self.assertIn(fieldname, fields)

	def test_report_cards_require_published_result_scope(self):
		service = (APP / "education" / "report_cards.py").read_text()
		self.assertIn('publication.status != "Published"', service)
		self.assertIn("report_card_ready", service)
		self.assertIn('"docstatus": 1', service)

	def test_report_card_workflow_does_not_mutate_accounting_or_submitted_results(self):
		api = (APP / "api" / "report_cards.py").read_text()
		service = (APP / "education" / "report_cards.py").read_text()
		combined = api + service
		self.assertNotIn('db_set("Assessment Result"', combined)
		self.assertNotIn('set_value("Assessment Result"', combined)
		self.assertNotIn('frappe.get_doc("Program Enrollment"', combined)
		self.assertNotIn('"doctype": "Program Enrollment"', combined)
		self.assertIn("preview_report_card", api)

	def test_principal_comment_is_backend_role_protected(self):
		service = (APP / "education" / "report_cards.py").read_text()
		api = (APP / "api" / "report_cards.py").read_text()
		self.assertIn("principal_comment", service)
		self.assertIn("APPROVER_ROLES", service)
		self.assertIn("Only an authorized academic approver", service)
		self.assertIn("require_principal_comment", api)

	def test_report_card_settings_are_configurable(self):
		path = APP / "eduedge" / "doctype" / "eduedge_settings" / "eduedge_settings.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in ("report_card_show_marks", "report_card_letter_head", "promotion_pass_average", "require_class_teacher_comment", "require_principal_comment"):
			self.assertIn(fieldname, fields)

	def test_report_card_page_uses_edgesuite_shell(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		loader = (APP / "eduedge" / "page" / "eduedge_report_cards" / "eduedge_report_cards.js").read_text()
		self.assertIn("<EdgeAppShell", vue)
		self.assertIn("edgeui.bundle.js", loader)
		self.assertLess(loader.index("edgeui.bundle.js"), loader.index("eduedge_report_cards.bundle.js"))
		self.assertIn("Progression Recommendation", vue)

	def test_pdf_template_contains_publication_and_comments(self):
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("publication.name", template)
		self.assertIn("class_teacher_comment", template)
		self.assertIn("principal_comment", template)
		self.assertIn("progression_recommendation", template)

	def test_hooks_scope_report_card_reviews(self):
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"EduEdge Report Card Review"', hooks)
		self.assertIn("report_card_review_query", hooks)
		self.assertIn("has_school_branch_permission", hooks)


if __name__ == "__main__":
	unittest.main()
