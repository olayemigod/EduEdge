from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import instructor_assignments as assignments
from eduedge.api import teacher_assignments as core
from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.teaching_assignments import current_user_instructors

MAX_RESULTS = 50


def _limit(value: int | str | None) -> int:
	return min(max(cint(value) or 20, 1), MAX_RESULTS)


def _allowed_branch_map() -> dict[str, dict]:
	return {row["name"]: row for row in core._allowed_branches()}


@frappe.whitelist()
def search_instructors(query: str = "", page_length: int | str = 20) -> list[dict]:
	core._require_read()
	filters: dict = {"status": "Active"}
	if not assignments._can_manage_assignments():
		own = current_user_instructors()
		filters["name"] = ["in", own] if own else ["in", ["__none__"]]
	meta = frappe.get_meta("Instructor")
	fields = ["name", "instructor_name", "department", "employee"]
	for fieldname in (INSTITUTION_FIELD, "eduedge_email", "eduedge_mobile"):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Instructor",
		filters=filters,
		fields=fields,
		order_by="instructor_name asc",
		page_length=CANDIDATE_LIMIT,
	)
	institutions = {
		row.name: row.institution_name
		for row in frappe.get_list(
			"EduEdge Institution",
			fields=["name", "institution_name"],
			page_length=CANDIDATE_LIMIT,
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
) -> list[dict]:
	core._require_read()
	allowed = _allowed_branch_map()
	if branch not in allowed:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	core.assert_branch_access(branch)
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "is_active": 1},
		fields=[
			"name", "offering_title", "offering_code", "program", "academic_year",
			"academic_term", "institution", "school_branch",
		],
		order_by="academic_year desc, offering_title asc",
		page_length=CANDIDATE_LIMIT,
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("offering_title") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("offering_code"), row.get("program"), row.get("academic_year"), row.get("academic_term")
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
) -> list[dict]:
	core._require_read()
	allowed = _allowed_branch_map()
	if branch not in allowed:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	core.assert_branch_access(branch)
	offering = frappe.db.get_value(
		"EduEdge Program Offering",
		program_offering,
		["name", "school_branch", "program", "academic_year", "academic_term", "is_active"],
		as_dict=True,
	)
	if not offering or not cint(offering.is_active) or offering.school_branch != branch:
		frappe.throw("Select an active Class / Programme Offering for this Branch.", frappe.ValidationError)
	filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	meta = frappe.get_meta("Student Group")
	if meta.has_field(OFFERING_FIELD):
		filters[OFFERING_FIELD] = program_offering
	fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD]
	for fieldname in ("eduedge_display_name", OFFERING_FIELD):
		if meta.has_field(fieldname):
			fields.append(fieldname)
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=fields,
		order_by="student_group_name asc",
		page_length=CANDIDATE_LIMIT,
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
