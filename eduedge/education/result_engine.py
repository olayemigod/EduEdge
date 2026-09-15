from __future__ import annotations

from collections import defaultdict
from statistics import mean

import frappe
from frappe import _
from frappe.utils import cint, flt

from education.education.api import get_grade

from eduedge.education.result_profile import get_component_source_index, get_result_profile_config

SCORE_STATES = {"Scored", "Absent", "Exempt", "Not Offered"}

BASIS_VALUE_FIELDS = {
	"Current Term Raw Score": "total_score",
	"Current Term Percentage": "percentage",
	"Year-to-Date Cumulative Raw Score": "cumulative_score",
	"Annual Cumulative Raw Score": "cumulative_score",
	"Annual Average Percentage": "annual_average_percentage",
}


def compose_terminal_subject_results(profile: str, result_rows: list) -> dict:
	"""Compose submitted native Assessment Results into report-level subject components.

	The function deliberately does not create a second marks ledger. Native Frappe
	Education Assessment Result remains the academic source of truth.
	"""
	config = get_result_profile_config(profile)
	source_index = get_component_source_index(config)
	component_config = {row["component_key"]: row for row in config["components"]}
	precision = cint(config.get("score_precision") or 2)

	subjects: dict[str, dict] = {}
	blockers: list[dict] = []
	unmapped: set[str] = set()

	for row in result_rows:
		assessment_group = _value(row, "assessment_group")
		component_key = source_index.get(assessment_group)
		if not component_key:
			if assessment_group:
				unmapped.add(assessment_group)
			continue

		course = _value(row, "course") or _("Unspecified Course")
		subject = subjects.setdefault(
			course,
			{
				"course": course,
				"components": {
					key: {
						"component_key": key,
						"component_label": component["component_label"],
						"score": 0.0,
						"maximum_score": 0.0,
						"assessment_count": 0,
						"sequence": component["sequence"],
					}
					for key, component in component_config.items()
				},
				"total_score": 0.0,
				"maximum_score": 0.0,
				"percentage": 0.0,
				"grade": "",
				"remark": "",
				"grading_scale": "",
			},
		)

		state = _value(row, "eduedge_score_state") or "Scored"
		if state not in SCORE_STATES:
			state = "Scored"
		if state in {"Exempt", "Not Offered"}:
			continue
		if state == "Absent":
			if config["absence_policy"] == "Block Publication":
				blockers.append(
					{"course": course, "assessment_group": assessment_group, "reason": "Absent"}
				)
				continue
			if config["absence_policy"] == "Exclude from Denominator":
				continue

		component = subject["components"][component_key]
		maximum_score = flt(_value(row, "maximum_score"))
		score = 0.0 if state == "Absent" else flt(_value(row, "total_score"))
		component["score"] += score
		component["maximum_score"] += maximum_score
		component["assessment_count"] += 1
		subject["total_score"] += score
		subject["maximum_score"] += maximum_score
		if _value(row, "grading_scale"):
			subject["grading_scale"] = _value(row, "grading_scale")

	for subject in subjects.values():
		missing_components = [
			key
			for key, component in subject["components"].items()
			if component["assessment_count"] == 0
		]
		if missing_components and config["missing_result_policy"] == "Block Publication":
			for component_key in missing_components:
				blockers.append(
					{
						"course": subject["course"],
						"component_key": component_key,
						"reason": "Missing Component",
					}
				)

		subject["total_score"] = round(subject["total_score"], precision)
		subject["maximum_score"] = round(subject["maximum_score"], precision)
		subject["percentage"] = round(
			subject["total_score"] / subject["maximum_score"] * 100,
			precision,
		) if subject["maximum_score"] else 0.0

		grading_scale = config.get("grading_scale") or subject.get("grading_scale")
		if grading_scale and subject["maximum_score"]:
			subject["grade"] = get_grade(grading_scale, subject["percentage"])
			subject["remark"] = get_grade_remark(grading_scale, subject["percentage"])

		subject["components"] = sorted(
			subject["components"].values(),
			key=lambda row: (row["sequence"], row["component_key"]),
		)
		for component in subject["components"]:
			component["score"] = round(component["score"], precision)
			component["maximum_score"] = round(component["maximum_score"], precision)

	return {
		"profile": config,
		"subjects": sorted(subjects.values(), key=lambda row: row["course"]),
		"blockers": blockers,
		"unmapped_assessment_groups": sorted(unmapped),
	}


def calculate_class_statistics(subject_rows: list[dict], calculation_basis: str) -> dict:
	"""Return generic cohort statistics; labels such as CHS/CLS/CAS belong to Result Profile."""
	fieldname = BASIS_VALUE_FIELDS.get(calculation_basis)
	if not fieldname:
		frappe.throw(_("Unsupported statistics calculation basis."), frappe.ValidationError)
	values = [
		flt(row.get(fieldname))
		for row in subject_rows
		if row.get(fieldname) is not None and row.get("eligible", True)
	]
	if not values:
		return {"count": 0, "highest": None, "lowest": None, "average": None}
	return {
		"count": len(values),
		"highest": max(values),
		"lowest": min(values),
		"average": mean(values),
	}


def format_metric_value(value, display_as: str, decimal_places: int = 2):
	if value is None:
		return None
	precision = max(0, min(cint(decimal_places), 6))
	if display_as == "Percentage":
		return f"{flt(value):.{precision}f}%"
	if display_as == "Number":
		return str(int(round(flt(value))))
	if display_as == "Raw Score":
		return f"{flt(value):.{precision}f}"
	return str(value)


def get_grade_remark(grading_scale: str, percentage: float) -> str:
	if not grading_scale:
		return ""
	intervals = frappe.get_all(
		"Grading Scale Interval",
		filters={"parent": grading_scale},
		fields=["threshold", "eduedge_report_remark"],
		order_by="threshold desc",
	)
	for interval in intervals:
		if flt(percentage) >= flt(interval.threshold):
			return interval.eduedge_report_remark or ""
	return ""


def _value(row, fieldname: str):
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)
