from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultsSecurityHardeningContract(unittest.TestCase):
	def test_result_records_use_instructor_aware_permission_hooks(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "education" / "permissions.py").read_text()
		for doctype, handler in (
			("EduEdge Result Publication", "has_result_publication_permission"),
			("EduEdge Published Result Snapshot", "has_published_result_snapshot_permission"),
			("EduEdge Report Card Review", "has_report_card_review_permission"),
			("EduEdge Report Card Issue", "has_report_card_issue_permission"),
		):
			self.assertIn(f'"{doctype}"', hooks)
			self.assertIn(handler, hooks)
		self.assertIn("def _governed_result_query", permissions)
		self.assertIn("def _owned_student_group_condition", permissions)
		self.assertIn("schedule.student_group", permissions)
		self.assertIn("schedule.instructor", permissions)

	def test_report_card_service_rejects_unassigned_teacher_class(self):
		service = (APP / "education" / "report_cards.py").read_text()
		self.assertIn("is_limited_instructor_user", service)
		self.assertIn("get_user_instructor_names", service)
		self.assertIn("def _assert_publication_operator_scope", service)
		self.assertIn("You are not assigned to this Student Group / Class.", service)
		self.assertNotIn("if write and not roles.intersection(OPERATIONAL_ROLES)", service)

	def test_teacher_has_no_raw_snapshot_or_issue_payload_permission(self):
		for relative in (
			"eduedge/doctype/eduedge_published_result_snapshot/eduedge_published_result_snapshot.json",
			"eduedge/doctype/eduedge_report_card_issue/eduedge_report_card_issue.json",
		):
			payload = json.loads((APP / relative).read_text())
			roles = {row.get("role") for row in payload.get("permissions") or []}
			self.assertNotIn("Teacher", roles)
			self.assertNotIn("Instructor", roles)

	def test_publication_and_review_transitions_lock_source_rows(self):
		assessment_api = (APP / "api" / "assessment_operations.py").read_text()
		report_api = (APP / "api" / "report_cards.py").read_text()
		self.assertIn("for_update=True", assessment_api)
		self.assertIn("where name=%s for update", assessment_api)
		self.assertIn("def _get_review_for_update", report_api)
		self.assertIn("where name=%s for update", report_api)

	def test_corrections_cannot_branch_from_stale_published_version(self):
		assessment_api = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("A newer published result version exists.", assessment_api)
		self.assertIn("next_version = int(source.publication_version or 1) + 1", assessment_api)

	def test_database_uniqueness_guards_snapshot_and_issue_versions(self):
		patches = (APP / "patches.txt").read_text()
		patch = (APP / "patches" / "v1_0" / "add_result_record_unique_constraints.py").read_text()
		self.assertIn("add_result_record_unique_constraints", patches)
		self.assertIn('"EduEdge Published Result Snapshot"', patch)
		self.assertIn('["result_publication", "student"]', patch)
		self.assertIn('"EduEdge Report Card Issue"', patch)
		self.assertIn('["result_publication", "student", "issue_version"]', patch)
		self.assertIn("frappe.db.add_unique", patch)
		self.assertIn("def _constraint_exists", patch)
		self.assertIn("if not _constraint_exists(doctype, constraint_name)", patch)
		self.assertIn("Resolve the duplicate records before migration.", patch)


if __name__ == "__main__":
	unittest.main()
