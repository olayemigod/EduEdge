from __future__ import annotations

import json
import unittest
from pathlib import Path


APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTScheduleAuditHardeningContract(unittest.TestCase):
	def test_schedule_operations_are_serialised_and_internal_routes_are_sealed(self):
		wrapper = (APP / "api" / "cbt_schedule_operations.py").read_text(encoding="utf-8")
		hooks = (APP / "hooks.py").read_text(encoding="utf-8")
		for token in (
			"schedule_operation_lock",
			"controlled_cbt_operation",
			"withdraw_non_started_candidates_for_cancellation",
			"frappe.get_doc(SCHEDULE_DOCTYPE, schedule, for_update=True)",
			'payload.pop("approved_extra_time_minutes", None)',
			"Schedule management permission is required to search Invigilators",
		):
			self.assertIn(token, wrapper)
		for method in (
			"get_context",
			"get_schedule",
			"get_candidate",
			"get_template_context",
			"save_schedule",
			"set_schedule_status",
			"save_candidate",
			"set_candidate_status",
			"assign_template_student_group",
			"record_intervention",
			"search_options",
		):
			self.assertIn(
				f'"eduedge.api.cbt_schedule_operations_hardened.{method}": '
				f'"eduedge.api.cbt_schedule_operations.{method}"',
				hooks,
			)

	def test_schedule_controller_blocks_direct_status_and_audit_deletion(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.py"
		).read_text(encoding="utf-8")
		for token in (
			"eduedge_controlled_status_action",
			"Change Schedule status only through the controlled CBT Schedule Operations lifecycle actions",
			"validate_terminal_schedule_readiness",
			"delete_cbt_exam_schedule",
			"Only a Draft examination schedule with no audit history can be deleted",
			"EduEdge CBT Intervention Log",
			"EduEdge CBT Lifecycle Log",
			"_validate_program_scope",
		):
			self.assertIn(token, controller)

	def test_candidate_controller_blocks_direct_status_extra_time_and_audit_deletion(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_candidate_assignment"
			/ "eduedge_cbt_candidate_assignment.py"
		).read_text(encoding="utf-8")
		for token in (
			"eduedge_controlled_status_action",
			"Change Candidate status only through controlled CBT lifecycle actions",
			"Initial extra time cannot be entered directly",
			"Approved Extra Time can change only through an Applied Time Extension intervention",
			"delete_cbt_candidate_assignment",
			"Only a Draft Candidate Assignment with no audit history can be deleted",
			"for_update=True",
		):
			self.assertIn(token, controller)

	def test_intervention_controller_is_controlled_and_does_not_reopen_expired_access(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_intervention_log"
			/ "eduedge_cbt_intervention_log.py"
		).read_text(encoding="utf-8")
		for token in (
			"eduedge_controlled_intervention",
			"Record CBT interventions only through the controlled Schedule Operations action",
			"Candidate access has already closed",
			"requires_attempt_review = 0 if self.intervention_type == \"Time Extension\" else 1",
			"record_cbt_intervention",
		):
			self.assertIn(token, controller)

	def test_terminal_candidate_and_schedule_rules_are_server_authoritative(self):
		governance = (APP / "cbt" / "schedule_governance.py").read_text(encoding="utf-8")
		for token in (
			"filelock",
			"schedule_operation_lock",
			"validate_terminal_schedule_readiness",
			"withdraw_non_started_candidates_for_cancellation",
			"Checked In or Released candidates",
			"Resolve all open Candidate Assignments",
			"At least one candidate must be Completed",
			"At least one non-terminal candidate is required",
		):
			self.assertIn(token, governance)

	def test_native_schema_cannot_import_or_directly_edit_governed_fields(self):
		schedule = json.loads(
			(
				DOCTYPE_ROOT
				/ "eduedge_cbt_exam_schedule"
				/ "eduedge_cbt_exam_schedule.json"
			).read_text(encoding="utf-8")
		)
		candidate = json.loads(
			(
				DOCTYPE_ROOT
				/ "eduedge_cbt_candidate_assignment"
				/ "eduedge_cbt_candidate_assignment.json"
			).read_text(encoding="utf-8")
		)
		self.assertEqual(schedule.get("allow_import"), 0)
		self.assertEqual(candidate.get("allow_import"), 0)
		schedule_fields = {row["fieldname"]: row for row in schedule["fields"]}
		candidate_fields = {row["fieldname"]: row for row in candidate["fields"]}
		self.assertEqual(schedule_fields["status"].get("read_only"), 1)
		self.assertEqual(candidate_fields["assignment_status"].get("read_only"), 1)
		self.assertEqual(candidate_fields["approved_extra_time_minutes"].get("read_only"), 1)

	def test_edgesuite_runtime_removes_direct_extra_time_and_explains_terminal_actions(self):
		bundle = (APP / "public" / "js" / "eduedge_cbt_schedules.bundle.js").read_text(
			encoding="utf-8"
		)
		for token in (
			'field.fieldname !== "approved_extra_time_minutes"',
			"delete values.approved_extra_time_minutes",
			"Extra time is granted only through an audited Time Extension intervention",
			"Draft and Eligible candidates will be withdrawn",
			"Every candidate must already be Completed, Withdrawn or Disqualified",
		):
			self.assertIn(token, bundle)

	def test_unique_index_patch_uses_supported_frappe_aggregate_syntax(self):
		patch = (
			APP / "patches" / "v0_8" / "add_cbt_candidate_assignment_unique_indexes.py"
		).read_text(encoding="utf-8")
		self.assertIn('{"COUNT": "name", "as": "total"}', patch)
		self.assertNotIn('"count(name) as total"', patch)


if __name__ == "__main__":
	unittest.main()
