from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_scope import get_instructor_identity_states
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"
SCHEME_DOCTYPE = "EduEdge Scheme of Work"
DELIVERY_LOG_DOCTYPE = "EduEdge Scheme Delivery Log"
READINESS_MANAGER_ROLES = {
	"Administrator",
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
}
ATTENTION_TYPES = (
	"Teaching Assignment",
	"Instructor Identity",
	"Scheme of Work",
	"Curriculum Delivery",
)
SCHEME_ATTENTION_STATUSES = {"Missing", "Draft Only", "Retired Only"}
DELIVERY_ATTENTION_STATUSES = {"No Delivery Data", "Deferred"}


def _require_manager() -> None:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	roles = set(frappe.get_roles(user)) | {user}
	if not READINESS_MANAGER_ROLES.intersection(roles):
		frappe.throw(_("Academic readiness intelligence is available to academic management roles."), frappe.PermissionError)


def _allowed_branches() -> list[dict]:
	return [dict(row) for row in (get_allowed_school_branches() or []) if row.get("name")]


def _resolve_branch(branch: str | None) -> tuple[str, list[dict]]:
	branches = _allowed_branches()
	allowed = {row["name"] for row in branches}
	current = get_current_school_branch() or {}
	value = str(branch or current.get("name") or "").strip()
	if not value and len(allowed) == 1:
		value = next(iter(allowed))
	if not value or value not in allowed:
		frappe.throw(_("Select a permitted Branch / Campus."), frappe.PermissionError)
	assert_branch_access(value)
	return value, branches


def _offering_rows(
	branch: str,
	*,
	academic_year: str = "",
	academic_term: str = "",
	include_historical: bool = False,
) -> list[dict]:
	filters: dict[str, Any] = {"school_branch": branch}
	if academic_year:
		filters["academic_year"] = academic_year
	if academic_term:
		filters["academic_term"] = academic_term
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


def _group_rows(branch: str, offerings: list[dict], *, include_historical: bool = False) -> list[dict]:
	if not offerings:
		return []
	meta = frappe.get_meta("Student Group")
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", "disabled", BRANCH_FIELD]
	if meta.has_field(OFFERING_FIELD):
		fields.append(OFFERING_FIELD)
	if meta.has_field("eduedge_display_name"):
		fields.append("eduedge_display_name")
	filters: dict[str, Any] = {BRANCH_FIELD: branch}
	if not include_historical:
		filters["disabled"] = 0
	rows = frappe.get_all("Student Group", filters=filters, fields=fields, limit_page_length=0)
	offering_names = {row["name"] for row in offerings}
	offering_by_fallback: dict[tuple[str, str, str], list[str]] = defaultdict(list)
	for offering in offerings:
		offering_by_fallback[
			(
				str(offering.get("program") or ""),
				str(offering.get("academic_year") or ""),
				str(offering.get("academic_term") or ""),
			)
		].append(offering["name"])
	result = []
	for row in rows:
		value = dict(row)
		offering = str(value.get(OFFERING_FIELD) or "") if meta.has_field(OFFERING_FIELD) else ""
		if not offering:
			matches = offering_by_fallback.get(
				(
					str(value.get("program") or ""),
					str(value.get("academic_year") or ""),
					str(value.get("academic_term") or ""),
				),
				[],
			)
			offering = matches[0] if len(matches) == 1 else ""
		if offering not in offering_names:
			continue
		value["resolved_offering"] = offering
		value["label"] = value.get("eduedge_display_name") or value.get("student_group_name") or value["name"]
		result.append(value)
	return result


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


def _date_overlap(start_a, end_a, start_b, end_b) -> bool:
	minimum = getdate("1900-01-01")
	maximum = getdate("2999-12-31")
	a_start = getdate(start_a) if start_a else minimum
	a_end = getdate(end_a) if end_a else maximum
	b_start = getdate(start_b) if start_b else minimum
	b_end = getdate(end_b) if end_b else maximum
	return a_start <= b_end and b_start <= a_end


def _expected_contexts(offerings: list[dict], groups: list[dict]) -> list[dict]:
	groups_by_offering: dict[str, list[dict]] = defaultdict(list)
	for group in groups:
		groups_by_offering[group["resolved_offering"]].append(group)
	program_courses = _program_courses({row.get("program") for row in offerings if row.get("program")})
	courses = {course for values in program_courses.values() for course in values}
	course_labels = _course_labels(courses)
	contexts: list[dict] = []
	for offering in offerings:
		subjects = program_courses.get(offering.get("program"), [])
		offering_groups = groups_by_offering.get(offering["name"], [])
		group_targets = offering_groups or [{"name": "", "label": "Class-wide"}]
		for group in group_targets:
			for course in subjects:
				contexts.append(
					{
						"school_branch": offering["school_branch"],
						"institution": offering.get("institution") or "",
						"program_offering": offering["name"],
						"offering_label": offering.get("offering_title") or offering["name"],
						"program": offering.get("program") or "",
						"academic_year": offering.get("academic_year") or "",
						"academic_term": offering.get("academic_term") or "",
						"period_start_date": offering.get("period_start_date"),
						"period_end_date": offering.get("period_end_date"),
						"student_group": group.get("name") or "",
						"student_group_label": group.get("label") or "Class-wide",
						"course": course,
						"course_label": course_labels.get(course, course),
					}
				)
	return contexts


def _assignment_rows(branch: str, offering_names: set[str]) -> list[dict]:
	if not offering_names or not frappe.db.exists("DocType", ASSIGNMENT_DOCTYPE):
		return []
	rows = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			"school_branch": branch,
			"program_offering": ["in", sorted(offering_names)],
			"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
			"enabled": 1,
		},
		fields=[
			"name", "assignment_title", "instructor", "instructor_name", "assignment_type", "assignment_scope",
			"program_offering", "student_group", "course", "valid_from", "valid_to",
		],
		limit_page_length=0,
	)
	return [dict(row) for row in rows]


def _assignment_matches_context(row: dict, context: dict) -> bool:
	if row.get("program_offering") != context["program_offering"] or row.get("course") != context["course"]:
		return False
	if not _date_overlap(
		row.get("valid_from"),
		row.get("valid_to"),
		context.get("period_start_date"),
		context.get("period_end_date"),
	):
		return False
	scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
	if context["student_group"]:
		return scope == CLASS_SCOPE or (scope == CLASS_ARM_SCOPE and row.get("student_group") == context["student_group"])
	return scope == CLASS_SCOPE


def _scheme_rows(branch: str, offering_names: set[str]) -> list[dict]:
	if not offering_names or not frappe.db.exists("DocType", SCHEME_DOCTYPE):
		return []
	rows = frappe.get_all(
		SCHEME_DOCTYPE,
		filters={"school_branch": branch, "program_offering": ["in", sorted(offering_names)]},
		fields=[
			"name", "scheme_title", "status", "version_no", "program_offering", "student_group", "course",
			"course_name_snapshot", "offering_title_snapshot", "student_group_name_snapshot",
		],
		order_by="program_offering asc, course asc, student_group asc, version_no desc",
		limit_page_length=0,
	)
	return [dict(row) for row in rows]


def _select_scheme_for_context(rows: list[dict], context: dict) -> dict | None:
	applicable = [
		row
		for row in rows
		if row.get("program_offering") == context["program_offering"]
		and row.get("course") == context["course"]
		and (not row.get("student_group") or row.get("student_group") == context["student_group"])
	]
	if not applicable:
		return None
	group = context["student_group"]
	priority = {
		("Approved", True): 0,
		("Approved", False): 1,
		("Draft", True): 2,
		("Draft", False): 3,
		("Retired", True): 4,
		("Retired", False): 5,
	}
	return min(
		applicable,
		key=lambda row: (
			priority.get((row.get("status"), bool(group and row.get("student_group") == group)), 99),
			-cint(row.get("version_no")),
		),
	)


def _scheme_items(scheme_names: set[str]) -> dict[str, list[dict]]:
	if not scheme_names:
		return {}
	rows = frappe.get_all(
		"EduEdge Scheme of Work Item",
		filters={"parent": ["in", sorted(scheme_names)], "parenttype": SCHEME_DOCTYPE},
		fields=["name", "parent", "estimated_periods"],
		limit_page_length=0,
	)
	result: dict[str, list[dict]] = defaultdict(list)
	for row in rows:
		result[row.parent].append(dict(row))
	return dict(result)


def _delivery_logs(scheme_names: set[str]) -> dict[str, list[dict]]:
	if not scheme_names or not frappe.db.exists("DocType", DELIVERY_LOG_DOCTYPE):
		return {}
	rows = frappe.get_all(
		DELIVERY_LOG_DOCTYPE,
		filters={"scheme_of_work": ["in", sorted(scheme_names)]},
		fields=[
			"name", "scheme_of_work", "scheme_item_reference", "delivery_status", "periods_delivered",
			"instructor", "logged_on", "creation",
		],
		order_by="scheme_of_work asc, logged_on asc, creation asc",
		limit_page_length=0,
	)
	result: dict[str, list[dict]] = defaultdict(list)
	for row in rows:
		result[row.scheme_of_work].append(dict(row))
	return dict(result)


def _delivery_state(items: list[dict], logs: list[dict]) -> dict:
	if not logs:
		return {"status": "No Delivery Data", "coverage_percent": 0, "completed": 0, "planned": len(items)}
	latest: dict[str, dict] = {}
	for row in logs:
		latest[row.get("scheme_item_reference")] = row
	completed = sum(1 for item in items if (latest.get(item["name"]) or {}).get("delivery_status") == "Completed")
	deferred = sum(1 for item in items if (latest.get(item["name"]) or {}).get("delivery_status") == "Deferred")
	if items and completed == len(items):
		status = "Completed"
	elif deferred:
		status = "Deferred"
	else:
		status = "In Progress"
	return {
		"status": status,
		"coverage_percent": round((completed / len(items)) * 100, 1) if items else 0,
		"completed": completed,
		"planned": len(items),
	}


def _assessment_metrics(branch: str, group_names: set[str], academic_year: str = "", academic_term: str = "") -> dict:
	filters: dict[str, Any] = {BRANCH_FIELD: branch, "docstatus": ["!=", 2]}
	if group_names:
		filters["student_group"] = ["in", sorted(group_names)]
	if academic_year:
		filters["academic_year"] = academic_year
	if academic_term:
		filters["academic_term"] = academic_term
	rows = frappe.get_all(
		"Assessment Plan",
		filters=filters,
		fields=["name", "student_group", "course", "docstatus"],
		limit_page_length=0,
	)
	return {
		"assessment_plans": len(rows),
		"draft_assessment_plans": sum(1 for row in rows if cint(row.docstatus) == 0),
		"submitted_assessment_plans": sum(1 for row in rows if cint(row.docstatus) == 1),
	}


def _student_count(group_names: set[str]) -> int:
	if not group_names:
		return 0
	return len(
		set(
			frappe.get_all(
				"Student Group Student",
				filters={"parent": ["in", sorted(group_names)], "parenttype": "Student Group", "active": 1},
				pluck="student",
				limit_page_length=0,
			)
		)
	)


def _attention_route(row_type: str, context: dict | None = None, instructor: str = "", scheme: str = "") -> dict:
	context = context or {}
	if row_type in {"Teaching Assignment", "Instructor Identity"}:
		return {
			"route": "/app/eduedge-instructor-assignments",
			"query": {
				"branch": context.get("school_branch") or "",
				"offering": context.get("program_offering") or "",
				"course": context.get("course") or "",
				"instructor": instructor,
			},
		}
	return {
		"route": "/app/eduedge-scheme-of-work",
		"query": {
			"branch": context.get("school_branch") or "",
			"offering": context.get("program_offering") or "",
			"student_group": context.get("student_group") or "",
			"course": context.get("course") or "",
			"scheme": scheme,
		},
	}


def _attention_row(
	row_type: str,
	title: str,
	detail: str,
	*,
	severity: str,
	context: dict | None = None,
	instructor: str = "",
	scheme: str = "",
) -> dict:
	return {
		"type": row_type,
		"severity": severity,
		"title": title,
		"detail": detail,
		**_attention_route(row_type, context=context, instructor=instructor, scheme=scheme),
	}


def _page_length(value) -> int:
	return min(max(cint(value) or 50, 1), 100)


@frappe.whitelist()
def get_academic_readiness(
	school_branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	attention_type: str | None = None,
	include_historical: int | str = 0,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	"""Return management readiness signals without inventing a single opaque score."""
	_require_manager()
	require_eduedge_access(feature_key="academics", action="view_academic_readiness")
	branch, branches = _resolve_branch(school_branch)
	requested_type = str(attention_type or "").strip()
	if requested_type and requested_type not in ATTENTION_TYPES:
		frappe.throw(_("Select a valid Academic Readiness attention type."), frappe.ValidationError)
	include_history = bool(cint(include_historical))
	year = str(academic_year or "").strip()
	term = str(academic_term or "").strip()

	all_branch_offerings = _offering_rows(branch, include_historical=True)
	available_years = sorted({row.get("academic_year") for row in all_branch_offerings if row.get("academic_year")}, reverse=True)
	available_terms = sorted(
		{
			row.get("academic_term")
			for row in all_branch_offerings
			if row.get("academic_term") and (not year or row.get("academic_year") == year)
		}
	)
	if year and year not in available_years:
		frappe.throw(_("Select an Academic Session available in this Branch."), frappe.ValidationError)
	if term and term not in available_terms:
		frappe.throw(_("Select a Term / Semester available in the selected Academic Session."), frappe.ValidationError)

	offerings = _offering_rows(
		branch,
		academic_year=year,
		academic_term=term,
		include_historical=include_history,
	)
	groups = _group_rows(branch, offerings, include_historical=include_history)
	contexts = _expected_contexts(offerings, groups)
	offering_names = {row["name"] for row in offerings}
	assignments = _assignment_rows(branch, offering_names)
	assignments_by_context: dict[tuple[str, str], list[dict]] = defaultdict(list)
	for row in assignments:
		assignments_by_context[(row.get("program_offering"), row.get("course"))].append(row)

	attention: list[dict] = []
	covered_contexts = 0
	context_instructors: set[str] = set()
	for context in contexts:
		matched = [
			row
			for row in assignments_by_context.get((context["program_offering"], context["course"]), [])
			if _assignment_matches_context(row, context)
		]
		if matched:
			covered_contexts += 1
			context_instructors.update(row.get("instructor") for row in matched if row.get("instructor"))
			continue
		attention.append(
			_attention_row(
				"Teaching Assignment",
				_("No Instructor assigned: {0} · {1}").format(context["offering_label"], context["course_label"]),
				_("{0} has no effective Subject Instructor Assignment covering {1} for this academic period.").format(
					context["student_group_label"], context["course_label"]
				),
				severity="high",
				context=context,
			)
		)

	identity_states = get_instructor_identity_states(sorted(context_instructors))
	identity_ready = 0
	for instructor in sorted(context_instructors):
		state = identity_states.get(instructor) or {}
		if state.get("operational_ready"):
			identity_ready += 1
			continue
		name = frappe.db.get_value("Instructor", instructor, "instructor_name") or instructor
		attention.append(
			_attention_row(
				"Instructor Identity",
				_("Teaching identity needs attention: {0}").format(name),
				state.get("message") or _("User → Employee → Instructor identity is not operationally ready."),
				severity="high" if state.get("severity") == "danger" else "medium",
				instructor=instructor,
			)
		)

	schemes = _scheme_rows(branch, offering_names)
	selected_schemes: dict[str, dict] = {}
	scheme_context_status: dict[int, str] = {}
	approved_scheme_contexts = 0
	for index, context in enumerate(contexts):
		scheme = _select_scheme_for_context(schemes, context)
		if not scheme:
			status = "Missing"
		elif scheme.get("status") == "Approved":
			status = "Approved"
			approved_scheme_contexts += 1
			selected_schemes[scheme["name"]] = scheme
		elif scheme.get("status") == "Draft":
			status = "Draft Only"
		else:
			status = "Retired Only"
		scheme_context_status[index] = status
		if status in SCHEME_ATTENTION_STATUSES:
			label = context["course_label"]
			attention.append(
				_attention_row(
					"Scheme of Work",
					_("{0} Scheme: {1} · {2}").format(status, context["offering_label"], label),
					_("{0} · {1} does not yet have an Approved Scheme of Work governing this academic context.").format(
						context["student_group_label"], label
					),
					severity="medium",
					context=context,
					scheme=(scheme or {}).get("name") or "",
				)
			)

	items_by_scheme = _scheme_items(set(selected_schemes))
	logs_by_scheme = _delivery_logs(set(selected_schemes))
	delivery_status_counts: dict[str, int] = defaultdict(int)
	coverage_values: list[float] = []
	seen_delivery_attention: set[tuple[str, str]] = set()
	for context in contexts:
		scheme = _select_scheme_for_context(schemes, context)
		if not scheme or scheme.get("status") != "Approved":
			continue
		state = _delivery_state(items_by_scheme.get(scheme["name"], []), logs_by_scheme.get(scheme["name"], []))
		delivery_status_counts[state["status"]] += 1
		coverage_values.append(flt(state["coverage_percent"]))
		attention_key = (scheme["name"], state["status"])
		if state["status"] not in DELIVERY_ATTENTION_STATUSES or attention_key in seen_delivery_attention:
			continue
		seen_delivery_attention.add(attention_key)
		attention.append(
			_attention_row(
				"Curriculum Delivery",
				_("{0}: {1}").format(state["status"], scheme.get("scheme_title") or context["course_label"]),
				_("Approved Scheme delivery is at {0}% coverage ({1}/{2} Topics completed).").format(
					state["coverage_percent"], state["completed"], state["planned"]
				),
				severity="high" if state["status"] == "Deferred" else "medium",
				context=context,
				scheme=scheme["name"],
			)
		)

	group_names = {row["name"] for row in groups}
	assessment = _assessment_metrics(branch, group_names, academic_year=year, academic_term=term)
	student_count = _student_count(group_names)

	if requested_type:
		attention = [row for row in attention if row["type"] == requested_type]
	severity_order = {"high": 0, "medium": 1, "low": 2}
	attention.sort(key=lambda row: (severity_order.get(row["severity"], 99), row["type"], row["title"].lower()))
	length = _page_length(page_length)
	start_value = max(cint(start), 0)
	total_attention = len(attention)
	page_attention = attention[start_value : start_value + length]

	expected_count = len(contexts)
	return {
		"filters": {
			"school_branch": branch,
			"academic_year": year,
			"academic_term": term,
			"attention_type": requested_type,
			"include_historical": include_history,
		},
		"allowed_branches": branches,
		"options": {
			"academic_years": available_years,
			"academic_terms": available_terms,
			"attention_types": list(ATTENTION_TYPES),
		},
		"summary": {
			"offerings": len(offerings),
			"class_groups": len(groups),
			"students": student_count,
			"expected_teaching_contexts": expected_count,
			"assigned_teaching_contexts": covered_contexts,
			"unassigned_teaching_contexts": max(expected_count - covered_contexts, 0),
			"teaching_assignment_coverage": round((covered_contexts / expected_count) * 100, 1) if expected_count else 0,
			"instructors_in_scope": len(context_instructors),
			"identity_ready": identity_ready,
			"identity_attention": max(len(context_instructors) - identity_ready, 0),
			"approved_scheme_contexts": approved_scheme_contexts,
			"scheme_approval_coverage": round((approved_scheme_contexts / expected_count) * 100, 1) if expected_count else 0,
			"average_delivery_coverage": round(sum(coverage_values) / len(coverage_values), 1) if coverage_values else 0,
			"delivery_completed_contexts": delivery_status_counts.get("Completed", 0),
			"delivery_deferred_contexts": delivery_status_counts.get("Deferred", 0),
			"delivery_no_data_contexts": delivery_status_counts.get("No Delivery Data", 0),
			**assessment,
		},
		"attention": page_attention,
		"paging": {
			"start": start_value,
			"page_length": length,
			"has_more": start_value + length < total_attention,
			"total": total_attention,
		},
		"notes": {
			"assessment_planning": _("Assessment counts show recorded planning activity only; EduEdge does not infer a missing Assessment Plan without an Institution assessment policy."),
			"readiness_score": _("No single readiness score is calculated. Each signal remains independently auditable and actionable."),
		},
	}
