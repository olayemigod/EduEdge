from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import class_arms as core
from eduedge.api.fuzzy_search import get_bounded_candidates, rank_link_candidates
from eduedge.education.class_arm_identity import CLASS_ARM_DOCTYPE, DISPLAY_NAME_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD


@frappe.whitelist()
def get_class_arms_page(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	search: str | None = None,
	start: int | str = 0,
	page_length: int | str = core.DEFAULT_PAGE_LENGTH,
) -> dict:
	"""Fuzzy-aware Class Arm search while preserving normal paginated browsing."""
	search = str(search or "").strip()
	if not search:
		return core.get_class_arms_page(
			branch,
			academic_year,
			academic_term,
			search,
			start,
			page_length,
		)

	core._require_read()
	branch, selected_branch, branches = core._resolve_branch(branch)
	start = max(cint(start), 0)
	page_length = min(
		max(cint(page_length) or core.DEFAULT_PAGE_LENGTH, 1),
		core.MAX_PAGE_LENGTH,
	)
	filters = {BRANCH_FIELD: branch}
	if str(academic_year or "").strip():
		filters["academic_year"] = str(academic_year).strip()

	fields = core._student_group_fields()
	search_fields = tuple(
		fieldname
		for fieldname in (
			DISPLAY_NAME_FIELD,
			"student_group_name",
			"program",
			"course",
			"academic_year",
			"academic_term",
		)
		if fieldname in fields
	)
	rows = get_bounded_candidates(
		"Student Group",
		filters=filters,
		fields=fields,
		query=search,
		search_fields=search_fields,
		order_by="disabled asc, academic_year desc, student_group_name asc, modified desc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = (
			row.get(DISPLAY_NAME_FIELD)
			or row.get("student_group_name")
			or row.get("name")
		)
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("program"),
				row.get("course"),
				row.get("academic_year"),
				row.get("academic_term"),
			)
			if value
		)
		candidates.append(row)

	ranked = rank_link_candidates(
		candidates,
		search,
		exact_fields=("value",),
		search_fields=("label", "description"),
	)
	has_more = start + page_length < len(ranked)
	result_rows = ranked[start : start + page_length]
	core._attach_group_summary(result_rows)
	return {
		"selected_branch": selected_branch,
		"allowed_branches": branches,
		"class_arms": result_rows,
		"filters": {
			"branch": branch,
			"academic_year": str(academic_year or "").strip(),
			"search": search,
		},
		"paging": {
			"start": start,
			"page_length": page_length,
			"has_more": has_more,
			"next_start": start + len(result_rows),
		},
		"permissions": {
			"can_create": bool(
				frappe.has_permission("Student Group", "create")
				and frappe.has_permission(CLASS_ARM_DOCTYPE, "create")
			),
			"can_write": bool(frappe.has_permission("Student Group", "write")),
		},
	}
