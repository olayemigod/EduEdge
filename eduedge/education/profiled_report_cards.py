from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from eduedge.education.result_snapshots import get_snapshot_payload

SNAPSHOT_DOCTYPE = "EduEdge Published Result Snapshot"


def get_profiled_publication_student_summaries(publication, review_doctype: str) -> list[dict]:
	snapshots = frappe.get_all(
		SNAPSHOT_DOCTYPE,
		filters={"result_publication": publication.name},
		fields=["student", "student_name"],
		order_by="student_name asc, student asc",
		page_length=0,
	)
	if not snapshots:
		frappe.throw(
			_("This published Result Profile has no immutable student snapshots."),
			frappe.ValidationError,
		)
	student_names = [row.student for row in snapshots]
	reviews = frappe.get_all(
		review_doctype,
		filters={"result_publication": publication.name, "student": ["in", student_names]},
		fields=[
			"name",
			"student",
			"class_teacher_comment",
			"principal_comment",
			"progression_recommendation",
			"progression_status",
			"average_percent",
			"overall_grade",
			"attendance_percent",
			"recommended_by",
			"recommended_on",
			"approved_by",
			"approved_on",
			"last_review_note",
		],
		page_length=0,
	)
	review_by_student = {row.student: row for row in reviews}
	output = []
	for snapshot in snapshots:
		payload = get_snapshot_payload(publication.name, snapshot.student)
		if not payload:
			continue
		summary = summary_from_snapshot_payload(payload)
		review = review_by_student.get(snapshot.student)
		summary["review"] = dict(review) if review else None
		output.append(summary)
	return output


def get_profiled_student_report_card_payload(publication, student: str, review_doctype: str) -> dict:
	payload = get_snapshot_payload(publication.name, student)
	if not payload:
		frappe.throw(
			_("No immutable report-card snapshot exists for this Student and publication."),
			frappe.DoesNotExistError,
		)
	summary = summary_from_snapshot_payload(payload)
	review = frappe.db.get_value(
		review_doctype,
		{"result_publication": publication.name, "student": student},
		[
			"name",
			"class_teacher_comment",
			"principal_comment",
			"progression_recommendation",
			"progression_status",
			"recommended_by",
			"recommended_on",
			"approved_by",
			"approved_on",
			"last_review_note",
		],
		as_dict=True,
	)
	identity = _institution_identity(publication.school_branch)
	return {
		"publication": dict(publication),
		"student": payload.get("student") or {"name": student},
		"branch": identity["branch"],
		"company": identity["company"],
		"address": identity["address"],
		"summary": summary,
		"review": dict(review) if review else {},
		"snapshot": {
			"schema_version": payload.get("schema_version"),
			"grading_legend": payload.get("grading_legend") or [],
			"source_assessment_results": payload.get("source_assessment_results") or [],
		},
	}


def summary_from_snapshot_payload(payload: dict) -> dict:
	publication = payload.get("publication") or {}
	student = payload.get("student") or {}
	result = payload.get("result") or {}
	result_summary = result.get("summary") or {}
	profile = payload.get("profile") or {}
	attendance = payload.get("attendance") or {}
	mode = publication.get("result_mode") or "Terminal"
	courses = _prepare_courses(result.get("subjects") or [], profile, mode)
	average_percent = flt(result_summary.get("overall_percentage"))
	suggested = _suggested_progression(mode, average_percent, bool(courses))
	school_opened = int(attendance.get("school_opened") or 0)
	return {
		"student": student.get("name"),
		"student_name": student.get("student_name"),
		"group_roll_number": student.get("group_roll_number"),
		"result_publication": publication.get("name"),
		"publication_version": int(publication.get("publication_version") or 1),
		"result_mode": mode,
		"result_profile": publication.get("result_profile"),
		"student_group": publication.get("student_group"),
		"academic_year": publication.get("academic_year"),
		"academic_term": publication.get("academic_term"),
		"academic_term_label": publication.get("academic_term_label") or publication.get("academic_term"),
		"assessment_group": publication.get("assessment_group"),
		"course_count": int(result_summary.get("subject_count") or len(courses)),
		"courses": courses,
		"total_score": flt(result_summary.get("total_score")),
		"maximum_score": flt(result_summary.get("maximum_score")),
		"sum_subject_percentages": flt(result_summary.get("sum_subject_percentages")),
		"average_percent": average_percent,
		"overall_grade": result_summary.get("overall_grade") or "",
		"overall_remark": result_summary.get("overall_remark") or "",
		"attendance_present": int(attendance.get("present") or 0),
		"attendance_absent": int(attendance.get("absent") or 0),
		"attendance_leave": int(attendance.get("leave") or 0),
		"attendance_total": school_opened,
		"attendance_school_opened": school_opened,
		"attendance_percent": flt(attendance.get("attendance_percentage")),
		"next_term_start_date": payload.get("next_term_start_date"),
		"suggested_progression": suggested,
		"profile": profile,
		"display_components": _visible_components(profile, mode),
		"display_metrics": _visible_metrics(profile, mode),
		"periods": result.get("periods") or [],
		"grading_legend": payload.get("grading_legend") or [],
	}


def _prepare_courses(subjects: list[dict], profile: dict, mode: str) -> list[dict]:
	visible_keys = {row["component_key"] for row in _visible_components(profile, mode)}
	output = []
	for source in subjects:
		row = dict(source)
		row["course_name"] = row.get("course_name") or row.get("course")
		row["metrics"] = list(row.get("metrics") or [])
		if mode == "Annual":
			prepared_periods = []
			for period in row.get("periods") or []:
				period_row = dict(period)
				period_row["display_components"] = [
					component
					for component in (period_row.get("components") or [])
					if component.get("component_key") in visible_keys
				]
				prepared_periods.append(period_row)
			row["periods"] = prepared_periods
		else:
			row["display_components"] = [
				component
				for component in (row.get("components") or [])
				if component.get("component_key") in visible_keys
			]
		output.append(row)
	return sorted(output, key=lambda row: (row.get("course_name") or "").casefold())


def _visible_components(profile: dict, mode: str) -> list[dict]:
	fieldname = "show_on_annual" if mode == "Annual" else "show_on_terminal"
	return [
		row for row in (profile.get("components") or []) if row.get(fieldname)
	]


def _visible_metrics(profile: dict, mode: str) -> list[dict]:
	fieldname = "show_on_annual" if mode == "Annual" else "show_on_terminal"
	return [
		row for row in (profile.get("metrics") or []) if row.get(fieldname)
	]


def _suggested_progression(mode: str, average_percent: float, has_courses: bool) -> str:
	if mode != "Annual" or not has_courses:
		return "Pending Review"
	settings = frappe.get_single("EduEdge Settings")
	pass_average = flt(settings.promotion_pass_average or 0)
	return "Promote" if average_percent >= pass_average else "Repeat"


def _institution_identity(branch_name: str) -> dict:
	branch = frappe.db.get_value(
		"EduEdge School Branch",
		branch_name,
		["name", "branch_name", "branch_code", "company", "address"],
		as_dict=True,
	)
	company = None
	if branch and branch.company:
		company = frappe.db.get_value(
			"Company",
			branch.company,
			["name", "company_name", "company_logo"],
			as_dict=True,
		)
	address = None
	if branch and branch.address:
		address = frappe.db.get_value(
			"Address",
			branch.address,
			[
				"address_line1",
				"address_line2",
				"city",
				"state",
				"country",
				"pincode",
				"phone",
				"email_id",
			],
			as_dict=True,
		)
	return {
		"branch": dict(branch) if branch else {},
		"company": dict(company) if company else {},
		"address": dict(address) if address else {},
	}
