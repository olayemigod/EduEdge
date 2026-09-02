from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import instructor_assignments as assignments
from eduedge.api import teacher_assignments as core
from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows
from eduedge.education.academic_fields import INSTITUTION_FIELD

MAX_RESULTS = 50


def _limit(value: int | str | None) -> int:
	return min(max(cint(value) or 20, 1), MAX_RESULTS)


@frappe.whitelist()
def search_assignment_courses(
	branch: str,
	program_offering: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Search Institution-visible courses for one permitted assignment row."""
	core._require_read()
	allowed = {row["name"]: row for row in core._allowed_branches()}
	branch_row = allowed.get(branch)
	if not branch_row:
		frappe.throw("The selected Branch is not available to your user.", frappe.PermissionError)
	core.assert_branch_access(branch)

	offering = frappe.db.get_value(
		"EduEdge Program Offering",
		program_offering,
		["name", "school_branch", "institution", "program", "is_active"],
		as_dict=True,
	)
	if not offering or not cint(offering.is_active) or offering.school_branch != branch:
		frappe.throw(
			"Select an active Class / Programme Offering for this Branch.",
			frappe.ValidationError,
		)
	if offering.institution and branch_row.get("institution") != offering.institution:
		frappe.throw("The selected Class belongs to another Institution.", frappe.ValidationError)

	configured = {
		row.course
		for row in frappe.get_all(
			"Program Course",
			filters={"parent": offering.program, "parenttype": "Program"},
			fields=["course"],
			limit_page_length=0,
		)
		if row.course
	}
	meta = frappe.get_meta("Course")
	filters: dict = {}
	if meta.has_field(INSTITUTION_FIELD) and offering.institution:
		filters[INSTITUTION_FIELD] = ["in", ["", offering.institution]]
	fields = ["name", "course_name", "department"]
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	rows = frappe.get_list(
		"Course",
		filters=filters,
		fields=fields,
		order_by="course_name asc",
		page_length=CANDIDATE_LIMIT,
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("course_name") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("department"),
				"In curriculum" if row.get("name") in configured else "Institution course",
			)
			if value
		)
		row["configured"] = row.get("name") in configured
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value",),
		search_fields=("label", "description"),
		page_length=_limit(page_length),
	)
