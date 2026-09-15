from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "eduedge"


class TestAnnualResultEngineContract(unittest.TestCase):
	def test_result_period_labels_and_weights_are_institution_calendar_specific(self):
		path = APP / "eduedge" / "doctype" / "eduedge_academic_calendar_period" / "eduedge_academic_calendar_period.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertIn("report_label", fields)
		self.assertIn("annual_result_weight", fields)
		self.assertIn("include_in_result_aggregation", fields)
		custom_fields = (APP / "education" / "result_fields.py").read_text()
		self.assertNotIn('"Academic Term": [', custom_fields)

	def test_result_components_can_be_required_or_optional(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_component" / "eduedge_result_component.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertIn("required", fields)
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('component["required"]', engine)
		self.assertIn('component["excluded_count"] == 0', engine)

	def test_annual_engine_preserves_period_components_and_supports_missing_not_offered(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("compose_cumulative_subject_results", engine)
		self.assertIn('"periods": []', engine)
		self.assertIn('"components": term_subject["components"]', engine)
		self.assertIn('state in {"Exempt", "Not Offered"}', engine)
		self.assertIn("eligible_period_count", engine)
		self.assertIn("minimum_eligible_periods", engine)

	def test_annual_calculation_supports_equal_weighted_and_raw_cumulative(self):
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn('method == "Equal Average of Eligible Terms"', engine)
		self.assertIn('method == "Weighted Average"', engine)
		self.assertIn('method == "Raw Cumulative"', engine)
		self.assertIn("Missing Annual Result Weight", engine)
		self.assertIn("cumulative_percentage", engine)
		self.assertIn("annual_percentage", engine)

	def test_overall_percentage_policy_is_explicit(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_profile" / "eduedge_result_profile.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(
			fields["overall_calculation_method"]["options"],
			"Average of Subject Percentages\nAggregate Score Percentage",
		)
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("calculate_overall_summary", engine)
		self.assertIn("sum_subject_percentages", engine)

	def test_chs_cls_cas_remain_generic_metric_configuration(self):
		path = APP / "eduedge" / "doctype" / "eduedge_result_metric" / "eduedge_result_metric.json"
		payload = json.loads(path.read_text())
		fields = {field["fieldname"]: field for field in payload["fields"]}
		self.assertEqual(fields["metric_key"]["options"], "Class Highest\nClass Lowest\nClass Average")
		self.assertIn("Annual Cumulative Raw Score", fields["calculation_basis"]["options"])
		self.assertIn("Annual Average Percentage", fields["calculation_basis"]["options"])
		raw = path.read_text()
		for fixed_label in ('"CHS"', '"CLS"', '"CAS"'):
			self.assertNotIn(fixed_label, raw)
		engine = (APP / "education" / "result_engine.py").read_text()
		self.assertIn("build_configured_class_metrics", engine)

	def test_annual_publication_uses_sessional_student_group_and_calendar_periods(self):
		service = (APP / "education" / "assessment_operations.py").read_text()
		self.assertIn('result_mode == "Annual"', service)
		self.assertIn("TERM_BOUND_ANNUAL_COHORT", service)
		self.assertIn("get_result_periods", service)
		self.assertIn('plan_filters["academic_term"] = [', service)
		self.assertIn("compose_cumulative_subject_results", service)
		self.assertNotIn("ANNUAL_COHORT_PENDING", service)


if __name__ == "__main__":
	unittest.main()
