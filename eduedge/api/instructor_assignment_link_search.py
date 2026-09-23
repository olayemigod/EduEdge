from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import instructor_assignments as assignments
from eduedge.api import teacher_assignments as core
from eduedge.api.fuzzy_search import get_bounded_candidates, rank_link_rows
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import current_user_instructors
from eduedge.services.instructor_branch_governance import (
	assignment_eligibility_covers_period,
	assignment_eligibility_overlap_periods,
	assignment_eligibility_overlaps_period,
	eligible_branch_names,
)

MAX_RESULTS = 50


def _limit(value: int | str | None) -> int:
	return min(max(cint(value) or 20, 1), MAX_RESULTS)


def _allowed_branch_map() -> dict[str, dict]:
	return {row["name"]: row for row in core._allowed_branches()}


def _assert_search_instructor_available(instructor: str) -> str:
	resolved = str(instructor or "").strip()
	if not resolved:
		return ""
	if not assignments._can_manage_assignments():
		own = set(current_user_instructors())
		if resolved not in own:
			frappe.throw("The selected Instructor is not available to your user.", frappe.PermissionError)
	doc = frappe.get_doc("Instructor", resolved)
	doc.check_permission("read")
	if str(doc.status or "") != "Active":
		frappe.throw("Select an active Instructor.", frappe.ValidationError)
	return resolved


def _offering_available_for_instructor(instructor: str, branch: str, offering) -> bool:
	resolved_instructor = str(instructor or "").strip()
	if not resolved_instructor:
		return True
	period_start, period_end = assignments._period_dates(
		offering.get("academic_year"),
		offering.get("academic_term"),
	)
	return assignment_eligibility_overlaps_period(
		resolved_instructor,
		branch,
		period_start,
		period_end,
	)


def _assert_offering_period_governance(instructor: str, branch: str, offering) -> None:
	if _offering_available_for_instructor(instructor, branch, offering):
		return
	frappe.throw(
		"The selected Class / Programme Offering does not overlap this Instructor's Branch Governance eligibility period.",
		frappe.ValidationError,
	)


def _validated_offering(branch: str, program_offering: str):
	allowed = _allowed_branch_map()
	if branch not in allowed:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	core.assert_branch_access(branch)
	offering = frappe.db.get_value(
		"EduEdge Program Offering",
		program_offering,
		[
			"name",
			"school_branch",
			"program",
			"academic_year",
			"academic_term",
			"institution",
			"is_active",
		],
		as_dict=True,
	)
	if not offering or not cint(offering.is_active) or offering.school_branch != branch:
		frappe.throw(
			"Select an active Class / Programme Offering for this Branch.",
			frappe.ValidationError,
		)
	return offering


@frappe.whitelist()
def search_instructors(query: str = "", page_length: int | str = 20) -> list[dict]:
	core._require_read()
	filters: dict = {"status": "Active"}
	if assignments._can_manage_assignments():
		visible = assignments._manager_visible_instructor_names(include_history=False)
		filters["name"] = ["in", sorted(visible)] if visible else ["in", ["__none__"]]
	else:
		own = current_user_instructors()
		filters["name"] = ["in", own] if own else ["in", ["__none__"]]
	meta = frappe.get_meta("Instructor")
	fields = ["name", "instructor_name", "department", "employee"]
	search_fields = ["instructor_name", "department", "employee"]
	for fieldname in (INSTITUTION_FIELD, "eduedge_email", "eduedge_mobile"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
			search_fields.append(fieldname)
	rows = get_bounded_candidates(
		"Instructor",
		filters=filters,
		fields=fields,
		query=query,
		search_fields=tuple(search_fields),
		order_by="instructor_name asc",
	)
	institutions = {
		row.name: row.institution_name
		for row in frappe.get_list(
			"EduEdge Institution",
			fields=["name", "institution_name"],
			page_length=100,
		)
	}
	candidates = []
	for source in rows:
		row = dict(source)
		institution_name = institutions.get(row.get(INSTITUTION_FIELD)) or row.get(INSTITUTION_FIELD)
		row["value"] = row.get("name")
		row["label"] = row.get("instructor_name") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				institution_name,
				row.get("department"),
				row.get("eduedge_mobile"),
				row.get("eduedge_email"),
			)
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value", "eduedge_mobile", "eduedge_email"),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_assignment_offerings(
	branch: str,
	query: str = "",
	page_length: int | str = 20,
	instructor: str | None = None,
) -> list[dict]:
	core._require_read()
	allowed = _allowed_branch_map()
	if branch not in allowed:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	core.assert_branch_access(branch)
	if instructor:
		resolved_instructor = _assert_search_instructor_available(instructor)
		_assert_governed_branch(resolved_instructor, branch)
	rows = get_bounded_candidates(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "is_active": 1},
		fields=[
			"name",
			"offering_title",
			"offering_code",
			"program",
			"academic_year",
			"academic_term",
			"institution",
			"school_branch",
		],
		query=query,
		search_fields=("offering_title", "offering_code", "program", "academic_year", "academic_term"),
		order_by="academic_year desc, offering_title asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["period_start_date"], row["period_end_date"] = assignments._period_dates(
			row.get("academic_year"), row.get("academic_term")
		)
		if instructor and not _offering_available_for_instructor(resolved_instructor, branch, row):
			continue
		if instructor:
			row["branch_eligibility_full_period"] = assignment_eligibility_covers_period(
				resolved_instructor,
				branch,
				row.get("period_start_date"),
				row.get("period_end_date"),
			)
			row["branch_eligibility_periods"] = assignment_eligibility_overlap_periods(
				resolved_instructor,
				branch,
				row.get("period_start_date"),
				row.get("period_end_date"),
			)
		row["value"] = row.get("name")
		row["label"] = row.get("offering_title") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("offering_code"),
				row.get("program"),
				row.get("academic_year"),
				row.get("academic_term"),
				(
					"Partial Branch Eligibility — set assignment dates within the governed period"
					if instructor and row.get("branch_eligibility_full_period") is False
					else None
				),
			)
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value", "offering_code"),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_assignment_class_arms(
	branch: str,
	program_offering: str,
	query: str = "",
	page_length: int | str = 20,
	instructor: str | None = None,
) -> list[dict]:
	core._require_read()
	offering = _validated_offering(branch, program_offering)
	if instructor:
		resolved_instructor = _assert_search_instructor_available(instructor)
		_assert_governed_branch(resolved_instructor, branch)
		_assert_offering_period_governance(resolved_instructor, branch, offering)
	filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	meta = frappe.get_meta("Student Group")
	if meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = program_offering
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD]
	search_fields = ["student_group_name", "program", "academic_year", "academic_term"]
	for fieldname in ("eduedge_display_name", OFFERING_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
			search_fields.append(fieldname)
	rows = get_bounded_candidates(
		"Student Group",
		filters=filters,
		fields=fields,
		query=query,
		search_fields=tuple(search_fields),
		order_by="student_group_name asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		if row.get("program") and row.get("program") != offering.program:
			continue
		if row.get("academic_year") and row.get("academic_year") != offering.academic_year:
			continue
		if row.get("academic_term") and row.get("academic_term") != offering.academic_term:
			continue
		row["value"] = row.get("name")
		row["label"] = row.get("eduedge_display_name") or row.get("student_group_name") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (row.get("program"), row.get("academic_year"), row.get("academic_term"))
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value",),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_assignment_courses(
	branch: str,
	program_offering: str,
	query: str = "",
	page_length: int | str = 20,
	instructor: str | None = None,
) -> list[dict]:
	core._require_read()
	offering = _validated_offering(branch, program_offering)
	if instructor:
		resolved_instructor = _assert_search_instructor_available(instructor)
		_assert_governed_branch(resolved_instructor, branch)
		_assert_offering_period_governance(resolved_instructor, branch, offering)
	meta = frappe.get_meta("Course")
	fields = ["name", "course_name"]
	filters: dict = {}
	search_fields = ["course_name"]
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
		search_fields.append(INSTITUTION_FIELD)
		if offering.institution:
			filters[INSTITUTION_FIELD] = ["in", [offering.institution, ""]]
	rows = get_bounded_candidates(
		"Course",
		filters=filters,
		fields=fields,
		query=query,
		search_fields=tuple(search_fields),
		order_by="course_name asc",
	)
	configured = core._course_membership({offering.program}).get(offering.program, set())
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("course_name") or row.get("name")
		row["in_program"] = row.get("name") in configured
		row["description"] = " · ".join(
			value
			for value in (
				"In Class curriculum" if row["in_program"] else "Available Institution course",
				row.get(INSTITUTION_FIELD) or "",
			)
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value",),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)

def _standard_filters(filters) -> dict:
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return dict(filters or {})


def _slice_query_rows(rows: list[list], start, page_len) -> list[list]:
	resolved_start = max(cint(start), 0)
	resolved_length = _limit(page_len)
	return rows[resolved_start : resolved_start + resolved_length]


def _assert_governed_branch(instructor: str, branch: str) -> dict:
	resolved_instructor = str(instructor or "").strip()
	resolved_branch = str(branch or "").strip()
	if not resolved_instructor or not resolved_branch:
		frappe.throw("Select an Instructor and governed Branch first.", frappe.ValidationError)
	allowed = _allowed_branch_map()
	if resolved_branch not in allowed:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	governed = eligible_branch_names(resolved_instructor, within=allowed.keys())
	if resolved_branch not in governed:
		frappe.throw(
			"The selected Branch is not covered by this Instructor's Branch Governance eligibility.",
			frappe.PermissionError,
		)
	return allowed[resolved_branch]


@frappe.whitelist()
def get_assignment_offering_context(
	instructor: str,
	branch: str,
	program_offering: str,
) -> dict:
	"""Return the server-governed Offering context used by the native assignment form."""
	assignments._require_assignment_manager()
	resolved_instructor = _assert_search_instructor_available(instructor)
	_assert_governed_branch(resolved_instructor, branch)
	offering = _validated_offering(branch, program_offering)
	_assert_offering_period_governance(resolved_instructor, branch, offering)
	period_start, period_end = assignments._period_dates(
		offering.academic_year,
		offering.academic_term,
	)
	return {
		"name": offering.name,
		"institution": offering.institution,
		"school_branch": offering.school_branch,
		"academic_year": offering.academic_year,
		"academic_term": offering.academic_term,
		"period_start_date": str(period_start or ""),
		"period_end_date": str(period_end or ""),
		"branch_eligibility_full_period": assignment_eligibility_covers_period(
			resolved_instructor,
			branch,
			period_start,
			period_end,
		),
		"branch_eligibility_periods": assignment_eligibility_overlap_periods(
			resolved_instructor,
			branch,
			period_start,
			period_end,
		),
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_assignment_instructor_query(doctype, txt, searchfield, start, page_len, filters):
	"""Native-form Instructor choices that can actually receive governed responsibilities."""
	assignments._require_assignment_manager()
	allowed = _allowed_branch_map()
	if not allowed:
		return []
	candidates = search_instructors(txt or "", page_length=MAX_RESULTS)
	if not candidates:
		return []
	candidate_names = [row.get("value") for row in candidates if row.get("value")]
	home_institutions = {
		str(row.get(INSTITUTION_FIELD) or "").strip()
		for row in candidates
		if str(row.get(INSTITUTION_FIELD) or "").strip()
	}
	enabled_institutions = set(
		frappe.get_all(
			"EduEdge Institution",
			filters={"name": ["in", sorted(home_institutions)], "enabled": 1},
			pluck="name",
			limit_page_length=0,
		)
	) if home_institutions else set()
	eligibility_rows = frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={
			"instructor": ["in", candidate_names],
			"school_branch": ["in", sorted(allowed)],
			"enabled": 1,
		},
		fields=["instructor", "school_branch"],
		limit_page_length=0,
	) if candidate_names else []
	eligible_by_instructor: dict[str, set[str]] = {}
	for row in eligibility_rows:
		eligible_by_instructor.setdefault(str(row.instructor), set()).add(str(row.school_branch))

	result = []
	for row in candidates:
		instructor = str(row.get("value") or "")
		home = str(row.get(INSTITUTION_FIELD) or "").strip()
		if not instructor or not home or home not in enabled_institutions:
			continue
		matching_branch = any(
			str(allowed.get(branch, {}).get("institution") or "").strip() == home
			for branch in eligible_by_instructor.get(instructor, set())
		)
		if not matching_branch:
			continue
		result.append(
			[
				instructor,
				row.get("label") or instructor,
				row.get("description") or "",
				home,
			]
		)
	return _slice_query_rows(result, start, page_len)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_assignment_branch_query(doctype, txt, searchfield, start, page_len, filters):
	assignments._require_assignment_manager()
	values = _standard_filters(filters)
	instructor = str(values.get("instructor") or "").strip()
	if not instructor:
		return []
	allowed = _allowed_branch_map()
	governed = eligible_branch_names(instructor, within=allowed.keys())
	needle = str(txt or "").strip().lower()
	rows = []
	for name in sorted(governed):
		row = allowed.get(name) or {}
		haystack = " ".join(
			str(value or "")
			for value in (
				name,
				row.get("branch_name"),
				row.get("branch_code"),
				row.get("institution_name"),
				row.get("institution"),
				row.get("company"),
			)
		).lower()
		if needle and needle not in haystack:
			continue
		rows.append(
			[
				name,
				row.get("branch_name") or name,
				row.get("institution_name") or row.get("institution") or "",
				row.get("company") or "",
			]
		)
	return _slice_query_rows(rows, start, page_len)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_assignment_offering_query(doctype, txt, searchfield, start, page_len, filters):
	assignments._require_assignment_manager()
	values = _standard_filters(filters)
	instructor = str(values.get("instructor") or "").strip()
	branch = str(values.get("school_branch") or "").strip()
	if not instructor or not branch:
		return []
	_assert_governed_branch(instructor, branch)
	rows = search_assignment_offerings(branch, instructor=instructor, query=txt or "", page_length=MAX_RESULTS)
	return _slice_query_rows(
		[
			[
				row.get("value"),
				row.get("label") or row.get("value"),
				row.get("program") or "",
				row.get("academic_year") or "",
				row.get("academic_term") or "",
			]
			for row in rows
			if row.get("value")
		],
		start,
		page_len,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_assignment_class_arm_query(doctype, txt, searchfield, start, page_len, filters):
	assignments._require_assignment_manager()
	values = _standard_filters(filters)
	instructor = str(values.get("instructor") or "").strip()
	branch = str(values.get("school_branch") or "").strip()
	offering = str(values.get("program_offering") or "").strip()
	if not instructor or not branch or not offering:
		return []
	_assert_governed_branch(instructor, branch)
	rows = search_assignment_class_arms(branch, offering, instructor=instructor, query=txt or "", page_length=MAX_RESULTS)
	return _slice_query_rows(
		[
			[
				row.get("value"),
				row.get("label") or row.get("value"),
				row.get("program") or "",
				row.get("academic_year") or "",
				row.get("academic_term") or "",
			]
			for row in rows
			if row.get("value")
		],
		start,
		page_len,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_assignment_course_query(doctype, txt, searchfield, start, page_len, filters):
	"""Native form exposes only curriculum courses; planner-only curriculum additions stay on EdgeSuite."""
	assignments._require_assignment_manager()
	values = _standard_filters(filters)
	instructor = str(values.get("instructor") or "").strip()
	branch = str(values.get("school_branch") or "").strip()
	program_offering = str(values.get("program_offering") or "").strip()
	if not instructor or not branch or not program_offering:
		return []
	_assert_governed_branch(instructor, branch)
	offering = _validated_offering(branch, program_offering)
	_assert_offering_period_governance(instructor, branch, offering)
	configured = core._course_membership({offering.program}).get(offering.program, set())
	if not configured:
		return []
	meta = frappe.get_meta("Course")
	fields = ["name", "course_name"]
	search_fields = ["course_name"]
	filters_dict: dict = {"name": ["in", sorted(configured)]}
	if meta.has_field("department"):
		fields.append("department")
		search_fields.append("department")
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
		search_fields.append(INSTITUTION_FIELD)
		if offering.institution:
			filters_dict[INSTITUTION_FIELD] = ["in", [offering.institution, ""]]
	rows = get_bounded_candidates(
		"Course",
		filters=filters_dict,
		fields=fields,
		query=txt or "",
		search_fields=tuple(search_fields),
		order_by="course_name asc",
	)
	ranked = rank_link_rows(
		[
			{
				**dict(row),
				"value": row.get("name"),
				"label": row.get("course_name") or row.get("name"),
				"description": " · ".join(
					str(value)
					for value in (row.get("department"), row.get(INSTITUTION_FIELD))
					if value
				),
			}
			for row in rows
		],
		str(txt or "").strip(),
		exact_fields=("value",),
		search_fields=("label", "description"),
		page_length=MAX_RESULTS,
	)
	return _slice_query_rows(
		[
			[
				row.get("value"),
				row.get("label") or row.get("value"),
				row.get("description") or "",
			]
			for row in ranked
			if row.get("value")
		],
		start,
		page_len,
	)

