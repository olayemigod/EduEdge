from __future__ import annotations

import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


class TestCBTExamScheduleContract(unittest.TestCase):
	def test_schedule_owns_sitting_and_academic_context(self):
		path = APP / "eduedge" / "doctype" / "eduedge_cbt_exam_schedule" / "eduedge_cbt_exam_schedule.json"
		meta = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"exam_template",
			"school_branch",
			"course",
			"student_group",
			"academic_year",
			"academic_term",
			"program",
			"assessment_group",
			"scheduled_start",
			"scheduled_end",
			"require_candidate_check_in",
			"candidate_start_mode",
			"allow_late_entry",
			"late_entry_grace_minutes",
			"allow_invigilator_time_extension",
			"maximum_time_extension_minutes",
			"allow_invigilator_force_submit",
			"status_change_reason",
		):
			self.assertIn(fieldname, fields)
		self.assertTrue(fields["scheduled_end"].get("read_only"))
		self.assertTrue(fields["device_change_policy"].get("read_only"))
		self.assertTrue(fields["attempt_review_policy"].get("read_only"))
		self.assertIn("Fixed Question Set", fields["exam_template"].get("description", ""))

	def test_template_owns_reusable_integrity_policies(self):
		path = APP / "eduedge" / "doctype" / "eduedge_cbt_exam_template" / "eduedge_cbt_exam_template.json"
		meta = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		self.assertEqual(fields["device_change_policy"]["fieldtype"], "Select")
		self.assertEqual(fields["attempt_review_policy"]["fieldtype"], "Select")
		self.assertNotIn("pending_sync", " ".join(fields))

	def test_runtime_enforces_snapshot_readiness_and_immutability(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.py"
		).read_text()
		governance = (APP / "cbt" / "schedule_governance.py").read_text()
		for token in (
			"Select an Approved CBT Exam Template",
			"SNAPSHOT_FIELDS",
			"scheduled_end",
			"ALLOWED_STATUS_TRANSITIONS",
			"PROTECTED_AFTER_CANDIDATE_CONFIRMATION",
			"Policy Blueprint scheduling is disabled",
			"require_public_exam_authoring",
			"assert_branch_access",
			"write_lifecycle_log",
		):
			self.assertIn(token, controller)
		for token in (
			"validate_activation_readiness",
			"Examination Centre capacity",
			"_assert_no_schedule_overlap",
			"_assert_no_candidate_overlap",
		):
			self.assertIn(token, governance)

	def test_branch_permissions_cover_schedules_and_lifecycle(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "cbt" / "permissions.py").read_text()
		self.assertIn('"EduEdge CBT Exam Schedule": "eduedge.cbt.permissions.cbt_exam_schedule_query"', hooks)
		self.assertIn('"EduEdge CBT Lifecycle Log": "eduedge.cbt.permissions.cbt_lifecycle_log_query"', hooks)
		self.assertIn('"EduEdge CBT Exam Schedule"', permissions)
		self.assertIn('"EduEdge CBT Lifecycle Log"', permissions)

	def test_general_settings_are_not_expanded_with_exam_specific_controls(self):
		settings_path = APP / "eduedge" / "doctype" / "eduedge_settings" / "eduedge_settings.json"
		settings = settings_path.read_text()
		for token in (
			"candidate_start_mode",
			"late_entry_grace_minutes",
			"maximum_time_extension_minutes",
			"allow_invigilator_force_submit",
		):
			self.assertNotIn(token, settings)


if __name__ == "__main__":
	unittest.main()
