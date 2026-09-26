from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestReportCardIssueContract(unittest.TestCase):
	def test_issued_report_card_is_immutable_and_hashed(self):
		path = APP / "eduedge" / "doctype" / "eduedge_report_card_issue" / "eduedge_report_card_issue.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"] for field in payload["fields"]}
		for fieldname in ("result_publication", "report_card_review", "issue_version", "student", "payload_hash", "payload_json"):
			self.assertIn(fieldname, fields)
		for permission in payload["permissions"]:
			self.assertFalse(permission.get("write"))
			self.assertFalse(permission.get("create"))
		model = path.with_suffix(".py").read_text()
		self.assertIn("Issued Report Cards are immutable", model)
		self.assertIn("sha256", model)

	def test_approval_issues_frozen_report_card_and_reapproval_versions_it(self):
		api = (APP / "api" / "report_cards.py").read_text()
		service = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn("create_report_card_issue", api)
		self.assertIn("_next_issue_version", service)
		self.assertIn("supersedes_issue", service)
		self.assertIn("_prefer_issued=False", service)

	def test_pdf_prefers_issued_payload_only_while_review_is_approved(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		report_cards = (APP / "education" / "report_cards.py").read_text()
		self.assertIn('review.progression_status != "Approved"', service)
		self.assertIn("get_effective_issued_payload", report_cards)
		self.assertIn("_prefer_issued: bool = True", report_cards)

	def test_reopen_keeps_old_issue_but_live_preview_stops_using_it_until_reapproval(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn('return None', service)
		self.assertNotIn("delete", service.lower())

	def test_issue_permissions_are_branch_scoped(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "education" / "permissions.py").read_text()
		self.assertIn('"EduEdge Report Card Issue"', hooks)
		self.assertIn("report_card_issue_query", hooks)
		self.assertIn("has_report_card_issue_permission", hooks)
		self.assertIn('"EduEdge Report Card Issue"', permissions)


if __name__ == "__main__":
	unittest.main()
