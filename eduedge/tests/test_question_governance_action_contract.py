from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestQuestionGovernanceActionContract(unittest.TestCase):
	def test_governance_service_defines_single_record_actions_and_policy_checks(self):
		source = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		for expected in (
			'ACTION_SUBMIT = "submit_for_review"',
			'ACTION_RETURN = "return_to_draft"',
			'ACTION_APPROVE = "approve"',
			'ACTION_RETIRE = "retire"',
			"resolve_question_governance",
			'policy.get("question_approval_mode") == "Standard"',
			'require_separate_question_approver',
			'allow_academic_admin_override',
			'_value(question, "owner") == user',
			"can_author_public_exams",
		):
			self.assertIn(expected, source)
		self.assertNotIn("bulk", source.lower())

	def test_status_changes_require_governance_context_and_stale_records_are_rejected(self):
		service = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		lifecycle = (APP / "cbt/master_lifecycle.py").read_text(encoding="utf-8")
		for expected in (
			"GOVERNANCE_ACTION_FLAG",
			"governance_action_context",
			"validate_question_governance_transition",
			"expected_modified",
			"TimestampMismatchError",
			"doc.save()",
		):
			self.assertIn(expected, service)
		self.assertIn("validate_question_governance_transition(doc)", lifecycle)
		self.assertIn("Use the Question Bank or Question Builder action", service)

	def test_approval_audit_is_set_without_overwriting_it_on_retirement(self):
		source = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		transition_start = source.index("with governance_action_context(action):")
		transition_end = source.index("\n\t\tdoc.save()", transition_start)
		transition_block = source[transition_start:transition_end]
		self.assertIn("doc.reviewed_by = frappe.session.user", transition_block)
		self.assertIn("doc.reviewed_on = now_datetime()", transition_block)
		self.assertNotIn("elif action == ACTION_RETIRE", transition_block)

	def test_whitelisted_api_requires_record_read_permission(self):
		source = (APP / "api/question_governance.py").read_text(encoding="utf-8")
		for expected in (
			"@frappe.whitelist()",
			'doc.has_permission("read")',
			"get_question_action_state(doc)",
			'state["modified"] = str(doc.modified)',
			"apply_question_action(doc, action, expected_modified=expected_modified)",
		):
			self.assertIn(expected, source)

	def test_builder_saves_content_before_calling_governed_action_api(self):
		source = (APP / "public/js/eduedge_question_builder.bundle.js").read_text(encoding="utf-8")
		for expected in (
			"question_action_state",
			"loadQuestionActionState",
			"this.payload(currentStatus)",
			"eduedge.api.question_builder.save_question",
			"eduedge.api.question_governance.perform_action",
			'"return_to_draft"',
			'"submit_for_review"',
			"requires_confirmation",
			"expected_modified: this.context?.question_action_state?.modified",
		):
			self.assertIn(expected, source)
		self.assertLess(
			source.index("eduedge.api.question_builder.save_question"),
			source.index("eduedge.api.question_governance.perform_action"),
		)
		self.assertNotIn("this.payload(targetStatus)", source)


if __name__ == "__main__":
	unittest.main()
