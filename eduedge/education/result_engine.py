from __future__ import annotations

from collections import defaultdict
from statistics import mean

import frappe
from frappe import _
from frappe.utils import cint, flt

from education.education.api import get_grade

from eduedge.education.result_profile import get_component_source_index, get_result_profile_config
from eduedge.services.academic_calendar import get_enabled_institution_calendar

SCORE_STATES = {"Scored", "Absent", "Exempt", "Not Offered"}

BASIS_VALUE_FIELDS = {
	"Current Term Raw Score": "total_score",
	"Current Term Percentage": "percentage",
	"Year-to-Date Cumulative Raw Score": "cumulative_score",
	"Year-to-Date Cumulative Percentage": "cumulative_percentage",
	"Annual Cumulative Raw Score": "cumulative_score",
	"Annual Cumulative Percentage": "cumulative_percentage",
	"Annual Average Percentage": "annual_percentage",
}


def get_result_periods(profile: str | dict, academic_year: str) -> list[dict]:
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
	calendar = get_enabled_institution_calendar(
		config.get("institution"),
		academic_year=academic_year,
	)
	if not calendar:
		frappe.throw(
			_("Configure an enabled Institution Academic Calendar before calculating cumulative results."),
			frappe.ValidationError,
		)
	rows = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={
			"parent": calendar.name,
			"parenttype": "EduEdge Institution Academic Calendar",
			"include_in_result_aggregation": 1,
		},
		fields=[
			"academic_term",
			"report_label",
			"start_date",
			"end_date",
			"sequence",
			"annual_result_weight",
		],
		order_by="sequence asc, start_date asc, idx asc",
	)
	output = []
	for row in rows:
		term = frappe.db.get_value(
			"Academic Term",
			row.academic_term,
			["term_name", "academic_year"],
			as_dict=True,
		)
		if not term or term.academic_year != academic_year:
			frappe.throw(
				_("Academic Calendar period {0} is outside Academic Year {1}.").format(
					row.academic_term, academic_year
				),
				frappe.ValidationError,
			)
		output.append(
			{
				"academic_term": row.academic_term,
				"display_label": row.report_label or term.term_name or row.academic_term,
				"start_date": row.start_date,
				"end_date": row.end_date,
				"sequence": cint(row.sequence),
				"weight": flt(row.annual_result_weight),
			}
		)
	return output


def compose_terminal_subject_results(profile: str | dict, result_rows: list) -> dict:
	"""Compose submitted native Assessment Results into report-level subject components."""
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
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
						"excluded_count": 0,
						"states": [],
						"required": bool(component.get("required")),
						"sequence": component["sequence"],
					}
					for key, component in component_config.items()
				},
				"total_score": 0.0,
				"maximum_score": 0.0,
				"percentage": 0.0,
				"eligible": False,
				"grade": "",
				"remark": "",
				"grading_scale": "",
			},
		)

		state = _value(row, "eduedge_score_state") or "Scored"
		if state not in SCORE_STATES:
			state = "Scored"
		component = subject["components"][component_key]
		if state in {"Exempt", "Not Offered"}:
			component["excluded_count"] += 1
			component["states"].append(state)
			continue
		if state == "Absent":
			component["states"].append(state)
			if config["absence_policy"] == "Block Publication":
				blockers.append(
					{"course": course, "assessment_group": assessment_group, "reason": "Absent"}
				)
				continue
			if config["absence_policy"] == "Exclude from Denominator":
				component["excluded_count"] += 1
				continue
			if config["absence_policy"] != "Treat as Zero":
				frappe.throw(_("Unsupported absence policy."), frappe.ValidationError)

		maximum_score = flt(_value(row, "maximum_score"))
		score = 0.0 if state == "Absent" else flt(_value(row, "total_score"))
		component["score"] += score
		component["maximum_score"] += maximum_score
		component["assessment_count"] += 1
		if state == "Scored":
			component["states"].append("Scored")
		subject["total_score"] += score
		subject["maximum_score"] += maximum_score
		if _value(row, "grading_scale"):
			subject["grading_scale"] = _value(row, "grading_scale")

	for subject in subjects.values():
		missing_components = [
			key
			for key, component in subject["components"].items()
			if component["required"]
			and component["assessment_count"] == 0
			and component["excluded_count"] == 0
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
		subject["eligible"] = bool(subject["maximum_score"])
		subject["percentage"] = (
			round(subject["total_score"] / subject["maximum_score"] * 100, precision)
			if subject["maximum_score"]
			else 0.0
		)

		grading_scale = config.get("grading_scale") or subject.get("grading_scale")
		if grading_scale and subject["eligible"]:
			subject["grade"] = get_grade(grading_scale, subject["percentage"])
			subject["remark"] = get_grade_remark(grading_scale, subject["percentage"])

		subject["components"] = sorted(
			subject["components"].values(),
			key=lambda row: (row["sequence"], row["component_key"]),
		)
		for component in subject["components"]:
			component["score"] = round(component["score"], precision)
			component["maximum_score"] = round(component["maximum_score"], precision)

	sorted_subjects = sorted(subjects.values(), key=lambda row: row["course"])
	return {
		"profile": config,
		"subjects": sorted_subjects,
		"summary": calculate_overall_summary(sorted_subjects, config),
		"blockers": blockers,
		"unmapped_assessment_groups": sorted(unmapped),
	}


def compose_cumulative_subject_results(
	profile: str | dict,
	result_rows: list,
	periods: list[dict],
	*,
	through_term: str | None = None,
) -> dict:
	"""Compose Year-to-Date or full Annual subject results from native term results."""
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
	precision = cint(config.get("score_precision") or 2)
	active_periods = []
	for period in periods:
		active_periods.append(period)
		if through_term and period["academic_term"] == through_term:
			break
	if through_term and not any(row["academic_term"] == through_term for row in active_periods):
		frappe.throw(_("Selected Academic Term is not part of the Result Profile calendar."), frappe.ValidationError)

	rows_by_term: dict[str, list] = defaultdict(list)
	for row in result_rows:
		term = _value(row, "academic_term")
		if term:
			rows_by_term[term].append(row)

	term_payloads: dict[str, dict] = {}
	blockers: list[dict] = []
	unmapped: set[str] = set()
	for period in active_periods:
		term = period["academic_term"]
		payload = compose_terminal_subject_results(config, rows_by_term.get(term, []))
		term_payloads[term] = payload
		blockers.extend(
			{"academic_term": term, **item} for item in (payload.get("blockers") or [])
		)
		unmapped.update(payload.get("unmapped_assessment_groups") or [])

	subjects: dict[str, dict] = {}
	for period in active_periods:
		payload = term_payloads[period["academic_term"]]
		for term_subject in payload["subjects"]:
			subject = subjects.setdefault(
				term_subject["course"],
				{
					"course": term_subject["course"],
					"periods": [],
					"cumulative_score": 0.0,
					"cumulative_maximum_score": 0.0,
					"cumulative_percentage": 0.0,
					"annual_percentage": 0.0,
					"annual_average_percentage": 0.0,
					"eligible_period_count": 0,
					"eligible": False,
					"grade": "",
					"remark": "",
					"grading_scale": term_subject.get("grading_scale") or "",
				},
			)
			period_row = {
				"academic_term": period["academic_term"],
				"display_label": period["display_label"],
				"sequence": period["sequence"],
				"weight": period["weight"],
				"components": term_subject["components"],
				"total_score": term_subject["total_score"],
				"maximum_score": term_subject["maximum_score"],
				"percentage": term_subject["percentage"],
				"eligible": term_subject["eligible"],
				"grade": term_subject["grade"],
				"remark": term_subject["remark"],
			}
			subject["periods"].append(period_row)
			if term_subject["eligible"]:
				subject["eligible_period_count"] += 1
				subject["cumulative_score"] += flt(term_subject["total_score"])
				subject["cumulative_maximum_score"] += flt(term_subject["maximum_score"])
				if term_subject.get("grading_scale"):
					subject["grading_scale"] = term_subject["grading_scale"]

	for subject in subjects.values():
		eligible_periods = [row for row in subject["periods"] if row["eligible"]]
		if subject["eligible_period_count"] < cint(config["minimum_eligible_periods"]):
			blockers.append(
				{
					"course": subject["course"],
					"reason": "Insufficient Eligible Periods",
					"eligible_periods": subject["eligible_period_count"],
					"minimum_eligible_periods": cint(config["minimum_eligible_periods"]),
				}
			)
		subject["cumulative_score"] = round(subject["cumulative_score"], precision)
		subject["cumulative_maximum_score"] = round(subject["cumulative_maximum_score"], precision)
		subject["cumulative_percentage"] = (
			round(
				subject["cumulative_score"] / subject["cumulative_maximum_score"] * 100,
				precision,
			)
			if subject["cumulative_maximum_score"]
			else 0.0
		)

		method = config["annual_aggregation_method"]
		if method == "Equal Average of Eligible Terms":
			annual_percentage = mean([row["percentage"] for row in eligible_periods]) if eligible_periods else 0
		elif method == "Weighted Average":
			missing_weights = [
				row["academic_term"] for row in eligible_periods if flt(row.get("weight")) <= 0
			]
			if missing_weights:
				blockers.append(
					{
						"course": subject["course"],
						"reason": "Missing Annual Result Weight",
						"academic_terms": missing_weights,
					}
				)
				annual_percentage = 0
			else:
				total_weight = sum(flt(row["weight"]) for row in eligible_periods)
				annual_percentage = (
					sum(flt(row["percentage"]) * flt(row["weight"]) for row in eligible_periods)
					/ total_weight
					if total_weight
					else 0
				)
		elif method == "Raw Cumulative":
			annual_percentage = subject["cumulative_percentage"]
		else:
			frappe.throw(_("Unsupported annual aggregation method."), frappe.ValidationError)

		subject["annual_percentage"] = round(annual_percentage, precision)
		subject["annual_average_percentage"] = subject["annual_percentage"]
		subject["eligible"] = bool(eligible_periods)
		grading_scale = config.get("grading_scale") or subject.get("grading_scale")
		if grading_scale and subject["eligible"]:
			subject["grade"] = get_grade(grading_scale, subject["annual_percentage"])
			subject["remark"] = get_grade_remark(grading_scale, subject["annual_percentage"])

	sorted_subjects = sorted(subjects.values(), key=lambda row: row["course"])
	return {
		"profile": config,
		"periods": active_periods,
		"subjects": sorted_subjects,
		"summary": calculate_overall_summary(
			sorted_subjects,
			config,
			percentage_field="annual_percentage",
			score_field="cumulative_score",
			maximum_field="cumulative_maximum_score",
		),
		"blockers": blockers,
		"unmapped_assessment_groups": sorted(unmapped),
	}


def calculate_overall_summary(
	subjects: list[dict],
	config: dict,
	*,
	percentage_field: str = "percentage",
	score_field: str = "total_score",
	maximum_field: str = "maximum_score",
) -> dict:
	precision = cint(config.get("score_precision") or 2)
	eligible = [row for row in subjects if row.get("eligible")]
	total_score = sum(flt(row.get(score_field)) for row in eligible)
	maximum_score = sum(flt(row.get(maximum_field)) for row in eligible)
	sum_subject_percentages = sum(flt(row.get(percentage_field)) for row in eligible)
	if config.get("overall_calculation_method") == "Aggregate Score Percentage":
		overall_percentage = total_score / maximum_score * 100 if maximum_score else 0
	else:
		overall_percentage = (
			sum_subject_percentages / len(eligible) if eligible else 0
		)
	grading_scale = config.get("grading_scale")
	overall_grade = get_grade(grading_scale, overall_percentage) if grading_scale and eligible else ""
	overall_remark = get_grade_remark(grading_scale, overall_percentage) if grading_scale and eligible else ""
	return {
		"subject_count": len(eligible),
		"total_score": round(total_score, precision),
		"maximum_score": round(maximum_score, precision),
		"sum_subject_percentages": round(sum_subject_percentages, precision),
		"overall_percentage": round(overall_percentage, precision),
		"overall_grade": overall_grade,
		"overall_remark": overall_remark,
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


def build_configured_class_metrics(
	profile: str | dict,
	subject_rows: list[dict],
	*,
	result_mode: str,
) -> list[dict]:
	config = get_result_profile_config(profile) if isinstance(profile, str) else profile
	visible_field = "show_on_annual" if result_mode == "Annual" else "show_on_terminal"
	output = []
	for metric in config.get("metrics") or []:
		if not metric.get(visible_field):
			continue
		stats = calculate_class_statistics(subject_rows, metric["calculation_basis"])
		stat_field = {
			"Class Highest": "highest",
			"Class Lowest": "lowest",
			"Class Average": "average",
		}.get(metric["metric_key"])
		if not stat_field:
			continue
		value = stats.get(stat_field)
		output.append(
			{
				"metric_key": metric["metric_key"],
				"display_label": metric["display_label"],
				"calculation_basis": metric["calculation_basis"],
				"display_as": metric["display_as"],
				"value": value,
				"display_value": format_metric_value(
					value,
					metric["display_as"],
					metric["decimal_places"],
				),
				"cohort_count": stats["count"],
				"sequence": metric["sequence"],
			}
		)
	return sorted(output, key=lambda row: (row["sequence"], row["display_label"]))


def format_metric_value(value, display_as: str, decimal_places: int = 2):
	if value is None:
		return None
	precision = max(0, min(cint(decimal_places), 6))
	if display_as == "Percentage":
		return f"{flt(value):.{precision}f}%"
	if display_as == "Number":
		return str(int(round(flt(value))))
	return f"{flt(value):.{precision}f}"


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
