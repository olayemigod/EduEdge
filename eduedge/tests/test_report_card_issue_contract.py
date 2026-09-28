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
		issue_creation = service.split("def create_report_card_issue", 1)[1].split("def get_effective_issued_payload", 1)[0]
		self.assertNotIn("delete", issue_creation.lower())

	def test_new_issues_archive_exact_private_pdf_bytes(self):
		path = APP / "eduedge" / "doctype" / "eduedge_report_card_issue" / "eduedge_report_card_issue.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in ("pdf_sha256", "pdf_filename", "pdf_size_bytes"):
			self.assertIn(fieldname, fields)
			self.assertTrue(fields[fieldname].get("read_only"))

		service = (APP / "education" / "report_card_issues.py").read_text()
		for token in (
			"issue.set_new_name()",
			'render_payload["issue_record"] = {',
			'render_payload["verification"] = build_issue_verification(issue.name, verification_token)',
			"pdf_bytes = render_report_card_pdf(render_payload)",
			"issue.pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()",
			"issue.pdf_size_bytes = len(pdf_bytes)",
			"issue.insert(ignore_permissions=True)",
			'"doctype": "File"',
			'"content": pdf_bytes',
			'"is_private": 1',
			'"attached_to_doctype": ISSUE_DOCTYPE',
			'"attached_to_name": issue.name',
			"file_doc.insert(ignore_permissions=True)",
			"get_archived_report_card_pdf(issue.name)",
		):
			self.assertIn(token, service)

	def test_archived_pdf_is_verified_and_legacy_issue_can_render_dynamically(self):
		service = (APP / "education" / "report_card_issues.py").read_text()
		for token in (
			"def resolve_report_card_pdf(payload: dict) -> bytes:",
			"def get_archived_report_card_pdf(issue_name: str) -> bytes:",
			'"pdf_sha256", "pdf_filename", "pdf_size_bytes"',
			"archive_values = (",
			"if any(archive_values):",
			"if not all(archive_values):",
			'"file_name": archive.pdf_filename',
			"if len(files) != 1:",
			'hmac.compare_digest(actual_hash, str(archive.pdf_sha256 or ""))',
			"len(pdf_bytes) != int(archive.pdf_size_bytes)",
			"return render_report_card_pdf(payload)",
		):
			self.assertIn(token, service)

		main_api = (APP / "api" / "report_cards.py").read_text()
		profiled_api = (APP / "api" / "report_cards_profiled.py").read_text()
		self.assertIn("resolve_report_card_pdf(payload)", main_api)
		self.assertIn("resolve_report_card_pdf(payload)", profiled_api)

	def test_archived_issue_pdf_file_cannot_be_changed_or_deleted(self):
		hooks = (APP / "hooks.py").read_text()
		service = (APP / "education" / "report_card_issues.py").read_text()
		self.assertIn(
			'"File": "eduedge.education.report_card_issues.has_archived_report_card_file_permission"',
			hooks,
		)
		self.assertIn("def has_archived_report_card_file_permission", service)
		self.assertIn('ptype in {"create", "write", "delete", "share"}', service)
		self.assertIn('ptype in {"read", "select", "print", "email"}', service)
		self.assertIn("frappe.has_permission(", service)
		self.assertIn("ISSUE_DOCTYPE", service)
		self.assertIn("return False", service)

	def test_issue_permissions_are_branch_scoped(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "education" / "permissions.py").read_text()
		self.assertIn('"EduEdge Report Card Issue"', hooks)
		self.assertIn("report_card_issue_query", hooks)
		self.assertIn("has_report_card_issue_permission", hooks)
		self.assertIn('"EduEdge Report Card Issue"', permissions)


if __name__ == "__main__":
	unittest.main()
