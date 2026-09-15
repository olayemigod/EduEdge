from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _

from eduedge.education.custom_fields import BRANCH_FIELD


VALID_ATTENDANCE_STATUSES = {"Present", "Absent", "Leave"}


def build_result_attendance_summary(
	*,
	school_branch: str,
	student_group: str,
	academic_year: str,
	academic_term: str | None,
	result_mode: str,
	students: list[str],
	periods: list[dict] | None = None,
) -> tuple[dict[str, dict], dict]:
	meta = {
		"source_mode": "None",
		"school_opened": 0,
		"missing_student_days": 0,
		"conflicting_student_days": 0,
		"duplicate_daily_student_days": 0,
		"invalid_status_days": 0,
		"course_only_dates": [],
	}
	if not students:
		return {}, meta

	from_date, to_date = _result_attendance_dates(
		academic_year=academic_year,
		academic_term=academic_term,
		result_mode=result_mode,
		periods=periods or [],
	)
	if not from_date or not to_date:
		return {}, meta

	rows = frappe.get_all(
		"Student Attendance",
		filters={
			BRANCH_FIELD: school_branch,
			"student_group": student_group,
			"student": ["in", students],
			"docstatus": 1,
			"date": ["between", [from_date, to_date]],
		},
		fields=["student", "date", "status", "course_schedule"],
		page_length=0,
	)

	# Daily Student Group attendance is authoritative whenever it exists in the
	# result period. Course Schedule attendance is only a fallback when there are
	# no daily class-attendance rows anywhere in the period.
	daily_rows = [row for row in rows if not row.course_schedule]
	all_dates = {str(row.date) for row in rows if row.date}
	daily_dates = {str(row.date) for row in daily_rows if row.date}
	course_only_dates = sorted(all_dates - daily_dates) if daily_rows else []
	source_rows = daily_rows if daily_rows else rows
	source_mode = "Daily Student Group" if daily_rows else ("Course Schedule Fallback" if rows else "None")
	opened_dates = sorted({str(row.date) for row in source_rows if row.date})
	school_opened = len(opened_dates)

	by_student_date: dict[tuple[str, str], list] = defaultdict(list)
	for row in source_rows:
		if row.date:
			by_student_date[(row.student, str(row.date))].append(row)

	missing_student_days = sum(
		1
		for date in opened_dates
		for student in students
		if (student, date) not in by_student_date
	)
	duplicate_daily_student_days = (
		sum(1 for day_rows in by_student_date.values() if len(day_rows) > 1)
		if daily_rows
		else 0
	)
	conflicting_student_days = 0
	invalid_status_days = 0
	counts: dict[str, dict] = defaultdict(lambda: {"Present": 0, "Absent": 0, "Leave": 0})
	for (student, _date), day_rows in by_student_date.items():
		statuses = {str(row.status or "").strip() for row in day_rows if str(row.status or "").strip()}
		if len(statuses) > 1:
			conflicting_student_days += 1
			continue
		day_status = next(iter(statuses), "")
		if day_status and day_status not in VALID_ATTENDANCE_STATUSES:
			invalid_status_days += 1
			continue
		if day_status:
			counts[student][day_status] = counts[student].get(day_status, 0) + 1

	coverage_complete = not (
		missing_student_days
		or conflicting_student_days
		or duplicate_daily_student_days
		or invalid_status_days
		or course_only_dates
	)
	output = {}
	for student in students:
		student_counts = counts[student]
		present = int(student_counts.get("Present", 0))
		output[student] = {
			"present": present,
			"absent": int(student_counts.get("Absent", 0)),
			"leave": int(student_counts.get("Leave", 0)),
			"school_opened": school_opened,
			"attendance_percentage": round(present / school_opened * 100, 2) if school_opened else 0.0,
			"from_date": str(from_date),
			"to_date": str(to_date),
			"source_mode": source_mode,
			"coverage_complete": coverage_complete,
		}
	meta = {
		"source_mode": source_mode,
		"school_opened": school_opened,
		"missing_student_days": missing_student_days,
		"conflicting_student_days": conflicting_student_days,
		"duplicate_daily_student_days": duplicate_daily_student_days,
		"invalid_status_days": invalid_status_days,
		"course_only_dates": course_only_dates,
	}
	return output, meta


def get_official_attendance_blockers(meta: dict) -> list[dict]:
	blockers = []
	if not meta.get("school_opened"):
		blockers.append(
			{
				"code": "NO_OFFICIAL_ATTENDANCE",
				"reason": "Attendance is enabled on this Result Profile, but no submitted attendance exists for the result period.",
			}
		)
	if meta.get("course_only_dates"):
		blockers.append(
			{
				"code": "MIXED_ATTENDANCE_SOURCE",
				"reason": "Attendance switches between daily class attendance and course-level attendance within the result period. Complete daily attendance for all opened dates before publishing official results.",
				"course_only_date_count": len(meta["course_only_dates"]),
			}
		)
	if meta.get("duplicate_daily_student_days"):
		blockers.append(
			{
				"code": "DUPLICATE_DAILY_ATTENDANCE",
				"reason": "Daily class attendance contains duplicate Student/day records. Resolve them before publishing official results.",
				"count": int(meta["duplicate_daily_student_days"]),
			}
		)
	if meta.get("conflicting_student_days"):
		blockers.append(
			{
				"code": "CONFLICTING_ATTENDANCE_STATUS",
				"reason": "Attendance contains conflicting statuses for the same Student/day. Resolve them before publishing official results.",
				"count": int(meta["conflicting_student_days"]),
			}
		)
	if meta.get("invalid_status_days"):
		blockers.append(
			{
				"code": "INVALID_ATTENDANCE_STATUS",
				"reason": "Attendance contains unsupported statuses. Use Present, Absent or Leave before publishing official results.",
				"count": int(meta["invalid_status_days"]),
			}
		)
	if meta.get("missing_student_days"):
		blockers.append(
			{
				"code": "INCOMPLETE_ATTENDANCE",
				"reason": _(
					"Attendance is incomplete for {0} Student/day combinations. Complete the attendance register before publishing official results."
				).format(meta["missing_student_days"]),
				"count": int(meta["missing_student_days"]),
			}
		)
	return blockers


def assert_official_attendance_complete(meta: dict) -> None:
	blockers = get_official_attendance_blockers(meta)
	if blockers:
		frappe.throw(_(blockers[0]["reason"]), frappe.ValidationError)


def _result_attendance_dates(
	*,
	academic_year: str,
	academic_term: str | None,
	result_mode: str,
	periods: list[dict],
):
	if (result_mode or "Terminal") == "Annual" and periods:
		return periods[0]["start_date"], periods[-1]["end_date"]
	if academic_term:
		return frappe.db.get_value(
			"Academic Term",
			academic_term,
			["term_start_date", "term_end_date"],
		)
	return frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
	)
