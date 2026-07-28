import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"
QUESTION_META = APP / "eduedge/doctype/eduedge_cbt_question/eduedge_cbt_question.json"


class TestQuestionStandardWorkflowContract(unittest.TestCase):
	def test_question_metadata_contains_standard_states_and_audit_fields(self):
		metadata = json.loads(QUESTION_META.read_text(encoding="utf-8"))
		fields = {row["fieldname"]: row for row in metadata["fields"]}
		status_options = set(fields["status"]["options"].splitlines())
		for status in (
			"Draft",
			"Under Review",
			"Under Subject Review",
			"Changes Requested",
			"Recommended",
			"Approved",
			"Retired",
		):
			self.assertIn(status, status_options)
		for fieldname in ("recommended_by", "recommended_on", "review_feedback", "reviewed_by", "reviewed_on"):
			self.assertIn(fieldname, fields)
			self.assertEqual(fields[fieldname].get("read_only"), 1)

	def test_governance_resolves_simple_and_standard_targets(self):
		source = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		for expected in (
			'"Under Subject Review" if mode == "Standard" else "Under Review"',
			'status in {"Under Subject Review", "Under Review"}',
			'return status == ("Recommended" if mode == "Standard" else "Under Review")',
			'"Changes Requested"',
			'"Recommended"',
		):
			self.assertIn(expected, source)

	def test_school_actions_require_scoped_responsibility_assignments(self):
		source = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		for expected in (
			'not responsibilities.get("can_author")',
			'not responsibilities.get("can_subject_review")',
			'not responsibilities.get("can_final_approve")',
			"active Question Author assignment",
			"active Subject Reviewer assignment",
			"active Final Approver assignment",
			"Institution, Branch, and Subject / Course",
		):
			self.assertIn(expected, source)
		self.assertNotIn("GLOBAL_SCOPE_ROLES.intersection", source)

	def test_request_changes_requires_feedback_and_recommendation_is_audited(self):
		source = (APP / "cbt/question_governance.py").read_text(encoding="utf-8")
		for expected in (
			'"requires_feedback": True',
			"if action_state.get(\"requires_feedback\") and not clean_feedback",
			"Enter the changes required",
			"doc.review_feedback = clean_feedback",
			"doc.recommended_by = frappe.session.user",
			"doc.recommended_on = now_datetime()",
		):
			self.assertIn(expected, source)

	def test_builder_locks_review_stages_and_exposes_scoped_actions(self):
		api = (APP / "api/question_builder.py").read_text(encoding="utf-8")
		bundle = (APP / "public/js/eduedge_question_builder.bundle.js").read_text(encoding="utf-8")
		for expected in (
			'EDITABLE_STATUSES = {"Draft", "Changes Requested"}',
			"status not in EDITABLE_STATUSES",
			"Question content can be changed only while the question is Draft or Changes Requested",
			'"recommended_by": doc.recommended_by or ""',
			'"review_feedback": doc.review_feedback or ""',
		):
			self.assertIn(expected, api)
		for expected in (
			"Policy-driven workflow",
			"Subject review note",
			'\"request_changes\"',
			'\"recommend\"',
			"Final Approver: ${allowed ? \"Assigned\" : \"Not assigned\"}",
			"Latest review feedback",
		):
			self.assertIn(expected, bundle)

	def test_question_bank_exposes_all_governance_status_filters(self):
		source = (APP / "api/question_bank.py").read_text(encoding="utf-8")
		for status in (
			'"Under Subject Review"',
			'"Changes Requested"',
			'"Recommended"',
		):
			self.assertIn(status, source)


if __name__ == "__main__":
	unittest.main()
