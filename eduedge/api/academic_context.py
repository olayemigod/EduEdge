from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.academic_fields import (
	ACADEMIC_LEVEL_FIELD,
	ACADEMIC_SECTION_FIELD,
	INSTITUTION_FIELD,
)
from eduedge.education.offerings import PURPOSE_FIELD, assert_branch_access, parse_query_filters


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_offering_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	branch = filters.get("school_branch") or filters.get("eduedge_school_branch")
	purpose = filters.get("purpose") or "enrollment"
	if purpose not in PURPOSE_FIELD:
		frappe.throw(_("Invalid Programme Offering purpose."), frappe.ValidationError)
	if not branch:
		return []
	assert_branch_access(branch)
	query_filters = {
		"school_branch": branch,
		"is_active": 1,
		PURPOSE_FIELD[purpose]: 1,
	}
	for fieldname in ("program", "academic_year", "academic_term"):
		if filters.get(fieldname):
			query_filters[fieldname] = filters[fieldname]
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=query_filters,
		or_filters={
			"name": ["like", f"%{txt}%"],
			"offering_title": ["like", f"%{txt}%"],
			"offering_code": ["like", f"%{txt}%"],
		},
		fields=["name", "offering_title", "offering_code", "program", "academic_year", "academic_term", "study_mode", "delivery_mode"],
		start=int(start),
		page_length=int(page_len),
		order_by="offering_title asc",
	)
	return [
		[
			row.name,
			row.offering_title or row.name,
			row.offering_code,
			" · ".join(value for value in (row.program, row.academic_year, row.academic_term, row.study_mode, row.delivery_mode) if value),
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def institution_scoped_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = parse_query_filters(filters)
	institution = filters.get(INSTITUTION_FIELD) or filters.get("institution")
	query_filters = {"enabled": 1} if frappe.get_meta(doctype).has_field("enabled") else {}
	if institution and frappe.get_meta(doctype).has_field("institution"):
		query_filters["institution"] = institution
	fields = ["name"]
	meta = frappe.get_meta(doctype)
	for candidate in ("section_name", "level_name", "institution_name", "title"):
		if meta.has_field(candidate):
			fields.append(candidate)
	rows = frappe.get_list(
		doctype,
		filters=query_filters,
		or_filters={field: ["like", f"%{txt}%"] for field in fields},
		fields=fields,
		start=int(start),
		page_length=int(page_len),
		order_by="sequence asc, modified desc" if meta.has_field("sequence") else "modified desc",
	)
	return [[row.name, next((row.get(field) for field in fields[1:] if row.get(field)), row.name)] for row in rows]


@frappe.whitelist()
def get_programme_offering_context(offering: str) -> dict:
	_require_login()
	row = frappe.db.get_value(
		"EduEdge Program Offering",
		offering,
		[
			"name", "school_branch", "institution", "program", "academic_year", "academic_term",
			"academic_section", "academic_level", "student_batch", "study_mode", "delivery_mode",
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Programme Offering not found."), frappe.DoesNotExistError)
	assert_branch_access(row.school_branch)
	return dict(row)
