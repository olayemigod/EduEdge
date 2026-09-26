from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from eduedge.education.result_engine import (
	build_component_plan_maximum_blockers,
	build_configured_class_metrics,
	build_missing_result_blockers,
	calculate_overall_summary,
	compose_cumulative_subject_results,
	compose_terminal_subject_results,
)
from eduedge.education.result_profile import (
	_validate_calculation_settings,
	_validate_metrics,
	resolve_promotion_pass_average,
)
from eduedge.education.profiled_report_cards import _suggested_progression
from eduedge.education.result_snapshots import build_publication_approval_fingerprint


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

	def test_missing_component_can_be_excluded_without_hiding_whole_subject(self):
		profile = _profile()
		profile["missing_result_policy"] = "Exclude from Denominator"
		payload = compose_terminal_subject_results(
			profile,
			[
				_row("Alpha", "CA", 30, 40),
			],
		)
		self.assertFalse(payload["blockers"])
		subject = payload["subjects"][0]
		self.assertEqual(subject["total_score"], 30)
		self.assertEqual(subject["maximum_score"], 40)
		self.assertEqual(subject["percentage"], 75)

		plans = [
			{"name": "PLAN-CA", "course": "CRS"},
			{"name": "PLAN-EXAM", "course": "CRS"},
		]
		partial_rows = [
			{"assessment_plan": "PLAN-CA", "student": "STU-1", "docstatus": 1},
		]
		self.assertEqual(
			build_missing_result_blockers(profile, plans, partial_rows, ["STU-1"]),
			[],
		)

		blockers = build_missing_result_blockers(profile, plans, [], ["STU-1"])
		self.assertEqual(len(blockers), 1)
		self.assertEqual(blockers[0]["code"], "MISSING_SUBJECT_RESULTS")
		self.assertEqual(blockers[0]["student"], "STU-1")
		self.assertEqual(blockers[0]["course"], "CRS")

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

	def test_approval_fingerprint_ignores_cosmetic_identity_but_tracks_academic_payload(self):
		publication = frappe._dict({"name": "PUB-1"})
		base_payload = {
			"STU-1": {
				"student": {"student_name": "Student One", "image": "/private/a.png"},
				"source_result_names": ["RES-1"],
				"payload": {
					"student": {"student_name": "Student One", "image": "/private/a.png"},
					"profile": {"presentation": {"show_attendance": 1}},
					"result": {"summary": {"overall_percentage": 72.5}},
					"attendance": {"present": 42, "absent": 3},
					"source_assessment_results": ["RES-1"],
				},
			}
		}
		with patch(
			"eduedge.education.result_snapshots.build_publication_student_payloads",
			return_value=base_payload,
		):
			first = build_publication_approval_fingerprint(publication)

		cosmetic = {
			"STU-1": {
				"student": {"student_name": "Renamed Student", "image": "/private/b.png"},
				"source_result_names": ["RES-1"],
				"payload": {
					"student": {"student_name": "Renamed Student", "image": "/private/b.png"},
					"profile": {"presentation": {"show_attendance": 1}},
					"result": {"summary": {"overall_percentage": 72.5}},
					"attendance": {"present": 42, "absent": 3},
					"source_assessment_results": ["RES-1"],
				},
			}
		}
		with patch(
			"eduedge.education.result_snapshots.build_publication_student_payloads",
			return_value=cosmetic,
		):
			second = build_publication_approval_fingerprint(publication)
		self.assertEqual(first, second)

		changed = {
			"STU-1": {
				"student": {"student_name": "Student One", "image": "/private/a.png"},
				"source_result_names": ["RES-1"],
				"payload": {
					"student": {"student_name": "Student One", "image": "/private/a.png"},
					"profile": {"presentation": {"show_attendance": 1}},
					"result": {"summary": {"overall_percentage": 73.5}},
					"attendance": {"present": 42, "absent": 3},
					"source_assessment_results": ["RES-1"],
				},
			}
		}
		with patch(
			"eduedge.education.result_snapshots.build_publication_student_payloads",
			return_value=changed,
		):
			third = build_publication_approval_fingerprint(publication)
		self.assertNotEqual(first["hash"], third["hash"])
		self.assertEqual(first["student_count"], 1)

		hidden_attendance_a = {
			"STU-1": {
				"student": {"student_name": "Student One"},
				"source_result_names": ["RES-1"],
				"payload": {
					"profile": {"presentation": {"show_attendance": 0}},
					"result": {"summary": {"overall_percentage": 72.5}},
					"attendance": {"present": 42, "absent": 3},
					"source_assessment_results": ["RES-1"],
				},
			}
		}
		hidden_attendance_b = {
			"STU-1": {
				"student": {"student_name": "Student One"},
				"source_result_names": ["RES-1"],
				"payload": {
					"profile": {"presentation": {"show_attendance": 0}},
					"result": {"summary": {"overall_percentage": 72.5}},
					"attendance": {"present": 10, "absent": 35},
					"source_assessment_results": ["RES-1"],
				},
			}
		}
		with patch(
			"eduedge.education.result_snapshots.build_publication_student_payloads",
			return_value=hidden_attendance_a,
		):
			hidden_first = build_publication_approval_fingerprint(publication)
		with patch(
			"eduedge.education.result_snapshots.build_publication_student_payloads",
			return_value=hidden_attendance_b,
		):
			hidden_second = build_publication_approval_fingerprint(publication)
		self.assertEqual(hidden_first, hidden_second)

	def test_promotion_threshold_is_profile_scoped_and_freezable(self):
		inherited = frappe._dict(
			{
				"use_custom_promotion_pass_average": 0,
				"promotion_pass_average": 50,
			}
		)
		with patch(
			"eduedge.education.result_profile.frappe.get_single",
			return_value=frappe._dict({"promotion_pass_average": 55}),
		):
			self.assertEqual(
				resolve_promotion_pass_average(inherited),
				(55.0, "EduEdge Settings"),
			)

		custom = frappe._dict(
			{
				"use_custom_promotion_pass_average": 1,
				"promotion_pass_average": 60,
			}
		)
		with patch("eduedge.education.result_profile.frappe.get_single") as settings_mock:
			self.assertEqual(
				resolve_promotion_pass_average(custom),
				(60.0, "Result Profile"),
			)
			settings_mock.assert_not_called()

		with patch("eduedge.education.profiled_report_cards.frappe.get_single") as settings_mock:
			self.assertEqual(
				_suggested_progression(
					"Annual",
					55,
					True,
					{"promotion_pass_average": 60},
				),
				"Repeat",
			)
			settings_mock.assert_not_called()

		with patch(
			"eduedge.education.profiled_report_cards.frappe.get_single",
			return_value=frappe._dict({"promotion_pass_average": 50}),
		):
			self.assertEqual(
				_suggested_progression("Annual", 55, True, {}),
				"Promote",
			)

	def test_custom_promotion_threshold_must_be_a_percentage(self):
		doc = frappe._dict(
			{
				"overall_calculation_method": "Average of Subject Percentages",
				"annual_aggregation_method": "Equal Average of Eligible Terms",
				"missing_result_policy": "Block Publication",
				"absence_policy": "Block Publication",
				"minimum_eligible_periods": 1,
				"score_precision": 2,
				"use_custom_promotion_pass_average": 1,
				"promotion_pass_average": 101,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			_validate_calculation_settings(doc)

	def test_overall_grade_uses_same_rounded_percentage_shown_to_user(self):
		config = _profile()
		config["score_precision"] = 0
		config["grading_scale"] = "TEST-SCALE"
		subjects = [
			{"eligible": True, "total_score": 49.6, "maximum_score": 100, "percentage": 49.6},
		]
		with (
			patch("eduedge.education.result_engine.get_grade", return_value="P") as grade_mock,
			patch("eduedge.education.result_engine.get_grade_remark", return_value="Pass") as remark_mock,
		):
			summary = calculate_overall_summary(subjects, config)
		self.assertEqual(summary["overall_percentage"], 50)
		grade_mock.assert_called_once_with("TEST-SCALE", 50)
		remark_mock.assert_called_once_with("TEST-SCALE", 50)
		self.assertEqual(summary["overall_grade"], "P")
		self.assertEqual(summary["overall_remark"], "Pass")

	def test_zero_score_precision_is_preserved(self):
		profile = _profile()
		profile["score_precision"] = 0
		payload = compose_terminal_subject_results(
			profile,
			[
				_row("Alpha", "CA", 30.4, 40),
				_row("Alpha", "EXAM", 47.6, 60),
			],
		)
		subject = payload["subjects"][0]
		self.assertEqual(subject["total_score"], 78)
		self.assertEqual(subject["percentage"], 78)
		self.assertEqual(
			[(row["component_key"], row["score"]) for row in subject["components"]],
			[("ca", 30), ("exam", 48)],
		)
		self.assertEqual(payload["summary"]["overall_percentage"], 78)

	def test_metric_basis_must_match_selected_report_surface(self):
		invalid_terminal = frappe._dict(
			metrics=[
				frappe._dict(
					metric_key="Class Average",
					display_label="Annual Average",
					calculation_basis="Annual Average Percentage",
					display_as="Percentage",
					decimal_places=2,
					show_on_terminal=1,
					show_on_annual=0,
				)
			]
		)
		with self.assertRaises(frappe.ValidationError):
			_validate_metrics(invalid_terminal)

		invalid_annual = frappe._dict(
			metrics=[
				frappe._dict(
					metric_key="Class Highest",
					display_label="Current Term Highest",
					calculation_basis="Current Term Percentage",
					display_as="Percentage",
					decimal_places=2,
					show_on_terminal=0,
					show_on_annual=1,
				)
			]
		)
		with self.assertRaises(frappe.ValidationError):
			_validate_metrics(invalid_annual)

		valid_both = frappe._dict(
			metrics=[
				frappe._dict(
					metric_key="Class Average",
					display_label="Cumulative Average",
					calculation_basis="Year-to-Date Cumulative Percentage",
					display_as="Percentage",
					decimal_places=2,
					show_on_terminal=1,
					show_on_annual=1,
				)
			]
		)
		_validate_metrics(valid_both)

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
