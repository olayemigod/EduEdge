from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from eduedge.api.exam_templates import (
	DEFAULT_PAGE_LENGTH,
	EXAM_BODIES,
	PAGE_LENGTH_OPTIONS,
	SORT_OPTIONS,
	STATUSES,
	TEMPLATE_DOCTYPE,
	_allowed_branch_rows,
	_branch_options,
	_clamp_start,
	_company_options,
	_institution_options,
	_normalise_page_length,
	_option,
	_require_allowed,
	_require_permission,
	_resolve_exam_scope,
	_search_or_filters,
	_serialise_list_rows,
)
from eduedge.cbt.public_access import can_author_public_exams
from eduedge.eduedge.doctype.eduedge_cbt_exam_template.eduedge_cbt_exam_template import (
	EXAM_PURPOSES,
	MODE_BLUEPRINT,
	MODE_FIXED,
	PUBLIC_EXAM,
	REUSE_BRANCH,
	REUSE_INSTITUTION,
	REUSE_SCOPES,
	REUSE_UNIVERSAL,
	SCHOOL_EXAM,
	SUBJECT_ANY,
	SUBJECT_APPLICABILITY,
	SUBJECT_SPECIFIC,
	TEMPLATE_MODES,
	can_review_templates,
)


def _permission_safe_status_counts(base_filters: dict, or_filters: list[list[str]]) -> dict:
	rows = frappe.get_list(
		TEMPLATE_DOCTYPE,
		filters=base_filters,
		or_filters=or_filters or None,
		fields=["status", "count(name) as count"],
		group_by="status",
		page_length=len(STATUSES) + 1,
	)
	counts = {"Total": 0, **{status: 0 for status in STATUSES}}
	for row in rows:
		status = row.status or "Draft"
		value = int(row.count or 0)
		counts[status] = value
		counts["Total"] += value
	return counts


@frappe.whitelist()
def get_exam_templates(
	search: str | None = None,
	exam_scope: str | None = None,
	company: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	template_reuse_scope: str | None = None,
	subject_applicability: str | None = None,
	course: str | None = None,
	status: str | None = None,
	exam_purpose: str | None = None,
	template_mode: str | None = None,
	exam_body: str | None = None,
	sort_by: str | None = None,
	start: int = 0,
	page_length: int = DEFAULT_PAGE_LENGTH,
) -> dict:
	_require_permission("read")
	branches = _allowed_branch_rows()
	companies = _company_options(branches)
	resolved_scope = _resolve_exam_scope(exam_scope)
	resolved_company = ""
	resolved_institution = ""
	resolved_branch = ""
	visible_institutions: list[dict] = []
	visible_branches: list[dict] = []

	if resolved_scope == SCHOOL_EXAM:
		resolved_company = _require_allowed(
			company,
			{row["value"] for row in companies},
			_("Company"),
		)
		visible_institutions = _institution_options(branches, resolved_company)
		resolved_institution = _require_allowed(
			institution,
			{row["value"] for row in visible_institutions},
			_("Institution"),
		)
		visible_branches = _branch_options(branches, resolved_company, resolved_institution)
		resolved_branch = _require_allowed(
			branch,
			{row["value"] for row in visible_branches},
			_("Branch / Campus"),
		)

	resolved_reuse = str(template_reuse_scope or "").strip()
	if resolved_reuse and resolved_reuse not in REUSE_SCOPES:
		resolved_reuse = ""
	resolved_subject_scope = str(subject_applicability or "").strip()
	if resolved_subject_scope and resolved_subject_scope not in SUBJECT_APPLICABILITY:
		resolved_subject_scope = ""
	resolved_status = str(status or "").strip()
	if resolved_status and resolved_status not in STATUSES:
		resolved_status = ""
	resolved_purpose = str(exam_purpose or "").strip()
	if resolved_purpose and resolved_purpose not in EXAM_PURPOSES:
		resolved_purpose = ""
	resolved_mode = str(template_mode or "").strip()
	if resolved_mode and resolved_mode not in TEMPLATE_MODES:
		resolved_mode = ""
	resolved_exam_body = str(exam_body or "").strip()
	if resolved_exam_body and resolved_exam_body not in EXAM_BODIES:
		resolved_exam_body = ""
	resolved_course = str(course or "").strip()
	if resolved_course and not frappe.db.exists("Course", resolved_course):
		frappe.throw(_("Select a valid Subject / Course."), frappe.ValidationError)
	resolved_search = str(search or "").strip()[:120]
	resolved_sort = sort_by if sort_by in SORT_OPTIONS else "modified_desc"
	resolved_page_length = _normalise_page_length(page_length)

	base_filters: dict[str, Any] = {"exam_scope": resolved_scope}
	if resolved_scope == SCHOOL_EXAM:
		allowed_companies = [resolved_company] if resolved_company else [row["value"] for row in companies]
		base_filters["company"] = ["in", allowed_companies or [""]]
		if resolved_institution:
			base_filters["institution"] = resolved_institution
		if resolved_branch:
			base_filters["school_branch"] = resolved_branch
		if resolved_reuse:
			base_filters["template_reuse_scope"] = resolved_reuse
	if resolved_subject_scope:
		base_filters["subject_applicability"] = resolved_subject_scope
	if resolved_course:
		base_filters["course"] = resolved_course
	if resolved_purpose:
		base_filters["exam_purpose"] = resolved_purpose
	if resolved_mode:
		base_filters["template_mode"] = resolved_mode
	if resolved_exam_body:
		base_filters["exam_body"] = resolved_exam_body

	or_filters = _search_or_filters(resolved_search)
	counts = _permission_safe_status_counts(base_filters, or_filters)
	filtered_total = counts.get(resolved_status, 0) if resolved_status else counts["Total"]
	resolved_start = _clamp_start(start, filtered_total, resolved_page_length)
	row_filters = dict(base_filters)
	if resolved_status:
		row_filters["status"] = resolved_status

	rows = frappe.get_list(
		TEMPLATE_DOCTYPE,
		filters=row_filters,
		or_filters=or_filters or None,
		fields=[
			"name",
			"template_title",
			"template_code",
			"exam_scope",
			"template_reuse_scope",
			"company",
			"institution",
			"school_branch",
			"exam_purpose",
			"template_mode",
			"subject_applicability",
			"course",
			"exam_body",
			"duration_minutes",
			"question_count",
			"total_marks",
			"status",
			"version_number",
			"modified",
		],
		order_by=SORT_OPTIONS[resolved_sort],
		start=resolved_start,
		page_length=resolved_page_length,
	)
	all_institutions = _institution_options(branches)
	serialised = _serialise_list_rows(rows, branches, all_institutions)

	return {
		"rows": serialised,
		"counts": counts,
		"filters": {
			"search": resolved_search,
			"exam_scope": resolved_scope,
			"company": resolved_company,
			"institution": resolved_institution,
			"branch": resolved_branch,
			"template_reuse_scope": resolved_reuse,
			"subject_applicability": resolved_subject_scope,
			"course": resolved_course,
			"status": resolved_status,
			"exam_purpose": resolved_purpose,
			"template_mode": resolved_mode,
			"exam_body": resolved_exam_body,
			"sort_by": resolved_sort,
		},
		"options": {
			"scope": [_option(SCHOOL_EXAM)] + ([_option(PUBLIC_EXAM)] if can_author_public_exams(frappe.session.user) else []),
			"companies": companies,
			"institutions": visible_institutions,
			"branches": visible_branches,
			"reuse_scopes": [_option(value) for value in (REUSE_UNIVERSAL, REUSE_INSTITUTION, REUSE_BRANCH)],
			"subject_applicability": [_option(value) for value in (SUBJECT_ANY, SUBJECT_SPECIFIC)],
			"purposes": [_option(value) for value in sorted(EXAM_PURPOSES)],
			"template_modes": [_option(value) for value in (MODE_BLUEPRINT, MODE_FIXED)],
			"statuses": [_option(value) for value in STATUSES],
			"exam_bodies": [_option(value) for value in EXAM_BODIES],
			"page_lengths": list(PAGE_LENGTH_OPTIONS),
		},
		"pagination": {
			"start": resolved_start,
			"page_length": resolved_page_length,
			"total": filtered_total,
			"has_previous": resolved_start > 0,
			"has_next": resolved_start + resolved_page_length < filtered_total,
		},
		"permissions": {
			"can_create": bool(frappe.has_permission(TEMPLATE_DOCTYPE, "create")),
			"can_write": bool(frappe.has_permission(TEMPLATE_DOCTYPE, "write")),
			"can_review": bool(can_review_templates(frappe.session.user)),
		},
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
	}
