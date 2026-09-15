from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from eduedge.education.assessment_operations import get_publication_readiness
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.result_engine import (
	build_component_plan_maximum_blockers,
	build_configured_class_metrics,
	compose_cumulative_subject_results,
	compose_terminal_subject_results,
	get_result_periods,
)
from eduedge.education.result_attendance import (
	assert_official_attendance_complete,
	build_result_attendance_summary,
)
from eduedge.education.result_profile import get_publication_result_profile_config

SNAPSHOT_DOCTYPE = "EduEdge Published Result Snapshot"


def create_publication_snapshots(publication: str) -> list[str]:
	doc = frappe.get_doc("EduEdge Result Publication", publication)
	if not doc.result_profile:
		# Historical publications remain supported. New Result Profile publications
		# receive immutable academic snapshots.
		return []

	payloads = build_publication_student_payloads(doc)
	names = []
	for student, item in payloads.items():
		payload_json = _canonical_json(item["payload"])
		payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
		existing = frappe.db.get_value(
			SNAPSHOT_DOCTYPE,
			{"result_publication": doc.name, "student": student},
			["name", "payload_hash"],
			as_dict=True,
		)
		if existing:
			if existing.payload_hash != payload_hash:
				frappe.throw(
					_("Published snapshot source changed after snapshot preparation. Create a new Result Publication revision."),
					frappe.ValidationError,
				)
			names.append(existing.name)
			continue
		snapshot = frappe.get_doc(
			{
				"doctype": SNAPSHOT_DOCTYPE,
				"result_publication": doc.name,
				"publication_version": int(doc.publication_version or 1),
				"student": student,
				"student_name": item["student"].get("student_name"),
				"school_branch": doc.school_branch,
				"student_group": doc.student_group,
				"academic_year": doc.academic_year,
				"academic_term": doc.academic_term,
				"result_profile": doc.result_profile,
				"result_mode": doc.result_mode or "Terminal",
				"payload_hash": payload_hash,
				"source_result_count": len(item["source_result_names"]),
				"generated_by": frappe.session.user,
				"generated_on": now_datetime(),
				"payload_json": payload_json,
			}
		)
		snapshot.insert(ignore_permissions=True)
		names.append(snapshot.name)
	return names


def build_publication_student_payloads(publication_doc) -> dict[str, dict]:
	config = get_publication_result_profile_config(publication_doc)
	readiness = get_publication_readiness(
		school_branch=publication_doc.school_branch,
		student_group=publication_doc.student_group,
		academic_year=publication_doc.academic_year,
		academic_term=publication_doc.academic_term,
		assessment_group=publication_doc.assessment_group,
		result_profile=publication_doc.result_profile,
		result_mode=publication_doc.result_mode or "Terminal",
		profile_config_override=config,
	)
	if not readiness["ready"]:
		frappe.throw(
			_("Result Publication is not ready for immutable snapshot generation."),
			frappe.ValidationError,
		)

	students = readiness["students"]
	student_names = [row.student for row in students]
	plan_names = [row.name for row in readiness["plans"]]
	rows = _get_submitted_result_rows(
		publication_doc.school_branch,
		plan_names,
		student_names,
	)
	rows_by_student: dict[str, list] = defaultdict(list)
	for row in rows:
		rows_by_student[row.student].append(row)

	composed_by_student: dict[str, dict] = {}
	if (publication_doc.result_mode or "Terminal") == "Annual":
		periods = readiness.get("periods") or get_result_periods(config, publication_doc.academic_year)
		for student in student_names:
			composed_by_student[student] = compose_cumulative_subject_results(
				config,
				rows_by_student.get(student, []),
				periods,
			)
		source_rows = rows
	else:
		periods = []
		for student in student_names:
			composed_by_student[student] = compose_terminal_subject_results(
				config,
				rows_by_student.get(student, []),
			)
		source_rows = list(rows)
		if _requires_ytd_metrics(config):
			if not publication_doc.academic_term:
				frappe.throw(
					_("Year-to-Date report metrics require an Academic Term publication."),
					frappe.ValidationError,
				)
			ytd_periods = _periods_through_term(
				get_result_periods(config, publication_doc.academic_year),
				publication_doc.academic_term,
			)
			ytd_rows = _get_complete_period_result_rows(
				publication_doc,
				config,
				student_names,
				ytd_periods,
			)
			ytd_by_student: dict[str, list] = defaultdict(list)
			for row in ytd_rows:
				ytd_by_student[row.student].append(row)
			for student in student_names:
				ytd = compose_cumulative_subject_results(
					config,
					ytd_by_student.get(student, []),
					ytd_periods,
					through_term=publication_doc.academic_term,
				)
				_ytd_by_course = {row["course"]: row for row in ytd["subjects"]}
				for subject in composed_by_student[student]["subjects"]:
					cumulative = _ytd_by_course.get(subject["course"])
					if cumulative:
						subject["cumulative_score"] = cumulative["cumulative_score"]
						subject["cumulative_maximum_score"] = cumulative["cumulative_maximum_score"]
						subject["cumulative_percentage"] = cumulative["cumulative_percentage"]
			periods = ytd_periods
			source_rows.extend(ytd_rows)

	_course_names = _course_name_map(composed_by_student)
	for result in composed_by_student.values():
		for subject in result["subjects"]:
			subject["course_name"] = _course_names.get(subject["course"]) or subject["course"]

	_cohort_by_course: dict[str, list] = defaultdict(list)
	for result in composed_by_student.values():
		for subject in result["subjects"]:
			_cohort_by_course[subject["course"]].append(subject)
	for result in composed_by_student.values():
		for subject in result["subjects"]:
			subject["metrics"] = build_configured_class_metrics(
				config,
				_cohort_by_course[subject["course"]],
				result_mode=publication_doc.result_mode or "Terminal",
			)

	attendance, attendance_meta = build_result_attendance_summary(
		school_branch=publication_doc.school_branch,
		student_group=publication_doc.student_group,
		academic_year=publication_doc.academic_year,
		academic_term=publication_doc.academic_term,
		result_mode=publication_doc.result_mode or "Terminal",
		students=student_names,
		periods=readiness.get("periods") or periods,
	)
	if (config.get("presentation") or {}).get("show_attendance"):
		assert_official_attendance_complete(attendance_meta)
	source_names_by_student: dict[str, set[str]] = defaultdict(set)
	for row in source_rows:
		source_names_by_student[row.student].add(row.name)

	student_info = {
		row.name: row
		for row in frappe.get_all(
			"Student",
			filters={"name": ["in", student_names]},
			fields=["name", "student_name", "image", "program"],
		)
	}
	group_rows = {row.student: row for row in students}
	output = {}
	for student in student_names:
		identity = student_info.get(student) or frappe._dict({"name": student})
		group_row = group_rows.get(student)
		payload = {
			"schema_version": 1,
			"publication": {
				"name": publication_doc.name,
				"publication_version": int(publication_doc.publication_version or 1),
				"result_mode": publication_doc.result_mode or "Terminal",
				"school_branch": publication_doc.school_branch,
				"student_group": publication_doc.student_group,
				"academic_year": publication_doc.academic_year,
				"academic_term": publication_doc.academic_term,
				"academic_term_label": _academic_term_report_label(
					publication_doc,
					config,
				),
				"assessment_group": publication_doc.assessment_group,
				"result_profile": publication_doc.result_profile,
			},
			"profile": config,
			"grading_legend": _grading_legend(config),
			"student": {
				"name": student,
				"student_name": identity.get("student_name"),
				"image": identity.get("image"),
				"program": identity.get("program"),
				"group_roll_number": group_row.get("group_roll_number") if group_row else None,
			},
			"result": composed_by_student[student],
			"attendance": attendance.get(student, {}),
			"next_term_start_date": _next_term_start(
				publication_doc,
				get_result_periods(config, publication_doc.academic_year),
			),
			"source_assessment_results": sorted(source_names_by_student[student]),
		}
		output[student] = {
			"student": payload["student"],
			"source_result_names": payload["source_assessment_results"],
			"payload": payload,
		}
	return output


def get_snapshot_payload(publication: str, student: str) -> dict | None:
	row = frappe.db.get_value(
		SNAPSHOT_DOCTYPE,
		{"result_publication": publication, "student": student},
		["name", "payload_json", "payload_hash"],
		as_dict=True,
	)
	if not row:
		return None
	actual_hash = hashlib.sha256((row.payload_json or "").encode("utf-8")).hexdigest()
	if actual_hash != row.payload_hash:
		frappe.throw(_("Published Result Snapshot integrity check failed."), frappe.ValidationError)
	return json.loads(row.payload_json)


def _get_submitted_result_rows(branch: str, plan_names: list[str], students: list[str]) -> list:
	if not plan_names or not students:
		return []
	fields = [
		"name",
		"assessment_plan",
		"assessment_group",
		"student",
		"course",
		"academic_term",
		"docstatus",
		"maximum_score",
		"total_score",
		"grade",
		"grading_scale",
	]
	if frappe.get_meta("Assessment Result").has_field("eduedge_score_state"):
		fields.append("eduedge_score_state")
	return frappe.get_all(
		"Assessment Result",
		filters={
			BRANCH_FIELD: branch,
			"assessment_plan": ["in", plan_names],
			"student": ["in", students],
			"docstatus": 1,
		},
		fields=fields,
		page_length=0,
	)


def _get_complete_period_result_rows(publication_doc, config: dict, students: list[str], periods: list[dict]) -> list:
	if frappe.db.get_value("Student Group", publication_doc.student_group, "academic_term"):
		frappe.throw(
			_("Year-to-Date statistics require a sessional Student Group/Class Arm."),
			frappe.ValidationError,
		)
	assessment_groups = sorted(
		{
			leaf
			for source in config.get("component_sources") or []
			for leaf in source.get("leaf_assessment_groups") or []
		}
	)
	terms = [row["academic_term"] for row in periods]
	plans = frappe.get_all(
		"Assessment Plan",
		filters={
			BRANCH_FIELD: publication_doc.school_branch,
			"student_group": publication_doc.student_group,
			"academic_year": publication_doc.academic_year,
			"academic_term": ["in", terms or ["__none__"]],
			"assessment_group": ["in", assessment_groups or ["__none__"]],
			"docstatus": 1,
		},
		fields=["name", "assessment_group", "course", "academic_term", "maximum_assessment_score"],
		page_length=0,
	)
	maximum_blockers = build_component_plan_maximum_blockers(config, plans)
	if maximum_blockers:
		first = maximum_blockers[0]
		frappe.throw(
			_(
				"Prior-period Assessment Plan maximum for {0} / {1} does not match the Result Profile target."
			).format(first.get("course"), first.get("component_key")),
			frappe.ValidationError,
		)
	plan_names = [row.name for row in plans]
	rows = _get_submitted_result_rows(publication_doc.school_branch, plan_names, students)
	expected = len(plan_names) * len(students)
	pairs = {(row.assessment_plan, row.student) for row in rows}
	if not plan_names or len(pairs) != expected:
		frappe.throw(
			_("Year-to-Date statistics are incomplete. Complete and submit prior-period results before publication."),
			frappe.ValidationError,
		)
	return rows


def _periods_through_term(periods: list[dict], academic_term: str) -> list[dict]:
	output = []
	found = False
	for period in periods:
		output.append(period)
		if period["academic_term"] == academic_term:
			found = True
			break
	if not found:
		frappe.throw(
			_("Academic Term is not configured for cumulative result aggregation."),
			frappe.ValidationError,
		)
	return output


def _requires_ytd_metrics(config: dict) -> bool:
	return any(
		metric.get("show_on_terminal")
		and str(metric.get("calculation_basis") or "").startswith("Year-to-Date")
		for metric in config.get("metrics") or []
	)


def _grading_legend(config: dict) -> list[dict]:
	grading_scale = config.get("grading_scale")
	if not grading_scale:
		return []
	fields = ["grade_code", "threshold"]
	if frappe.get_meta("Grading Scale Interval").has_field("eduedge_report_remark"):
		fields.append("eduedge_report_remark")
	rows = frappe.get_all(
		"Grading Scale Interval",
		filters={"parent": grading_scale},
		fields=fields,
		order_by="threshold desc, idx asc",
	)
	return [
		{
			"grade_code": row.grade_code,
			"threshold": flt(row.threshold),
			"remark": row.get("eduedge_report_remark") or "",
		}
		for row in rows
	]


def _course_name_map(composed_by_student: dict[str, dict]) -> dict[str, str]:
	courses = sorted(
		{
			subject["course"]
			for result in composed_by_student.values()
			for subject in result.get("subjects") or []
			if subject.get("course")
		}
	)
	if not courses:
		return {}
	return {
		row.name: row.course_name
		for row in frappe.get_all(
			"Course",
			filters={"name": ["in", courses]},
			fields=["name", "course_name"],
		)
	}


def _academic_term_report_label(publication_doc, config: dict):
	if not publication_doc.academic_term:
		return None
	for period in get_result_periods(config, publication_doc.academic_year):
		if period["academic_term"] == publication_doc.academic_term:
			return period.get("display_label") or publication_doc.academic_term
	return publication_doc.academic_term


def _next_term_start(publication_doc, periods: list[dict]):
	if not publication_doc.academic_term:
		return None
	for index, period in enumerate(periods):
		if period["academic_term"] == publication_doc.academic_term:
			if index + 1 < len(periods):
				return str(periods[index + 1]["start_date"])
			return None
	return None


def _canonical_json(value: dict) -> str:
	return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
