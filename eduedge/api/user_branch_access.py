from __future__ import annotations

import frappe

from eduedge.education.user_branch_access_permissions import (
    assignable_access_levels,
    assignable_company_names,
    assignable_institution_names,
    manageable_user_names,
)


def _like(txt: str | None) -> str:
    return f"%{str(txt or '').strip()}%"


@frappe.whitelist()
def get_user_branch_access_authoring_context() -> dict:
    return {"access_levels": assignable_access_levels()}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_branch_access_company_query(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe._dict(filters or {})
    names = assignable_company_names(filters.get("access_scope"))
    query_filters: dict = {"is_group": 0}
    if names is not None:
        if not names:
            return []
        query_filters["name"] = ["in", sorted(names)]
    rows = frappe.get_list(
        "Company",
        filters=query_filters,
        or_filters={
            "name": ["like", _like(txt)],
            "company_name": ["like", _like(txt)],
        } if str(txt or "").strip() else None,
        fields=["name", "company_name"],
        order_by="company_name asc",
        limit_start=int(start),
        limit_page_length=int(page_len),
    )
    return [[row.name, row.company_name or row.name] for row in rows]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_branch_access_institution_query(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe._dict(filters or {})
    company = str(filters.get("company") or "").strip()
    names = assignable_institution_names(filters.get("access_scope"), company=company or None)
    query_filters: dict = {"enabled": 1}
    if company:
        query_filters["company"] = company
    if names is not None:
        if not names:
            return []
        query_filters["name"] = ["in", sorted(names)]
    rows = frappe.get_list(
        "EduEdge Institution",
        filters=query_filters,
        or_filters={
            "name": ["like", _like(txt)],
            "institution_name": ["like", _like(txt)],
            "institution_code": ["like", _like(txt)],
        } if str(txt or "").strip() else None,
        fields=["name", "institution_name", "institution_code"],
        order_by="institution_name asc",
        limit_start=int(start),
        limit_page_length=int(page_len),
    )
    return [[row.name, row.institution_name or row.name, row.institution_code or ""] for row in rows]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def user_branch_access_user_query(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe._dict(filters or {})
    company = str(filters.get("company") or "").strip()
    names = manageable_user_names(company=company or None)
    query_filters: dict = {"enabled": 1, "user_type": "System User"}
    if names is not None:
        if not names:
            return []
        query_filters["name"] = ["in", sorted(names)]
    rows = frappe.get_list(
        "User",
        filters=query_filters,
        or_filters={
            "name": ["like", _like(txt)],
            "full_name": ["like", _like(txt)],
        } if str(txt or "").strip() else None,
        fields=["name", "full_name"],
        order_by="full_name asc, name asc",
        limit_start=int(start),
        limit_page_length=int(page_len),
    )
    return [[row.name, row.full_name or row.name] for row in rows]
