from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import people_operations as core
from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.people_fields import (
	INSTRUCTOR_PRIMARY_BRANCH_FIELD,
	PHOTO_LOCKED_FIELD,
	PHOTO_STATUS_FIELD,
)


@frappe.whitelist()
def get_instructors_page(
	branch: str | None = None,
	search: str | None = None,
	instructor: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	"""Fuzzy-aware Instructor workspace search with the original Branch boundary."""
	core._require_permission("Instructor", "read")
	resolved, selected, allowed = core._resolve_branch(branch)
	filters = {INSTRUCTOR_PRIMARY_BRANCH_FIELD: resolved}
	length = min(max(cint(page_length), 1), core.MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	search = str(search or "").strip()
	fields = core._row_fields(
		"Instructor",
		[
			"name", "instructor_name", "image", "status", "department", "employee",
			INSTITUTION_FIELD, INSTRUCTOR_PRIMARY_BRANCH_FIELD, "eduedge_email",
			"eduedge_mobile", "eduedge_qualification", "eduedge_specialisation",
			"eduedge_employment_type", PHOTO_STATUS_FIELD, PHOTO_LOCKED_FIELD,
		],
	)
	if search:
		candidate_rows = frappe.get_list(
			"Instructor",
			filters=filters,
			fields=fields,
			order_by="instructor_name asc",
			page_length=CANDIDATE_LIMIT,
		)
		candidates = []
		for source in candidate_rows:
			row = dict(source)
			row["value"] = row.get("name")
			row["label"] = row.get("instructor_name") or row.get("name")
			row["description"] = " · ".join(
				str(value)
				for value in (
					row.get("department"), row.get("eduedge_email"), row.get("eduedge_mobile"),
					row.get("employee"), row.get("eduedge_specialisation"),
				)
				if value
			)
			candidates.append(row)
		ranked = rank_link_rows(
			candidates,
			search,
			exact_fields=("value", "eduedge_email", "eduedge_mobile", "employee"),
			search_fields=("label", "description"),
			start=0,
			page_length=CANDIDATE_LIMIT,
		)
		has_more = start + length < len(ranked)
		rows = ranked[start : start + length]
	else:
		rows = frappe.get_list(
			"Instructor",
			filters=filters,
			fields=fields,
			order_by="instructor_name asc",
			start=start,
			page_length=length + 1,
		)
		has_more = len(rows) > length
		rows = rows[:length]
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"instructors": rows,
		"instructor": core._instructor_detail(instructor) if instructor else None,
		"options": core._standard_options(),
		"permissions": {
			"can_create": frappe.has_permission("Instructor", "create"),
			"can_write": frappe.has_permission("Instructor", "write"),
			"can_manage_photo": bool(core.PEOPLE_MANAGER_ROLES.intersection(frappe.get_roles())),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}
