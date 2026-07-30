from __future__ import annotations

import json
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = APP / "eduedge" / "doctype"


class TestCBTAttemptReviewContract(unittest.TestCase):
	def _meta(self, folder: str, filename: str) -> dict:
		return json.loads((DOCTYPE_ROOT / folder / filename).read_text())

	def test_review_schema_is_append_only_and_restricted(self):
		meta = self._meta("eduedge_cbt_attempt_review", "eduedge_cbt_attempt_review.json")
		fields = {field["fieldname"]: field for field in meta["fields"]}
		for fieldname in (
			"attempt",
			"exam_schedule",
			"school_branch",
			"candidate_assignment",
			"candidate_name",
			"attempt_status_before",
			"reported_pending_sync_count",
			"review_reasons_snapshot",
			"intervention_count",
			"decision",
			"decision_note",
			"attempt_status_after",
			"requires_review_after",
			"decided_by",
			"decided_on",
		):
			self.assertIn(fieldname, fields)
		self.assertIn("Accept for Scoring", fields["decision"]["options"])
		self.assertIn("Keep Flagged", fields["decision"]["options"])
		self.assertIn("Disqualify Candidate", fields["decision"]["options"])
		roles = {row["role"] for row in meta["permissions"]}
		for forbidden in ("Student", "EduEdge Parent", "CBT Invigilator", "Teacher", "Instructor", "Education Manager"):
			self.assertNotIn(forbidden, roles)

	def test_review_controller_blocks_direct_changes_and_deletion(self):
		controller = (
			DOCTYPE_ROOT
			/ "eduedge_cbt_attempt_review"
			/ "eduedge_cbt_attempt_review.py"
		).read_text()
		for token in (
			"in_cbt_attempt_review_service",
			"governed review service",
			"append-only and cannot be deleted",
		):
			self.assertIn(token, controller)

	def test_review_service_has_guarded_outcomes_and_never_reads_answers(self):
		service = (APP / "cbt" / "attempt_review.py").read_text()
		for token in (
			"REVIEW_DECISIONS",
			"Accept for Scoring",
			"Keep Flagged",
			"Disqualify Candidate",
			"Decision Note is required for every CBT Attempt review",
			"Pending browser answers must be resolved before accepting",
			"A CBT Result already exists",
			'status_after = "Auto Submitted" if attempt.attempt_status == "Timed Out"',
			'"assignment_status",\n\t\t\t"Disqualified"',
			'"doctype": "EduEdge CBT Attempt Review"',
		):
			self.assertIn(token, service)
		for forbidden in (
			"EduEdge CBT Attempt Answer",
			"EduEdge CBT Attempt Scoring Key",
			"answer_payload_json",
			"correct_option_ids_json",
			"answer_key",
			"marking_guide",
		):
			self.assertNotIn(forbidden, service)

	def test_acceptance_clears_review_disqualification_resolves_assignment_and_keep_flagged_does_not_clear(self):
		service = (APP / "cbt" / "attempt_review.py").read_text()
		self.assertIn('requires_review_after = 0', service)
		self.assertIn('status_after = "Cancelled"', service)
		self.assertIn('requires_review_after = 1', service)
		self.assertIn('"requires_review": requires_review_after', service)
		self.assertIn('"review_reasons": _append_resolution_reason', service)

	def test_permissions_and_hooks_register_review_branch_isolation(self):
		permissions = (APP / "cbt" / "permissions.py").read_text()
		hooks = (APP / "hooks.py").read_text()
		self.assertIn('"EduEdge CBT Attempt Review"', permissions)
		self.assertIn("cbt_attempt_review_query", permissions)
		self.assertIn(
			'"EduEdge CBT Attempt Review": "eduedge.cbt.permissions.cbt_attempt_review_query"',
			hooks,
		)
		self.assertIn(
			'"EduEdge CBT Attempt Review": "eduedge.cbt.permissions.has_school_branch_permission"',
			hooks,
		)

	def test_review_workbench_uses_collision_free_edgesuite_page(self):
		page_root = APP / "eduedge" / "page" / "eduedge_cbt_review_workbench"
		loader = (page_root / "eduedge_cbt_review_workbench.js").read_text()
		page_meta = json.loads((page_root / "eduedge_cbt_review_workbench.json").read_text())
		component = (
			APP
			/ "public"
			/ "js"
			/ "eduedge_cbt_attempt_review"
			/ "EduEdgeCBTAttemptReview.vue"
		).read_text()
		self.assertEqual(page_meta["name"], "eduedge-cbt-review-workbench")
		self.assertNotEqual(page_meta["name"], "eduedge-cbt-attempt-review")
		for token in (
			"edgesuite_ui.bundle.js",
			"eduedge_cbt_attempt_review.bundle.js",
			"createEduEdgeCBTAttemptReviewApp",
			"eduedge-cbt-review-workbench",
		):
			self.assertIn(token, loader)
		for token in (
			"get_attempt_review_queue",
			"resolve_attempt_review",
			"Accept for Scoring",
			"Keep Flagged",
			"Disqualify Candidate",
			"Decision Note",
			"Review Reasons",
			"Intervention Record",
			"Previous Review Decision",
		):
			self.assertIn(token, component)
		for forbidden in (
			"answer_payload_json",
			"correct_option_ids_json",
			"answer_key",
			"marking_guide",
			"candidate_answer",
		):
			self.assertNotIn(forbidden, component)

	def test_access_manifest_and_menus_register_review_resource_and_workbench(self):
		access = (APP / "access_control.py").read_text()
		navigation = (APP / "public" / "js" / "eduedge_ui" / "navigation.js").read_text()
		product_menu = (APP / "public" / "js" / "eduedge_product_menu.bundle.js").read_text()
		workspace = (APP / "eduedge" / "workspace" / "eduedge" / "eduedge.json").read_text()
		self.assertIn('"cbt_attempt_review": "EduEdge CBT Attempt Review"', access)
		self.assertIn('route: "/app/eduedge-cbt-review-workbench"', navigation)
		self.assertIn('"/app/eduedge-cbt-review-workbench"', navigation)
		self.assertIn('"/app/eduedge-cbt-review-workbench"', product_menu)
		self.assertIn('resource: "cbt_attempt_review"', product_menu)
		self.assertIn('"link_to":"eduedge-cbt-review-workbench"', workspace)


if __name__ == "__main__":
	unittest.main()
