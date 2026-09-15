from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from eduedge.education.result_engine import (
	build_component_plan_maximum_blockers,
	build_configured_class_metrics,
	compose_cumulative_subject_results,
	compose_terminal_subject_results,
)


def _profile() -> dict:
	return {
		"name": "TEST-PROFILE",
		"score_precision": 2,
		"grading_scale": None,
		"overall_calculation_method": "Average of Subject Percentages",
		"annual_aggregation_method": "Equal Average of Eligible Terms",
		"minimum_eligible_periods": 1,
		"missing_result_policy": "Block Publication",
		"absence_policy": "Block Publication",
		"components": [
			{
				"component_key": "ca",
				"component_label": "Continuous Assessment",
				"target_maximum_score": 40,
				"required": True,
				"sequence": 10,
				"show_on_terminal": True,
				"show_on_annual": True,
			},
			{
				"component_key": "exam",
				"component_label": "Examination",
				"target_maximum_score": 60,
				"required": True,
				"sequence": 20,
				"show_on_terminal": True,
				"show_on_annual": True,
			},
		],
		"component_sources": [
			{
				"component_key": "ca",
				"assessment_group": "CA",
				"sequence": 10,
				"leaf_assessment_groups": ["CA"],
			},
			{
				"component_key": "exam",
				"assessment_group": "EXAM",
				"sequence": 20,
				"leaf_assessment_groups": ["EXAM"],
			},
		],
		"metrics": [],
	}


def _row(term: str, group: str, score: float, maximum: float, *, course: str = "CRS", state: str = "Scored"):
	return {
		"academic_term": term,
		"assessment_group": group,
		"course": course,
		"total_score": score,
		"maximum_score": maximum,
		"grading_scale": None,
		"eduedge_score_state": state,
	}


class TestEduEdgeResultEngine(FrappeTestCase):
	def test_component_target_maximum_blocks_mismatched_native_plans(self):
		valid = build_component_plan_maximum_blockers(
			_profile(),
			[
				{"academic_term": "Alpha", "assessment_group": "CA", "course": "CRS", "maximum_assessment_score": 20},
				{"academic_term": "Alpha", "assessment_group": "CA", "course": "CRS", "maximum_assessment_score": 20},
				{"academic_term": "Alpha", "assessment_group": "EXAM", "course": "CRS", "maximum_assessment_score": 60},
			],
		)
		self.assertEqual(valid, [])

		blocked = build_component_plan_maximum_blockers(
			_profile(),
			[
				{"academic_term": "Alpha", "assessment_group": "CA", "course": "CRS", "maximum_assessment_score": 50},
				{"academic_term": "Alpha", "assessment_group": "EXAM", "course": "CRS", "maximum_assessment_score": 60},
			],
		)
		self.assertEqual(len(blocked), 1)
		self.assertEqual(blocked[0]["code"], "COMPONENT_MAXIMUM_MISMATCH")
		self.assertEqual(blocked[0]["component_key"], "ca")
		self.assertEqual(blocked[0]["expected_maximum"], 40)
		self.assertEqual(blocked[0]["configured_maximum"], 50)

	def test_terminal_composition_uses_native_component_rows(self):
		payload = compose_terminal_subject_results(
			_profile(),
			[
				_row("Alpha", "CA", 30, 40),
				_row("Alpha", "EXAM", 47, 60),
			],
		)
		self.assertFalse(payload["blockers"])
		self.assertEqual(len(payload["subjects"]), 1)
		subject = payload["subjects"][0]
		self.assertEqual(subject["total_score"], 77)
		self.assertEqual(subject["maximum_score"], 100)
		self.assertEqual(subject["percentage"], 77)
		self.assertEqual(
			[(row["component_key"], row["score"]) for row in subject["components"]],
			[("ca", 30), ("exam", 47)],
		)

	def test_yearly_result_matches_three_period_equal_average_example(self):
		periods = [
			{"academic_term": "Alpha", "display_label": "Alpha", "sequence": 10, "weight": 0},
			{"academic_term": "Rapha", "display_label": "Rapha", "sequence": 20, "weight": 0},
			{"academic_term": "Omega", "display_label": "Omega", "sequence": 30, "weight": 0},
		]
		payload = compose_cumulative_subject_results(
			_profile(),
			[
				_row("Alpha", "CA", 30, 40),
				_row("Alpha", "EXAM", 47, 60),
				_row("Rapha", "CA", 33, 40),
				_row("Rapha", "EXAM", 41, 60),
				_row("Omega", "CA", 36, 40),
				_row("Omega", "EXAM", 39, 60),
			],
			periods,
		)
		self.assertFalse(payload["blockers"])
		subject = payload["subjects"][0]
		self.assertEqual(subject["cumulative_score"], 226)
		self.assertEqual(subject["cumulative_maximum_score"], 300)
		self.assertEqual(subject["annual_percentage"], 75.33)
		self.assertEqual(payload["summary"]["overall_percentage"], 75.33)

	def test_not_offered_period_is_excluded_not_converted_to_zero(self):
		periods = [
			{"academic_term": "Alpha", "display_label": "Alpha", "sequence": 10, "weight": 0},
			{"academic_term": "Rapha", "display_label": "Rapha", "sequence": 20, "weight": 0},
			{"academic_term": "Omega", "display_label": "Omega", "sequence": 30, "weight": 0},
		]
		payload = compose_cumulative_subject_results(
			_profile(),
			[
				_row("Alpha", "CA", 35, 40, course="CCA"),
				_row("Alpha", "EXAM", 50, 60, course="CCA"),
				_row("Rapha", "CA", 31, 40, course="CCA"),
				_row("Rapha", "EXAM", 47, 60, course="CCA"),
				_row("Omega", "CA", 0, 40, course="CCA", state="Not Offered"),
				_row("Omega", "EXAM", 0, 60, course="CCA", state="Not Offered"),
			],
			periods,
		)
		self.assertFalse(payload["blockers"])
		subject = payload["subjects"][0]
		self.assertEqual(subject["eligible_period_count"], 2)
		self.assertEqual(subject["cumulative_score"], 163)
		self.assertEqual(subject["cumulative_maximum_score"], 200)
		self.assertEqual(subject["annual_percentage"], 81.5)

	def test_class_statistics_label_and_representation_are_profile_driven(self):
		profile = _profile()
		profile["metrics"] = [
			{
				"metric_key": "Class Average",
				"display_label": "Average %",
				"calculation_basis": "Annual Average Percentage",
				"display_as": "Percentage",
				"decimal_places": 2,
				"sequence": 10,
				"show_on_terminal": False,
				"show_on_annual": True,
			}
		]
		metrics = build_configured_class_metrics(
			profile,
			[
				{"annual_percentage": 75.33, "eligible": True},
				{"annual_percentage": 81.50, "eligible": True},
			],
			result_mode="Annual",
		)
		self.assertEqual(len(metrics), 1)
		self.assertEqual(metrics[0]["display_label"], "Average %")
		self.assertEqual(metrics[0]["display_value"], "78.42%")


if __name__ == "__main__":
	import unittest

	unittest.main()
