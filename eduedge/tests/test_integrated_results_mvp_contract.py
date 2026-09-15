from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestIntegratedResultsMVPContract(unittest.TestCase):
	def test_single_academic_truth_path_is_preserved(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		mark_entry = (APP / "api" / "mark_entry.py").read_text()
		snapshots = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn("Assessment Result", mark_entry)
		self.assertIn("compose_terminal_subject_results", engine)
		self.assertIn("compose_cumulative_subject_results", engine)
		self.assertIn("source_assessment_results", snapshots)
		self.assertNotIn("EduEdge Term Result", mark_entry + engine + snapshots)

	def test_all_mvp_result_surfaces_are_present(self):
		required = (
			APP / "api" / "mark_entry.py",
			APP / "api" / "results_portal.py",
			APP / "api" / "result_broadsheet.py",
			APP / "api" / "result_intelligence.py",
			APP / "education" / "result_snapshots.py",
			APP / "education" / "report_card_issues.py",
			APP / "education" / "result_verification.py",
			APP / "www" / "eduedge-results.py",
			APP / "www" / "eduedge-result-verify.py",
		)
		for path in required:
			self.assertTrue(path.exists(), str(path))

	def test_published_consumers_do_not_fall_back_to_live_assessment_result_data(self):
		for path in (
			APP / "api" / "result_broadsheet.py",
			APP / "api" / "result_intelligence.py",
			APP / "api" / "results_portal.py",
		):
			text = path.read_text()
			self.assertNotIn('"Assessment Result"', text, str(path))
		self.assertNotIn("'Assessment Result'", text, str(path))

	def test_student_guardian_portal_consumes_only_effective_issued_result(self):
		portal = (APP / "api" / "results_portal.py").read_text()
		self.assertIn("get_effective_issued_payload", portal)
		self.assertIn('"Student Guardian"', portal)
		self.assertIn('"Guardian"', portal)
		self.assertIn("You are not linked to this Student.", portal)

	def test_broadsheet_and_intelligence_read_immutable_snapshots(self):
		for filename in ("result_broadsheet.py", "result_intelligence.py"):
			text = (APP / "api" / filename).read_text()
			self.assertIn("EduEdge Published Result Snapshot", text)
			self.assertIn("EduEdge Result Publication", text)

	def test_official_report_governance_is_versioned_and_verifiable(self):
		issues = (APP / "education" / "report_card_issues.py").read_text()
		verify = (APP / "education" / "result_verification.py").read_text()
		self.assertIn("_next_issue_version", issues)
		self.assertIn("supersedes_issue", issues)
		self.assertIn("verification_token", issues)
		self.assertIn("hmac.compare_digest", verify)
		self.assertIn("payload_hash", verify)

	def test_chs_cls_cas_are_never_required_fixed_columns(self):
		metric = (APP / "eduedge" / "doctype" / "eduedge_result_metric" / "eduedge_result_metric.json").read_text()
		template = (APP / "templates" / "report_card.html").read_text()
		self.assertIn("Class Highest", metric)
		self.assertIn("Class Lowest", metric)
		self.assertIn("Class Average", metric)
		for fixed in ('"CHS"', '"CLS"', '"CAS"'):
			self.assertNotIn(fixed, metric)
		self.assertIn("summary.display_metrics", template)

	def test_progression_is_a_governed_handoff_not_result_engine_mutation(self):
		report_cards = (APP / "education" / "report_cards.py").read_text()
		progression = (APP / "education" / "progression.py").read_text()
		self.assertIn("progression", progression.lower())
		self.assertNotIn('db_set("Program Enrollment"', report_cards)
		self.assertNotIn('set_value("Program Enrollment"', report_cards)


if __name__ == "__main__":
	unittest.main()
