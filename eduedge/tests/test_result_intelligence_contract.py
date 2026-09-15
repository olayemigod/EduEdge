from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultIntelligenceContract(unittest.TestCase):
	def test_intelligence_reads_immutable_snapshots_not_live_assessment_results(self):
		api = (APP / "api" / "result_intelligence.py").read_text()
		self.assertIn('"EduEdge Published Result Snapshot"', api)
		self.assertIn('"EduEdge Result Publication"', api)
		self.assertNotIn('"Assessment Result"', api)

	def test_latest_publication_version_wins_per_scope(self):
		api = (APP / "api" / "result_intelligence.py").read_text()
		self.assertIn("publication_version", api)
		self.assertIn("latest[key]", api)
		self.assertIn(">= int(existing.publication_version", api)

	def test_dashboard_has_actionable_subject_student_and_trend_views(self):
		api = (APP / "api" / "result_intelligence.py").read_text()
		for key in ("subject_performance", "student_performance", "weak_subjects", "grade_distribution", "publication_trend"):
			self.assertIn(f'"{key}"', api)

	def test_pass_rate_is_not_inferred_without_explicit_policy(self):
		api = (APP / "api" / "result_intelligence.py").read_text()
		self.assertIn("Pass rate is intentionally not inferred", api)
		self.assertNotIn('"pass_rate":', api)

	def test_intelligence_is_branch_scoped_and_management_role_gated(self):
		api = (APP / "api" / "result_intelligence.py").read_text()
		self.assertIn("assert_branch_access", api)
		self.assertIn("INTELLIGENCE_ROLES", api)
		self.assertIn("You are not permitted to view Result Intelligence.", api)

	def test_page_is_edgesuite_action_oriented(self):
		vue = (APP / "public" / "js" / "eduedge_result_intelligence" / "EduEdgeResultIntelligence.vue").read_text()
		self.assertIn("Weakest Subjects by Published Average", vue)
		self.assertIn("Below Cohort Average", vue)
		self.assertIn("Subject Performance", vue)
		self.assertIn("Published Student Performance", vue)
		self.assertIn("/app/eduedge-report-cards", vue)


if __name__ == "__main__":
	unittest.main()
