from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAnnualResultProgressionEvidenceContract(unittest.TestCase):
	def test_result_publication_handoff_is_optional_but_server_validated_when_supplied(self):
		api = (APP / "api" / "student_progression.py").read_text()
		self.assertIn("def _approved_annual_result_evidence(", api)
		self.assertIn("if not publication_name:", api)
		self.assertIn('publication.status != "Published"', api)
		self.assertIn('publication.result_mode != "Annual"', api)
		self.assertIn("publication.school_branch != source_branch", api)
		self.assertIn("publication.academic_year != source.academic_year", api)
		self.assertIn("group.program != source.program", api)

	def test_progression_requires_immutable_snapshot_and_approved_review(self):
		api = (APP / "api" / "student_progression.py").read_text()
		self.assertIn('"EduEdge Published Result Snapshot"', api)
		self.assertIn("get_snapshot_payload", api)
		self.assertIn('"EduEdge Report Card Review"', api)
		self.assertIn('review.progression_status != "Approved"', api)
		self.assertIn("review.progression_recommendation != outcome", api)
		self.assertIn('"snapshot_hash": snapshot.payload_hash', api)
		self.assertIn('"approved_review": review.name', api)
		self.assertIn('"overall_percentage": result_summary.get("overall_percentage")', api)

	def test_preview_carries_approved_result_into_progression_evidence(self):
		api = (APP / "api" / "student_progression.py").read_text()
		self.assertIn('result_publication = str(data.get("result_publication")', api)
		self.assertIn("_approved_annual_result_evidence(result_publication, source, outcome)", api)
		self.assertIn('evidence["approved_annual_result"] = approved_annual_result', api)
		self.assertIn('"result_publication": result_publication', api)

	def test_target_enrollment_keeps_evidence_and_finalization_revalidates_it(self):
		api = (APP / "api" / "student_progression.py").read_text()
		self.assertIn('doc.set(PROGRESSION_EVIDENCE_FIELD, json.dumps(plan.get("evidence") or {}, sort_keys=True))', api)
		self.assertIn('stored_annual = stored_evidence.get("approved_annual_result") or {}', api)
		self.assertIn("publication_to_validate = result_publication or stored_publication", api)
		self.assertIn('stored_evidence["approved_annual_result"] = _approved_annual_result_evidence(', api)
		self.assertIn('"evidence_snapshot": json.dumps(stored_evidence, sort_keys=True)', api)

	def test_direct_outcomes_also_preserve_validated_result_evidence(self):
		api = (APP / "api" / "student_progression.py").read_text()
		self.assertIn("def _finalize_direct_outcome(", api)
		self.assertIn("result_publication: str | None = None", api)
		self.assertIn('"evidence_snapshot": json.dumps(evidence, sort_keys=True)', api)

	def test_result_handoff_never_auto_submits_or_creates_progression(self):
		api = (APP / "api" / "student_progression.py").read_text()
		vue = (APP / "public" / "js" / "eduedge_student_progression" / "EduEdgeStudentProgression.vue").read_text()
		self.assertIn("result_publication: this.resultHandoff?.result_publication || undefined", vue)
		self.assertIn("Preview revalidates every selected Student", vue)
		self.assertIn("creates destination Enrollment drafts only", vue)
		self.assertNotIn("doc.submit()", api)

	def test_report_card_handoff_requires_approved_annual_review(self):
		vue = (APP / "public" / "js" / "eduedge_report_cards" / "EduEdgeReportCards.vue").read_text()
		self.assertIn('this.selectedStudent?.result_mode === "Annual"', vue)
		self.assertIn('this.selectedStudent?.review?.progression_status === "Approved"', vue)
		self.assertIn("Continue to Student Progression", vue)
		self.assertIn("result_publication", vue)


if __name__ == "__main__":
	unittest.main()
