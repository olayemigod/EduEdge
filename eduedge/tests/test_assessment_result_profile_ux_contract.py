from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAssessmentResultProfileUXContract(unittest.TestCase):
	def test_assessment_operations_exposes_profile_and_mode(self):
		vue = (APP / "public" / "js" / "eduedge_assessment_operations" / "EduEdgeAssessmentOperations.vue").read_text()
		for text in (
			"Result Mode",
			"Result Profile",
			"Annual / Cumulative",
			"Manage result profiles",
			"Create correction version",
			"profile_blockers",
			"unmapped_assessment_groups",
		):
			self.assertIn(text, vue)
		self.assertIn("result_profile: this.filters.result_profile || undefined", vue)
		self.assertIn('result_mode: this.filters.result_mode || "Terminal"', vue)
		self.assertIn("create_result_publication_revision", vue)

	def test_annual_mode_does_not_require_legacy_assessment_group(self):
		vue = (APP / "public" / "js" / "eduedge_assessment_operations" / "EduEdgeAssessmentOperations.vue").read_text()
		self.assertIn('this.filters.result_profile || (', vue)
		self.assertIn('this.filters.result_mode !== "Annual" && this.filters.assessment_group', vue)
		self.assertIn('v-if="!filters.result_profile && filters.result_mode !== \'Annual\'"', vue)
		self.assertIn('if (this.filters.result_mode === "Annual") this.filters.academic_term = "";', vue)

	def test_snapshot_contains_grading_legend_not_only_scale_name(self):
		service = (APP / "education" / "result_snapshots.py").read_text()
		self.assertIn('"grading_legend": _grading_legend(config)', service)
		self.assertIn("def _grading_legend", service)
		self.assertIn('"grade_code"', service)
		self.assertIn('"threshold"', service)
		self.assertIn("eduedge_report_remark", service)


if __name__ == "__main__":
	unittest.main()
