from __future__ import annotations

import frappe
from frappe import _

from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.offerings import PURPOSE_FIELD, assert_branch_access, parse_query_filters

ALLOWED_SCOPED_QUERY_DOCTYPES = {
	"EduEdge Institution",
	"Department",
	# Deprecated masters remain allowlisted for privileged migration screens only.
	"EduEdge Academic Section",
	"EduEdge Academic Level",
}


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
	purpose_field = PURPOSE_FIELD[purpose]
	params = {"branch": branch, "candidate_limit": CANDIDATE_LIMIT}
	conditions = [
		"offering.school_branch = %(branch)s",
		"offering.is_active = 1",
		f"offering.`{purpose_field}` = 1",
	]
	for fieldname in ("program", "department", "academic_year"):
		if filters.get(fieldname):
			conditions.append(f"offering.`{fieldname}` = %({fieldname})s")
			params[fieldname] = filters[fieldname]
	if filters.get("academic_term"):
		conditions.append(
			"(coalesce(offering.academic_term, '') = '' or offering.academic_term = %(academic_term)s)"
		)
		params["academic_term"] = filters["academic_term"]
	rows = frappe.db.sql(
		f"""
		select offering.name, offering.offering_title, offering.offering_code,
			offering.program, offering.department, offering.academic_year, offering.academic_term,
			offering.study_mode, offering.delivery_mode
		from `tabEduEdge Program Offering` offering
		where {' and '.join(conditions)}
		order by offering.offering_title asc, offering.modified desc
		limit %(candidate_limit)s
		""",
		params,
		as_dict=True,
	)
	candidates = [
		{
			"value": row.name,
			"label": row.offering_title or row.name,
			"description": " · ".join(
				value
				for value in (
					row.offering_code,
					row.department,
					row.program,
					row.academic_year,
					row.academic_term,
					row.study_mode,
					row.delivery_mode,
				)
				if value
			),
			"code": row.offering_code or "",
			"raw": row,
		}
		for row in rows
	]
	ranked = rank_link_rows(
		candidates,
		str(txt or ""),
		exact_fields=("value", "code"),
		search_fields=("label", "description"),
		start=int(start),
		page_length=int(page_len),
	)
	return [
		[
			row["value"],
			row["label"],
			row.get("code") or "",
			row.get("description") or "",
		]
		for row in ranked
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def institution_scoped_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	if doctype not in ALLOWED_SCOPED_QUERY_DOCTYPES:
		frappe.throw(_("This academic lookup is not permitted."), frappe.PermissionError)
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You are not permitted to read {0}.").format(doctype), frappe.PermissionError)
	filters = parse_query_filters(filters)
	institution = filters.get(INSTITUTION_FIELD) or filters.get("institution")
	meta = frappe.get_meta(doctype)
	query_filters = {"enabled": 1} if meta.has_field("enabled") else {}
	institution_fieldname = "institution" if meta.has_field("institution") else INSTITUTION_FIELD
	if institution and meta.has_field(institution_fieldname):
		query_filters[institution_fieldname] = institution
	if meta.has_field("disabled"):
		query_filters["disabled"] = 0
	fields = ["name"]
	for candidate in ("department_name", "section_name", "level_name", "institution_name", "title"):
		if meta.has_field(candidate):
			fields.append(candidate)
	rows = frappe.get_list(
		doctype,
		filters=query_filters,
		fields=fields,
		page_length=CANDIDATE_LIMIT,
		order_by=(
			"lft asc"
			if doctype == "Department"
			else ("sequence asc, modified desc" if meta.has_field("sequence") else "modified desc")
		),
	)
	candidates = []
	for row in rows:
		label = next((row.get(field) for field in fields[1:] if row.get(field)), row.name)
		description = " · ".join(
			str(row.get(field) or "")
			for field in fields[1:]
			if row.get(field) and row.get(field) != label
		)
		candidates.append(
			{"value": row.name, "label": label, "description": description, "raw": row}
		)
	ranked = rank_link_rows(
		candidates,
		str(txt or ""),
		start=int(start),
		page_length=int(page_len),
	)
	return [[row["value"], row["label"]] for row in ranked]


@frappe.whitelist()
def get_programme_offering_context(offering: str) -> dict:
	_require_login()
	doc = frappe.get_doc("EduEdge Program Offering", offering)
	doc.check_permission("read")
	assert_branch_access(doc.school_branch)
	return {
		"name": doc.name,
		"school_branch": doc.school_branch,
		"institution": doc.institution,
		"program": doc.program,
		"department": doc.department,
		"academic_year": doc.academic_year,
		"academic_term": doc.academic_term,
		"student_batch": doc.student_batch,
		"study_mode": doc.study_mode,
		"delivery_mode": doc.delivery_mode,
	}
