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
		self.assertIn("centre_status", fields)
		self.assertIn("Draft\nActive\nSuspended\nRetired", fields["centre_status"]["options"])
		self.assertTrue(fields["enabled"]["read_only"])
		self.assertTrue(fields["enabled"]["hidden"])
		self.assertIn("public_hosting_status", fields)
		self.assertTrue(fields["public_hosting_status"]["read_only"])

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
		self.assertEqual(fields["options"]["label"], "Answer Choices")
		self.assertIn("School Question Bank", fields["ownership_scope"]["options"])
		self.assertIn("EduEdge Examination Bank", fields["ownership_scope"]["options"])
		self.assertIn("Yes/No", fields["question_type"]["options"])
		self.assertIn("'Yes/No'", fields["options"]["depends_on"])

	def test_question_uses_native_course_topics_and_friendly_defaults(self):
		payload = self._load_doctype(
			"eduedge_cbt_question", "eduedge_cbt_question.json"
		)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(fields["topic"]["fieldtype"], "Link")
		self.assertEqual(fields["topic"]["options"], "Topic")
		self.assertEqual(fields["curriculum"]["fieldtype"], "Data")
		self.assertIn("does not currently provide a native Curriculum master", fields["curriculum"]["description"])
		self.assertEqual(fields["exam_body"]["default"], "School Internal")
		self.assertEqual(fields["question_type"]["default"], "Single Choice")
		self.assertIn("starts without preloaded answer rows", fields["question_type"]["description"])

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
		self.assertIn("EduEdge Public Exam Administrator", roles)

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
		self.assertIn("require_public_exam_authoring", text)
		self.assertIn("assert_branch_access", text)

	def test_question_controller_prepares_only_fixed_binary_answers(self):
		text = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.py"
		).read_text()
		self.assertIn('"Yes/No": ("Yes", "No")', text)
		self.assertIn('"True/False": ("True", "False")', text)
		self.assertIn("def option_label", text)
		self.assertIn("def _prepare_answer_options", text)
		self.assertNotIn("while len(rows) < 2", text)
		self.assertIn('row.option_key = label', text)
		self.assertIn('Enter an Answer for option {0}', text)
		self.assertIn('self.question_type in {"Single Choice", "True/False", "Yes/No"}', text)

	def test_question_topic_is_course_filtered_and_server_validated(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.py"
		).read_text()
		script = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.js"
		).read_text()
		self.assertIn("def _validate_topic", controller)
		self.assertIn('frappe.db.exists(\n\t\t\t"Course Topic"', controller)
		self.assertIn("def course_topic_query", controller)
		self.assertIn("INNER JOIN `tabTopic`", controller)
		self.assertIn("course_topic.parentfield = 'topics'", controller)
		self.assertIn('frm.set_query("topic"', script)
		self.assertIn("course_topic_query", script)
		self.assertIn('await frm.set_value("topic", null)', script)

	def test_question_form_prepares_answer_rows_when_type_changes(self):
		text = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_question"
			/ "eduedge_cbt_question.js"
		).read_text()
		self.assertIn('"Yes/No": ["Yes", "No"]', text)
		self.assertIn('"True/False": ["True", "False"]', text)
		self.assertIn("function optionLabel", text)
		self.assertIn("function prepareAnswerOptions", text)
		self.assertIn("question_type(frm)", text)
		self.assertIn("ensureMinimumChoiceAnswers(frm)", text)
		self.assertIn("fresh question defaults to Single Choice without preloading answers", text)
		self.assertIn("normaliseAnswerOptions(frm)", text)
		self.assertIn('frappe.ui.form.on("EduEdge Question Option"', text)

	def test_platform_records_remain_hidden_during_legacy_branch_fallback(self):
		text = (ROOT / "eduedge" / "cbt" / "permissions.py").read_text()
		self.assertIn("school_branch` is not null", text)
		self.assertIn("if not branch:", text)
		self.assertIn("return False", text)
		self.assertIn("can_author_public_exams", text)
		self.assertNotIn("PLATFORM_MANAGER_ROLES", text)

	def test_cbt_records_are_registered_for_branch_permissions(self):
		hooks = (ROOT / "eduedge" / "hooks.py").read_text()
		self.assertIn('"EduEdge Examination Centre": "eduedge.cbt.permissions.examination_centre_query"', hooks)
		self.assertIn('"EduEdge CBT Question": "eduedge.cbt.permissions.cbt_question_query"', hooks)
		self.assertIn('"EduEdge Examination Centre": "eduedge.cbt.permissions.has_school_branch_permission"', hooks)
		self.assertIn('"EduEdge CBT Question": "eduedge.cbt.permissions.has_school_branch_permission"', hooks)

	def test_question_option_is_a_friendly_child_table(self):
		payload = self._load_doctype(
			"eduedge_question_option", "eduedge_question_option.json"
		)
		self.assertEqual(payload["istable"], 1)
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(
			set(fields),
			{"option_key", "option_text", "is_correct", "display_order"},
		)
		self.assertEqual(fields["option_key"]["label"], "Option")
		self.assertTrue(fields["option_key"]["read_only"])
		self.assertEqual(fields["option_text"]["label"], "Answer")
		self.assertTrue(fields["option_text"]["reqd"])
		self.assertEqual(fields["is_correct"]["label"], "Correct Answer")
		self.assertTrue(fields["display_order"]["hidden"])
		self.assertTrue(fields["display_order"]["read_only"])

	def test_centre_status_patch_is_registered(self):
		patches = (ROOT / "eduedge" / "patches.txt").read_text()
		patch = (ROOT / "eduedge" / "patches" / "v0_8" / "backfill_examination_centre_status.py").read_text()
		self.assertIn("backfill_examination_centre_status", patches)
		self.assertIn("WHEN COALESCE(`enabled`, 0) = 1 THEN 'Active'", patch)


if __name__ == "__main__":
	unittest.main()
