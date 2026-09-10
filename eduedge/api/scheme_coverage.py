from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from eduedge.api.scheme_of_work import _is_manager
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.instructor_assignment_capabilities import assignment_capability_enforcement_enabled
from eduedge.education.instructor_scope import get_active_instructor_names_for_user, is_limited_instructor_user
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access

SCHEME_DOCTYPE = "EduEdge Scheme of Work"
LOG_DOCTYPE = "EduEdge Scheme Delivery Log"
ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"
COVERAGE_STATUSES = (
	"Missing Scheme",
	"Draft Scheme",
	"No Delivery Data",
	"In Progress",
	"Deferred",
	"Completed",
	"Historical",
)
ATTENTION_STATUSES = {"Missing Scheme", "Draft Scheme", "No Delivery Data", "Deferred"}


def _require_reader() -> None:
	if _is_manager() or is_limited_instructor_user():
		return
	frappe.throw(_("You are not permitted to view curriculum coverage."), frappe.PermissionError)


def _exact_limited_instructor() -> str:
	if not is_limited_instructor_user():
		return ""
	instructors = get_active_instructor_names_for_user()
	if len(instructors) != 1:
		frappe.throw(
			_("Your User account must resolve to exactly one active Instructor before curriculum coverage can be viewed."),
			frappe.PermissionError,
		)
	return instructors[0]


def _clean_page_length(value) -> int:
	return min(max(cint(value) or 50, 1), 100)


def _group_context(student_group: str | None) -> dict:
	group_name = str(student_group or "").strip()
	if not group_name:
		return {}
	meta = frappe.get_meta("Student Group")
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", "disabled"]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	row = frappe.db.get_value("Student Group", group_name, fields, as_dict=True)
	return dict(row or {})


def _offering_rows(
	branch: str,
	*,
	academic_year: str = "",
	academic_term: str = "",
	program_offering: str = "",
	include_historical: bool = False,
) -> list[dict]:
	filters: dict[str, Any] = {"school_branch": branch}
	if academic_year:
		filters["academic_year"] = academic_year
	if academic_term:
		filters["academic_term"] = academic_term
	if program_offering:
		filters["name"] = program_offering
	if not include_historical:
		filters["is_active"] = 1
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name", "offering_title", "institution", "school_branch", "program", "academic_year",
			"academic_term", "period_start_date", "period_end_date", "is_active",
		],
		order_by="period_start_date desc, offering_title asc",
		limit_page_length=0,
	)
	return [dict(row) for row in rows]


def _assignment_rows(branch: str, instructor: str = "") -> list[dict]:
	if not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE):
		return []
	filters: dict[str, Any] = {
		"school_branch": branch,
		"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
		"enabled": 1,
	}
	if instructor:
		filters["instructor"] = instructor
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters=filters,
		fields=[
			"name", "instructor", "instructor_name", "program_offering", "assignment_scope",
			"student_group", "course", "valid_from", "valid_to", "can_view_subject_content",
		],
		limit_page_length=0,
	)
	return [dict(row) for row in rows]


def _ranges_overlap(start_a, end_a, start_b, end_b) -> bool:
	minimum = getdate("1900-01-01")
	maximum = getdate("2999-12-31")
	a_start = getdate(start_a) if start_a else minimum
	a_end = getdate(end_a) if end_a else maximum
	b_start = getdate(start_b) if start_b else minimum
	b_end = getdate(end_b) if end_b else maximum
	return a_start <= b_end and b_start <= a_end


def _assignment_applies(
	row: dict,
	*,
	offering: dict,
	course: str,
	student_group: str = "",
	require_view_capability: bool = False,
) -> bool:
	if row.get("program_offering") != offering.get("name") or row.get("course") != course:
		return False
	if not _ranges_overlap(row.get("valid_from"), row.get("valid_to"), offering.get("period_start_date"), offering.get("period_end_date")):
		return False
	scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
	if student_group:
		if scope == CLASS_ARM_SCOPE and row.get("student_group") != student_group:
			return False
		if scope not in {CLASS_SCOPE, CLASS_ARM_SCOPE}:
			return False
	elif scope == CLASS_ARM_SCOPE:
		# A Class Arm assignment can still establish that the Instructor has some
		# responsibility inside the Offering. It must not be treated as Class-wide,
		# but it is valid when the report itself is not narrowed to one Class Arm.
		pass
	elif scope != CLASS_SCOPE:
		return False
	if require_view_capability and not cint(row.get("can_view_subject_content")):
		return False
	return True


def _program_courses(programs: set[str]) -> dict[str, list[str]]:
	if not programs:
		return {}
	rows = frappe.get_all(
		"Program Course",
		filters={"parent": ["in", sorted(programs)], "parenttype": "Program"},
		fields=["parent", "course", "idx"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	)
	result: dict[str, list[str]] = defaultdict(list)
	for row in rows:
		if row.course and row.course not in result[row.parent]:
			result[row.parent].append(row.course)
	return dict(result)


def _scheme_rows(branch: str, offerings: set[str]) -> list[dict]:
	if not offerings:
		return []
	rows = frappe.get_all(
		SCHEME_DOCTYPE,
		filters={"school_branch": branch, "program_offering": ["in", sorted(offerings)]},
		fields=[
			"name", "scheme_title", "status", "version_no", "supersedes_scheme", "institution",
			"school_branch", "program_offering", "student_group", "course", "academic_year",
			"academic_term", "period_start_date", "period_end_date", "offering_title_snapshot",
			"student_group_name_snapshot", "course_name_snapshot", "approved_by", "approved_on",
		],
		order_by="program_offering asc, course asc, student_group asc, version_no desc",
		limit_page_length=0,
	)
	return [dict(row) for row in rows]


def _select_scheme(rows: list[dict]) -> dict | None:
	if not rows:
		return None
	for status in ("Approved", "Draft", "Retired"):
		matching = [row for row in rows if row.get("status") == status]
		if matching:
			return max(matching, key=lambda row: cint(row.get("version_no")))
	return max(rows, key=lambda row: cint(row.get("version_no")))


def _scheme_items(scheme_names: set[str]) -> dict[str, list[dict]]:
	if not scheme_names:
		return {}
	rows = frappe.get_all(
		"EduEdge Scheme of Work Item",
		filters={"parent": ["in", sorted(scheme_names)], "parenttype": SCHEME_DOCTYPE},
		fields=[
			"name", "parent", "sequence", "week_no", "topic", "topic_name_snapshot", "estimated_periods",
		],
		order_by="parent asc, sequence asc, idx asc",
		limit_page_length=0,
	)
	result: dict[str, list[dict]] = defaultdict(list)
	for row in rows:
		result[row.parent].append(dict(row))
	return dict(result)


def _delivery_logs(scheme_names: set[str]) -> dict[str, list[dict]]:
	if not scheme_names or not frappe.db.exists("DocType", LOG_DOCTYPE):
		return {}
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"scheme_of_work": ["in", sorted(scheme_names)]},
		fields=[
			"name", "scheme_of_work", "scheme_item_reference", "delivery_status", "delivered_on",
			"periods_delivered", "instructor", "instructor_assignment", "logged_on", "creation",
		],
		order_by="scheme_of_work asc, logged_on asc, creation asc",
		limit_page_length=0,
	)
	result: dict[str, list[dict]] = defaultdict(list)
	for row in rows:
		result[row.scheme_of_work].append(dict(row))
	return dict(result)


def _coverage_for_scheme(scheme: dict, items: list[dict], logs: list[dict]) -> dict:
	if scheme.get("status") == "Draft":
		status = "Draft Scheme"
	elif scheme.get("status") == "Retired":
		status = "Historical"
	elif not logs:
		status = "No Delivery Data"
	else:
		latest_by_item: dict[str, dict] = {}
		for log in logs:
			latest_by_item[log.get("scheme_item_reference")] = log
		completed = sum(1 for item in items if (latest_by_item.get(item.get("name")) or {}).get("delivery_status") == "Completed")
		deferred = sum(1 for item in items if (latest_by_item.get(item.get("name")) or {}).get("delivery_status") == "Deferred")
		if items and completed == len(items):
			status = "Completed"
		elif deferred:
			status = "Deferred"
		else:
			status = "In Progress"

	latest_by_item = {}
	for log in logs:
		latest_by_item[log.get("scheme_item_reference")] = log
	completed = sum(1 for item in items if (latest_by_item.get(item.get("name")) or {}).get("delivery_status") == "Completed")
	deferred = sum(1 for item in items if (latest_by_item.get(item.get("name")) or {}).get("delivery_status") == "Deferred")
	estimated_periods = sum(max(cint(item.get("estimated_periods")), 0) for item in items)
	delivered_periods = sum(flt(log.get("periods_delivered")) for log in logs)
	instructors = sorted({log.get("instructor") for log in logs if log.get("instructor")})
	return {
		"coverage_status": status,
		"planned_topics": len(items),
		"completed_topics": completed,
		"deferred_topics": deferred,
		"coverage_percent": round((completed / len(items)) * 100, 1) if items else 0,
		"estimated_periods": estimated_periods,
		"delivered_periods": delivered_periods,
		"delivery_instructors": instructors,
		"delivery_log_count": len(logs),
	}


def _instructor_labels(instructor_names: set[str]) -> dict[str, str]:
	if not instructor_names:
		return {}
	rows = frappe.get_all(
		"Instructor",
		filters={"name": ["in", sorted(instructor_names)]},
		fields=["name", "instructor_name"],
		limit_page_length=0,
	)
	return {row.name: row.instructor_name or row.name for row in rows}


def _course_labels(course_names: set[str]) -> dict[str, str]:
	if not course_names:
		return {}
	rows = frappe.get_all(
		"Course",
		filters={"name": ["in", sorted(course_names)]},
		fields=["name", "course_name"],
		limit_page_length=0,
	)
	return {row.name: row.course_name or row.name for row in rows}


def _group_labels(group_names: set[str]) -> dict[str, str]:
	if not group_names:
		return {}
	fields = ["name", "student_group_name"]
	meta = frappe.get_meta("Student Group")
	if meta.has_field("eduedge_display_name"):
		fields.append("eduedge_display_name")
	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", sorted(group_names)]},
		fields=fields,
		limit_page_length=0,
	)
	return {
		row.name: row.get("eduedge_display_name") or row.student_group_name or row.name
		for row in rows
	}


def _status_sort(status: str) -> int:
	order = {
		"Missing Scheme": 0,
		"Deferred": 1,
		"Draft Scheme": 2,
		"No Delivery Data": 3,
		"In Progress": 4,
		"Completed": 5,
		"Historical": 6,
	}
	return order.get(status, 99)


@frappe.whitelist()
def get_scheme_coverage_report(
	school_branch: str,
	academic_year: str | None = None,
	academic_term: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	instructor: str | None = None,
	coverage_status: str | None = None,
	include_historical: int | str = 0,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	"""Return action-oriented curriculum coverage without mutating academic history."""
	require_eduedge_access(feature_key="academics", action="view_scheme_coverage")
	_require_reader()
	branch = str(school_branch or "").strip()
	assert_branch_access(branch)
	requested_status = str(coverage_status or "").strip()
	if requested_status and requested_status not in COVERAGE_STATUSES:
		frappe.throw(_("Select a valid Curriculum Coverage status."), frappe.ValidationError)
	include_history = bool(cint(include_historical))
	group = _group_context(student_group)
	if group and frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
		group_offering = str(group.get(OFFERING_FIELD) or "")
		if program_offering and group_offering and group_offering != program_offering:
			frappe.throw(_("Class Arm does not belong to the selected Class / Programme Offering."), frappe.ValidationError)
		program_offering = program_offering or group_offering

	offerings = _offering_rows(
		branch,
		academic_year=str(academic_year or "").strip(),
		academic_term=str(academic_term or "").strip(),
		program_offering=str(program_offering or "").strip(),
		include_historical=include_history,
	)
	offering_map = {row["name"]: row for row in offerings}
	if not offerings:
		return {
			"filters": {"school_branch": branch},
			"summary": {"contexts": 0, "attention": 0, "missing_schemes": 0, "completed": 0, "average_coverage": 0},
			"rows": [],
			"paging": {"start": 0, "page_length": _clean_page_length(page_length), "has_more": False, "total": 0},
			"options": {"academic_years": [], "academic_terms": [], "instructors": [], "coverage_statuses": list(COVERAGE_STATUSES)},
		}

	limited_instructor = _exact_limited_instructor()
	selected_instructor = limited_instructor or str(instructor or "").strip()
	assignments = _assignment_rows(branch, instructor=selected_instructor)
	require_view_capability = bool(limited_instructor and assignment_capability_enforcement_enabled())
	program_courses = _program_courses({row["program"] for row in offerings if row.get("program")})
	requested_course = str(course or "").strip()
	requested_group = str(student_group or "").strip()

	# Expected contexts are Offering x configured Program Course, narrowed to exact
	# Instructor responsibility where this is a teacher view or a manager Instructor filter.
	expected: list[tuple[dict, str]] = []
	for offering in offerings:
		for subject in program_courses.get(offering.get("program"), []):
			if requested_course and subject != requested_course:
				continue
			if selected_instructor:
				if not any(
					_assignment_applies(
						row,
						offering=offering,
						course=subject,
						student_group=requested_group,
						require_view_capability=require_view_capability,
					)
					for row in assignments
				):
					continue
			expected.append((offering, subject))

	schemes = _scheme_rows(branch, {row[0]["name"] for row in expected})
	course_names = {subject for _, subject in expected}
	group_names = {str(row.get("student_group") or "") for row in schemes if row.get("student_group")}
	course_labels = _course_labels(course_names | {str(row.get("course") or "") for row in schemes if row.get("course")})
	group_labels = _group_labels(group_names)

	schemes_by_context: dict[tuple[str, str], list[dict]] = defaultdict(list)
	for row in schemes:
		if requested_course and row.get("course") != requested_course:
			continue
		row_group = str(row.get("student_group") or "")
		if requested_group and row_group not in {"", requested_group}:
			continue
		schemes_by_context[(row.get("program_offering"), row.get("course"))].append(row)

	selected_schemes = {
		selected["name"]: selected
		for rows in schemes_by_context.values()
		if (selected := _select_scheme(rows))
	}
	items_by_scheme = _scheme_items(set(selected_schemes))
	logs_by_scheme = _delivery_logs(set(selected_schemes))
	all_log_instructors = {
		str(log.get("instructor") or "")
		for logs in logs_by_scheme.values()
		for log in logs
		if log.get("instructor")
	}
	assignment_instructors = {str(row.get("instructor") or "") for row in _assignment_rows(branch) if row.get("instructor")}
	instructor_labels = _instructor_labels(all_log_instructors | assignment_instructors)

	rows: list[dict] = []
	for offering, subject in expected:
		context_key = (offering["name"], subject)
		scheme = _select_scheme(schemes_by_context.get(context_key, []))
		if not scheme:
			coverage = {
				"coverage_status": "Missing Scheme",
				"planned_topics": 0,
				"completed_topics": 0,
				"deferred_topics": 0,
				"coverage_percent": 0,
				"estimated_periods": 0,
				"delivered_periods": 0,
				"delivery_instructors": [],
				"delivery_log_count": 0,
			}
		else:
			coverage = _coverage_for_scheme(
				scheme,
				items_by_scheme.get(scheme["name"], []),
				logs_by_scheme.get(scheme["name"], []),
			)
		if requested_status and coverage["coverage_status"] != requested_status:
			continue
		rows.append(
			{
				"scheme": (scheme or {}).get("name") or "",
				"scheme_title": (scheme or {}).get("scheme_title") or "",
				"scheme_status": (scheme or {}).get("status") or "Not Configured",
				"version_no": cint((scheme or {}).get("version_no")),
				"school_branch": branch,
				"program_offering": offering["name"],
				"offering_label": (scheme or {}).get("offering_title_snapshot") or offering.get("offering_title") or offering["name"],
				"student_group": requested_group or (scheme or {}).get("student_group") or "",
				"student_group_label": group_labels.get(requested_group or (scheme or {}).get("student_group") or "", "Class-wide"),
				"course": subject,
				"course_label": (scheme or {}).get("course_name_snapshot") or course_labels.get(subject, subject),
				"academic_year": offering.get("academic_year") or "",
				"academic_term": offering.get("academic_term") or "",
				"period_start_date": offering.get("period_start_date"),
				"period_end_date": offering.get("period_end_date"),
				"is_active_offering": bool(cint(offering.get("is_active"))),
				**coverage,
				"delivery_instructor_labels": [
					instructor_labels.get(name, name) for name in coverage["delivery_instructors"]
				],
				"needs_attention": coverage["coverage_status"] in ATTENTION_STATUSES,
			}
		)

	rows.sort(
		key=lambda row: (
			_status_sort(row["coverage_status"]),
			str(row.get("academic_year") or ""),
			str(row.get("academic_term") or ""),
			str(row.get("offering_label") or "").lower(),
			str(row.get("course_label") or "").lower(),
		)
	)
	total = len(rows)
	start_value = max(cint(start), 0)
	length = _clean_page_length(page_length)
	page_rows = rows[start_value : start_value + length]
	configured_rows = [row for row in rows if row.get("scheme")]
	coverage_values = [flt(row.get("coverage_percent")) for row in configured_rows if row.get("scheme_status") == "Approved"]

	year_values = sorted({row.get("academic_year") for row in offerings if row.get("academic_year")}, reverse=True)
	term_values = sorted({row.get("academic_term") for row in offerings if row.get("academic_term")})
	manager_instructor_options = []
	if _is_manager():
		manager_instructor_options = [
			{"value": name, "label": instructor_labels.get(name, name)}
			for name in sorted(assignment_instructors, key=lambda value: instructor_labels.get(value, value).lower())
		]

	return {
		"filters": {
			"school_branch": branch,
			"academic_year": str(academic_year or ""),
			"academic_term": str(academic_term or ""),
			"program_offering": str(program_offering or ""),
			"student_group": requested_group,
			"course": requested_course,
			"instructor": selected_instructor,
			"coverage_status": requested_status,
			"include_historical": include_history,
		},
		"summary": {
			"contexts": total,
			"attention": sum(1 for row in rows if row["needs_attention"]),
			"missing_schemes": sum(1 for row in rows if row["coverage_status"] == "Missing Scheme"),
			"completed": sum(1 for row in rows if row["coverage_status"] == "Completed"),
			"in_progress": sum(1 for row in rows if row["coverage_status"] == "In Progress"),
			"deferred": sum(1 for row in rows if row["coverage_status"] == "Deferred"),
			"average_coverage": round(sum(coverage_values) / len(coverage_values), 1) if coverage_values else 0,
		},
		"rows": page_rows,
		"paging": {
			"start": start_value,
			"page_length": length,
			"has_more": start_value + length < total,
			"total": total,
		},
		"options": {
			"academic_years": year_values,
			"academic_terms": term_values,
			"instructors": manager_instructor_options,
			"coverage_statuses": list(COVERAGE_STATUSES),
		},
	}
