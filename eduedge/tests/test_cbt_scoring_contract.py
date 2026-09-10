from __future__ import annotations

import json
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTScoringContract(unittest.TestCase):
	def _meta(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_result_schema_is_attempt_unique_service_controlled_and_not_candidate_visible(self):
		meta = self._meta("eduedge_cbt_result", "eduedge_cbt_result.json")
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"attempt",
			"exam_schedule",
			"school_branch",
			"candidate_assignment",
			"candidate_name",
			"result_status",
			"objective_marks_awarded",
			"manual_marks_awarded",
			"total_awarded_marks",
			"percentage",
			"pass_percentage",
			"outcome",
			"manual_pending_count",
			"items",
			"approved_by",
			"approved_on",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["attempt"].get("unique"), 1)
		self.assertEqual(fields["items"].get("options"), "EduEdge CBT Result Item")
		roles = {row["role"] for row in meta["permissions"]}
		for forbidden in ("Student", "EduEdge Parent", "CBT Invigilator", "Teacher", "Instructor"):
			self.assertNotIn(forbidden, roles)
		write_roles = {row["role"] for row in meta["permissions"] if row.get("write")}
		self.assertIn("Academic Administrator", write_roles)
		self.assertIn("Education Manager", write_roles)

	def test_result_and_marking_log_block_direct_mutation_and_deletion(self):
		result_controller = (
			DOCTYPE_ROOT / "eduedge_cbt_result" / "eduedge_cbt_result.py"
		).read_text()
		log_controller = (
			DOCTYPE_ROOT / "eduedge_cbt_marking_log" / "eduedge_cbt_marking_log.py"
		).read_text()
		for token in (
			"in_cbt_result_service",
			"governed scoring and marking services",
			"immutable audit records and cannot be deleted",
		):
			self.assertIn(token, result_controller)
		for token in (
			"in_cbt_result_service",
			"governed marking service",
			"append-only and cannot be deleted",
		):
			self.assertIn(token, log_controller)

	def test_marking_audit_excludes_ordinary_teachers_and_instructors(self):
		meta = self._meta("eduedge_cbt_marking_log", "eduedge_cbt_marking_log.json")
		roles = {row["role"] for row in meta["permissions"]}
		for forbidden in ("Student", "EduEdge Parent", "CBT Invigilator", "Teacher", "Instructor"):
			self.assertNotIn(forbidden, roles)
		self.assertIn("Education Manager", roles)

	def test_objective_scoring_is_exact_match_negative_policy_and_idempotent(self):
		service = (APP / "cbt" / "scoring.py").read_text()
		for token in (
			"selected == correct",
			'Disable Negative Marking',
			"return -abs(flt(scoring_key.negative_mark))",
			"partial multiple-choice credit is deliberately excluded",
			'frappe.db.get_value("EduEdge CBT Result", {"attempt": attempt.name}, "name")',
			"SCHEDULE_SCORING_STATUSES",
			"The protected scoring-key snapshot is incomplete",
		):
			self.assertIn(token, service)
		existing_index = service.index('existing = frappe.db.get_value("EduEdge CBT Result"')
		status_index = service.index("if attempt.attempt_status not in SCOREABLE_ATTEMPT_STATUSES")
		self.assertLess(existing_index, status_index)

	def test_manual_queue_only_exposes_unmarked_questions_to_authorised_roles(self):
		service = (APP / "cbt" / "scoring.py").read_text()
		marker_block = service.split("MARKER_ROLES =", 1)[1].split("APPROVER_ROLES", 1)[0]
		self.assertNotIn('"Teacher"', marker_block)
		self.assertNotIn('"Instructor"', marker_block)
		self.assertIn('filters = {"result_status": "Manual Marking Required"}', service)
		self.assertIn('item.marking_status != "Manual Required"', service)
		self.assertIn("candidate_answer", service)
		self.assertIn("answer_key", service)
		self.assertIn("marking_guide", service)

	def test_manual_mark_is_bounded_audited_and_requires_comment_for_revision(self):
		service = (APP / "cbt" / "scoring.py").read_text()
		for token in (
			"Awarded Mark must be between 0 and {0}",
			"Marker Comment is required when revising a completed manual mark",
			'"doctype": "EduEdge CBT Marking Log"',
			'"previous_mark": previous_mark',
			'"new_mark": new_mark',
			'"attempt_status",\n\t\t"Under Review" if result.manual_pending_count else "Scored"',
		):
			self.assertIn(token, service)

	def test_approval_calls_server_readiness_and_does_not_publish_academic_results(self):
		service = (APP / "cbt" / "scoring.py").read_text()
		self.assertIn("assert_result_approval_ready(exam_schedule)", service)
		self.assertIn('result.result_status = "Approved"', service)
		for forbidden in (
			"Assessment Result",
			"EduEdge Result Publication",
			"Payment Entry",
			"Sales Invoice",
		):
			self.assertNotIn(forbidden, service)

	def test_permissions_route_result_items_through_parent_result(self):
		permissions = (APP / "cbt" / "permissions.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		for token in (
			"cbt_result_query",
			"cbt_result_item_query",
			"cbt_marking_log_query",
			"has_result_reference_permission",
			"_result_reference_condition",
		):
			self.assertIn(token, permissions)
		for token in (
			'"EduEdge CBT Result": "eduedge.cbt.permissions.cbt_result_query"',
			'"EduEdge CBT Result Item": "eduedge.cbt.permissions.cbt_result_item_query"',
			'"EduEdge CBT Marking Log": "eduedge.cbt.permissions.cbt_marking_log_query"',
			'"EduEdge CBT Result Item": "eduedge.cbt.permissions.has_result_reference_permission"',
		):
			self.assertIn(token, hooks)

	def test_marking_workspace_is_permission_aware_and_never_publishes(self):
		loader = (
			APP / "eduedge" / "page" / "eduedge_cbt_marking" / "eduedge_cbt_marking.js"
		).read_text()
		component = (
			APP / "public" / "js" / "eduedge_cbt_marking" / "EduEdgeCBTMarking.vue"
		).read_text()
		access = (APP / "access_control.py").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		for token in (
			"edgesuite_ui.bundle.js",
			"eduedge_cbt_marking.bundle.js",
			"createEduEdgeCBTMarkingApp",
		):
			self.assertIn(token, loader)
		for token in (
			"score_schedule_objective",
			"get_manual_marking_queue",
			"apply_manual_mark",
			"approve_schedule_results",
			"Approval does not publish or create Frappe Assessment Results",
			"Publication remains a separate governed step",
		):
			self.assertIn(token, component)
		self.assertIn('"cbt_result": "EduEdge CBT Result"', access)
		self.assertIn('"/app/eduedge-cbt-marking"', access)
		self.assertIn('route: "/app/eduedge-cbt-marking"', navigation)
		self.assertIn('resource: "cbt_result"', product_menu)
		self.assertIn('permissions: ["write"]', product_menu)


if __name__ == "__main__":
	unittest.main()
