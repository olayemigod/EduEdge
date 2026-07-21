from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = ROOT / "eduedge" / "eduedge" / "doctype"


class TestCBTFoundationContract(unittest.TestCase):
	def _load_doctype(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_examination_centre_separates_school_and_platform_scope(self):
		payload = self._load_doctype(
			"eduedge_examination_centre", "eduedge_examination_centre.json"
		)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertIn("School Examination Centre", fields["centre_type"]["options"])
		self.assertIn("EduEdge Exam Centre", fields["centre_type"]["options"])
		self.assertEqual(fields["school_branch"]["options"], "EduEdge School Branch")
		self.assertIn("mandatory_depends_on", fields["school_branch"])
		self.assertIn("allow_public_registration", fields)
		self.assertIn("allow_paid_exams", fields)

	def test_question_bank_has_ownership_versioning_and_answer_governance(self):
		payload = self._load_doctype(
			"eduedge_cbt_question", "eduedge_cbt_question.json"
		)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		for fieldname in (
			"question_code",
			"ownership_scope",
			"school_branch",
			"version_number",
			"supersedes_question",
			"course",
			"question_type",
			"question_text",
			"options",
			"answer_key",
			"marking_guide",
			"default_mark",
			"negative_mark",
			"status",
			"reviewed_by",
			"reviewed_on",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["options"]["options"], "EduEdge Question Option")
		self.assertIn("School Question Bank", fields["ownership_scope"]["options"])
		self.assertIn("EduEdge Examination Bank", fields["ownership_scope"]["options"])

	def test_question_permissions_do_not_expose_answer_bank_to_candidates_or_invigilators(self):
		payload = self._load_doctype(
			"eduedge_cbt_question", "eduedge_cbt_question.json"
		)
		roles = {permission["role"] for permission in payload["permissions"]}
		self.assertNotIn("Student", roles)
		self.assertNotIn("EduEdge Parent", roles)
		self.assertNotIn("CBT Invigilator", roles)
		self.assertIn("Teacher", roles)
		self.assertIn("Academic Administrator", roles)
		self.assertIn("EduEdge Super Administrator", roles)

	def test_question_controller_enforces_approval_and_immutability(self):
		text = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.py"
		).read_text()
		self.assertIn("ALLOWED_STATUS_TRANSITIONS", text)
		self.assertIn("Approved question content is immutable", text)
		self.assertIn("Create a new version instead", text)
		self.assertIn("Approved or Retired CBT questions cannot be deleted", text)
		self.assertIn("def autoname", text)
		self.assertIn("Only an EduEdge platform administrator", text)
		self.assertIn("assert_branch_access", text)

	def test_platform_records_remain_hidden_during_legacy_branch_fallback(self):
		text = (ROOT / "eduedge" / "cbt" / "permissions.py").read_text()
		self.assertIn("school_branch` is not null", text)
		self.assertIn("if not branch:", text)
		self.assertIn("return False", text)
		self.assertIn("PLATFORM_MANAGER_ROLES", text)

	def test_cbt_records_are_registered_for_branch_permissions(self):
		hooks = (ROOT / "eduedge" / "hooks.py").read_text()
		self.assertIn('"EduEdge Examination Centre": "eduedge.cbt.permissions.examination_centre_query"', hooks)
		self.assertIn('"EduEdge CBT Question": "eduedge.cbt.permissions.cbt_question_query"', hooks)
		self.assertIn('"EduEdge Examination Centre": "eduedge.cbt.permissions.has_school_branch_permission"', hooks)
		self.assertIn('"EduEdge CBT Question": "eduedge.cbt.permissions.has_school_branch_permission"', hooks)

	def test_question_option_is_a_child_table(self):
		payload = self._load_doctype(
			"eduedge_question_option", "eduedge_question_option.json"
		)
		self.assertEqual(payload["istable"], 1)
		fields = {field["fieldname"] for field in payload["fields"]}
		self.assertEqual(
			fields,
			{"option_key", "option_text", "is_correct", "display_order"},
		)


if __name__ == "__main__":
	unittest.main()
