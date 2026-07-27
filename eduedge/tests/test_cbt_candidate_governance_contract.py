from __future__ import annotations

import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTCandidateGovernanceContract(unittest.TestCase):
	def _load(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_candidate_assignment_is_schedule_and_branch_aware(self):
		meta = self._load(
			"eduedge_cbt_candidate_assignment",
			"eduedge_cbt_candidate_assignment.json",
		)
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"exam_schedule",
			"exam_template",
			"exam_scope",
			"school_branch",
			"student",
			"public_candidate_reference",
			"student_group",
			"approved_extra_time_minutes",
			"access_start",
			"access_end",
			"assignment_status",
		):
			self.assertIn(fieldname, fields)
		self.assertTrue(fields["school_branch"].get("read_only"))
		self.assertTrue(fields["access_end"].get("read_only"))

	def test_assignment_controller_enforces_eligibility_and_identity_lock(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_candidate_assignment"
			/ "eduedge_cbt_candidate_assignment.py"
		).read_text()
		for token in (
			"Student Group Student",
			"New candidates can be assigned only",
			"require_public_exam_capability",
			"This candidate is already assigned",
			"An eligible candidate assignment is immutable",
			"Candidate check-in has not opened",
		):
			self.assertIn(token, controller)

	def test_intervention_log_is_append_only_and_always_reviewable(self):
		meta = self._load(
			"eduedge_cbt_intervention_log",
			"eduedge_cbt_intervention_log.json",
		)
		fields = {field["fieldname"]: field for field in meta["fields"]}
		self.assertEqual(fields["requires_attempt_review"].get("default"), "1")
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_intervention_log"
			/ "eduedge_cbt_intervention_log.py"
		).read_text()
		for token in (
			"append-only and cannot be edited",
			"append-only and cannot be deleted",
			"A reason is required for every CBT intervention",
			"maximum permitted by the Examination Schedule",
			"Force Submission is not permitted",
		):
			self.assertIn(token, controller)

	def test_general_settings_remain_free_of_candidate_and_intervention_policies(self):
		settings = (
			DOCTYPE_ROOT / "eduedge_settings" / "eduedge_settings.json"
		).read_text()
		for token in (
			"approved_extra_time_minutes",
			"candidate_start_mode",
			"intervention_type",
			"requires_attempt_review",
		):
			self.assertNotIn(token, settings)


if __name__ == "__main__":
	unittest.main()
