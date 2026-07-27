from __future__ import annotations

import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


class TestCBTExamScheduleContract(unittest.TestCase):
	def test_schedule_doctype_owns_sitting_specific_controls(self):
		path = APP / "eduedge" / "doctype" / "eduedge_cbt_exam_schedule" / "eduedge_cbt_exam_schedule.json"
		meta = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"exam_template",
			"scheduled_start",
			"scheduled_end",
			"require_candidate_check_in",
			"candidate_start_mode",
			"allow_late_entry",
			"late_entry_grace_minutes",
			"allow_invigilator_time_extension",
			"maximum_time_extension_minutes",
			"allow_invigilator_force_submit",
		):
			self.assertIn(fieldname, fields)
		self.assertTrue(fields["scheduled_end"].get("read_only"))
		self.assertTrue(fields["device_change_policy"].get("read_only"))
		self.assertTrue(fields["attempt_review_policy"].get("read_only"))

	def test_template_owns_reusable_integrity_policies(self):
		path = APP / "eduedge" / "doctype" / "eduedge_cbt_exam_template" / "eduedge_cbt_exam_template.json"
		meta = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in meta["fields"]}
		self.assertEqual(fields["device_change_policy"]["fieldtype"], "Select")
		self.assertEqual(fields["attempt_review_policy"]["fieldtype"], "Select")
		self.assertNotIn("pending_sync", " ".join(fields))

	def test_runtime_enforces_snapshot_and_immutability(self):
		controller = (
			APP
			/ "eduedge"
			/ "doctype"
			/ "eduedge_cbt_exam_schedule"
			/ "eduedge_cbt_exam_schedule.py"
		).read_text()
		for token in (
			"Select an Approved CBT Exam Template",
			"SNAPSHOT_FIELDS",
			"scheduled_end",
			"ALLOWED_STATUS_TRANSITIONS",
			"An activated examination schedule is immutable",
			"require_public_exam_authoring",
			"assert_branch_access",
		):
			self.assertIn(token, controller)

	def test_branch_permissions_cover_schedules(self):
		hooks = (APP / "hooks.py").read_text()
		permissions = (APP / "cbt" / "permissions.py").read_text()
		self.assertIn('"EduEdge CBT Exam Schedule": "eduedge.cbt.permissions.cbt_exam_schedule_query"', hooks)
		self.assertIn('"EduEdge CBT Exam Schedule": "eduedge.cbt.permissions.has_school_branch_permission"', hooks)
		self.assertIn('"EduEdge CBT Exam Schedule"', permissions)

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
