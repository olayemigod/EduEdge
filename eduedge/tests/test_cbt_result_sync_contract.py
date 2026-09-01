from __future__ import annotations

import json
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTResultSyncContract(unittest.TestCase):
	def _meta(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_schedule_requires_a_governed_assessment_plan_mapping(self):
		meta = self._meta("eduedge_cbt_exam_schedule", "eduedge_cbt_exam_schedule.json")
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"assessment_plan",
			"maximum_assessment_score",
		):
			self.assertIn(fieldname, fields)
		self.assertEqual(fields["assessment_plan"].get("options"), "Assessment Plan")
		self.assertEqual(fields["student_group"].get("read_only"), 1)

		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.py"
		).read_text()
		for token in (
			"_validate_assessment_plan(template)",
			'plan.docstatus != 1',
			'plan.get(BRANCH_FIELD) != self.school_branch',
			'plan.course != self.course',
			'plan.student_group != self.student_group',
			'len(criteria) != 1',
			'Assessment Plan maximum score and its single criterion must equal',
			'"assessment_plan"',
		):
			self.assertIn(token, controller)

	def test_candidate_assignments_use_the_locked_schedule_class(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_candidate_assignment"
			/ "eduedge_cbt_candidate_assignment.py"
		).read_text()
		self.assertIn('"student_group",', controller)
		self.assertIn("self.student_group = schedule.student_group", controller)
		self.assertIn("locked on the examination schedule", controller)
		self.assertNotIn('template = frappe.db.get_value(\n\t\t\t"EduEdge CBT Exam Template"', controller)

	def test_assessment_results_gain_unique_traceable_cbt_source_links(self):
		fields = (APP / "cbt" / "result_sync_fields.py").read_text()
		for token in (
			'"Assessment Result"',
			'"eduedge_cbt_result"',
			'"options": "EduEdge CBT Result"',
			'"unique": 1',
			'"eduedge_cbt_exam_schedule"',
			"create_custom_fields",
		):
			self.assertIn(token, fields)
		install = (APP / "install.py").read_text()
		self.assertEqual(install.count("ensure_result_sync_custom_fields()"), 2)

	def test_cbt_result_tracks_draft_and_submitted_academic_records(self):
		meta = self._meta("eduedge_cbt_result", "eduedge_cbt_result.json")
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"assessment_plan",
			"assessment_result",
			"assessment_result_status",
			"assessment_result_prepared_by",
			"assessment_result_prepared_on",
			"assessment_result_submitted_by",
			"assessment_result_submitted_on",
		):
			self.assertIn(fieldname, fields)
		self.assertIn("Draft Prepared", fields["assessment_result_status"]["options"])
		self.assertIn("Submitted", fields["assessment_result_status"]["options"])

	def test_sync_service_is_school_only_approval_gated_and_two_step(self):
		service = (APP / "cbt" / "result_sync.py").read_text()
		for token in (
			'if schedule.exam_scope != SCHOOL_EXAM',
			"Public examination results remain with the central signed-result service",
			'if schedule.status != "Completed"',
			"assert_result_approval_ready(schedule.name)",
			'if row.result_status != "Approved"',
			"def prepare_schedule_assessment_results",
			"def submit_schedule_assessment_results",
			'"doctype": "Assessment Result"',
			'"eduedge_cbt_result": cbt_result.name',
			"assessment_result.submit()",
		):
			self.assertIn(token, service)

	def test_sync_is_idempotent_and_never_overwrites_unrelated_or_changed_results(self):
		service = (APP / "cbt" / "result_sync.py").read_text()
		for token in (
			"_find_existing_assessment_result",
			'"docstatus": ["!=", 2]',
			"was not prepared from the selected CBT Result",
			"score differs from the approved CBT Result",
			"EduEdge will not overwrite it",
			'if assessment_result.docstatus == 1',
			"existing_submitted.append",
		):
			self.assertIn(token, service)
		for forbidden in (
			"cancel()",
			"frappe.delete_doc",
			"EduEdge Result Publication",
			"publish_results",
			"Sales Invoice",
			"Payment Entry",
		):
			self.assertNotIn(forbidden, service)

	def test_sync_audit_is_append_only_service_controlled_and_branch_safe(self):
		meta = self._meta(
			"eduedge_cbt_result_sync_log",
			"eduedge_cbt_result_sync_log.json",
		)
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"cbt_result",
			"assessment_result",
			"exam_schedule",
			"school_branch",
			"student",
			"assessment_plan",
			"action",
			"score_snapshot",
			"acted_by",
			"acted_on",
		):
			self.assertIn(fieldname, fields)
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_result_sync_log"
			/ "eduedge_cbt_result_sync_log.py"
		).read_text()
		self.assertIn("in_cbt_result_sync_service", controller)
		self.assertIn("append-only audit records and cannot be deleted", controller)
		permissions = (APP / "cbt" / "permissions.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn("cbt_result_sync_log_query", permissions)
		self.assertIn(
			'"EduEdge CBT Result Sync Log": "eduedge.cbt.permissions.cbt_result_sync_log_query"',
			hooks,
		)
		self.assertIn(
			'"EduEdge CBT Result Sync Log": "eduedge.cbt.permissions.has_school_branch_permission"',
			hooks,
		)

	def test_schedule_ui_filters_plans_and_exposes_explicit_prepare_and_submit_actions(self):
		script = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.js"
		).read_text()
		for token in (
			'frm.set_query("assessment_plan"',
			"filters.eduedge_school_branch",
			"filters.student_group",
			"filters.course",
			"Prepare Assessment Result Drafts",
			"Submit Prepared Assessment Results",
			"prepare_schedule_assessment_results",
			"submit_schedule_assessment_results",
		):
			self.assertIn(token, script)

	def test_general_settings_and_public_result_boundary_remain_unchanged(self):
		settings = self._meta("eduedge_settings", "eduedge_settings.json")
		fieldnames = {field["fieldname"] for field in settings["fields"]}
		for forbidden in (
			"cbt_result_sync_enabled",
			"cbt_assessment_plan",
			"auto_publish_cbt_results",
			"public_exam_result_sync",
		):
			self.assertNotIn(forbidden, fieldnames)
		service = (APP / "cbt" / "result_sync.py").read_text()
		self.assertNotIn("CoreEdge Public Result", service)
		self.assertNotIn("public_candidate_reference", service)


if __name__ == "__main__":
	unittest.main()
