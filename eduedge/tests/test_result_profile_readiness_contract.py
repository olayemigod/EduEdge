from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestResultProfileReadinessContract(unittest.TestCase):
	def test_profile_aware_readiness_uses_recursive_component_sources(self):
		text = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn("result_profile: str | None = None", text)
		self.assertIn("get_result_profile_config", text)
		self.assertIn('plan_filters["assessment_group"] = ["in", assessment_groups', text)
		self.assertIn("compose_terminal_subject_results", text)
		self.assertIn("profile_blockers", text)
		self.assertIn("unmapped_assessment_groups", text)

	def test_legacy_readiness_still_uses_existing_assessment_group_when_no_profile(self):
		text = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn('plan_filters["assessment_group"] = assessment_group', text)
		self.assertIn('"result_profile": result_profile', text)
		self.assertIn('"result_mode": result_mode', text)

	def test_annual_mode_uses_sessional_cohort_and_calendar_period_resolver(self):
		text = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn('result_mode == "Annual"', text)
		self.assertIn("TERM_BOUND_ANNUAL_COHORT", text)
		self.assertIn("get_result_periods", text)
		self.assertIn("compose_cumulative_subject_results", text)
		self.assertNotIn("ANNUAL_COHORT_PENDING", text)
		self.assertIn("not all_blockers", text)

	def test_publication_api_accepts_profile_and_mode_but_keeps_defaults(self):
		text = (APP / "api" / "assessment_operations.py").read_text()
		self.assertIn("result_profile: str | None = None", text)
		self.assertIn('result_mode: str = "Terminal"', text)
		self.assertIn('"result_profile": result_profile', text)
		self.assertIn('"result_mode": result_mode or "Terminal"', text)
		self.assertIn('result_profile=doc.get("result_profile")', text)

	def test_profile_readiness_enforces_component_maxima_and_required_courses(self):
		readiness = (APP / "education" / "assessment_operations.py").read_text()
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("build_component_plan_maximum_blockers", readiness)
		self.assertIn("COMPONENT_MAXIMUM_MISMATCH", engine)
		self.assertIn("target_maximum_score", engine)
		self.assertIn("def _build_required_course_plan_blockers", readiness)
		self.assertIn('"parenttype": "Program"', readiness)
		self.assertIn('"required": 1', readiness)
		self.assertIn("REQUIRED_PROGRAM_COURSE_MISSING", readiness)
		self.assertIn('group.get("group_based_on") == "Course"', readiness)


if __name__ == "__main__":
	unittest.main()
