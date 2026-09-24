from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.services.branch_context import (
    ASSIGNMENT_SCOPE_BRANCH,
    ASSIGNMENT_SCOPE_COMPANY,
    ASSIGNMENT_SCOPE_INSTITUTION,
    ASSIGNMENT_SCOPES,
    _get_active_access_rows,
    is_branch_access_enforced,
)

PRIVILEGED_ROLES = {
    "System Manager",
    "EduEdge Super Administrator",
    "EduEdge Administrator",
}


def _is_privileged(user: str | None = None) -> bool:
    resolved = user or frappe.session.user
    if resolved == "Administrator":
        return True
    return bool(PRIVILEGED_ROLES.intersection(frappe.get_roles(resolved)))


def _effective_scope(row) -> str:
    scope = str(row.get("access_scope") or "").strip()
    if scope in ASSIGNMENT_SCOPES:
        return scope
    if cint(row.get("hq_all_branch_access")):
        return ASSIGNMENT_SCOPE_COMPANY
    if row.get("institution") and not row.get("school_branch"):
        return ASSIGNMENT_SCOPE_INSTITUTION
    return ASSIGNMENT_SCOPE_BRANCH


def get_assignable_access_scope(user: str | None = None) -> dict | None:
    """Return the exact scopes the current actor may delegate.

    None means unrestricted because branch enforcement is off or the actor is a
    platform administrator. Limited users may delegate only the same scope level
    they already hold, or a narrower one. This deliberately does not infer broad
    Institution/Company delegation merely because current Branch coverage happens
    to include every existing campus.
    """
    resolved = user or frappe.session.user
    if _is_privileged(resolved) or not is_branch_access_enforced():
        return None
    if resolved != frappe.session.user and not _is_privileged(frappe.session.user):
        return {"branches": set(), "institutions": set(), "companies": set()}

    direct_branches: set[str] = set()
    direct_institutions: set[str] = set()
    direct_companies: set[str] = set()
    for row in _get_active_access_rows(resolved):
        scope = _effective_scope(row)
        if scope == ASSIGNMENT_SCOPE_COMPANY and row.get("company"):
            direct_companies.add(str(row.company))
        elif scope == ASSIGNMENT_SCOPE_INSTITUTION and row.get("institution"):
            direct_institutions.add(str(row.institution))
        elif scope == ASSIGNMENT_SCOPE_BRANCH and row.get("school_branch"):
            direct_branches.add(str(row.school_branch))

    branch_rows = frappe.get_all(
        "EduEdge School Branch",
        filters={"enabled": 1},
        fields=["name", "company", "institution"],
        limit_page_length=0,
    )
    branches = {
        str(row.name)
        for row in branch_rows
        if row.name
        and (
            row.name in direct_branches
            or row.institution in direct_institutions
            or row.company in direct_companies
        )
    }

    institution_rows = frappe.get_all(
        "EduEdge Institution",
        filters={"enabled": 1},
        fields=["name", "company"],
        limit_page_length=0,
    )
    institutions = {
        str(row.name)
        for row in institution_rows
        if row.name
        and (row.name in direct_institutions or row.company in direct_companies)
    }

    return {
        "branches": branches,
        "institutions": institutions,
        "companies": direct_companies,
    }


def _scope_allowed(doc, scope: dict | None) -> bool:
    if scope is None:
        return True
    access_scope = _effective_scope(doc)
    if access_scope == ASSIGNMENT_SCOPE_COMPANY:
        return bool(doc.get("company") and doc.get("company") in scope["companies"])
    if access_scope == ASSIGNMENT_SCOPE_INSTITUTION:
        return bool(doc.get("institution") and doc.get("institution") in scope["institutions"])
    return bool(doc.get("school_branch") and doc.get("school_branch") in scope["branches"])


def assert_user_branch_access_scope(doc) -> None:
    if _scope_allowed(doc, get_assignable_access_scope()):
        return
    frappe.throw(
        _(
            "You cannot grant or change User Branch Access outside your governed access scope. "
            "A Branch administrator may delegate Branch access only; broader Institution or "
            "Company access requires matching broader authority."
        ),
        frappe.PermissionError,
    )



def assert_default_branch_change_scope(doc) -> None:
    if not cint(doc.get("is_default_branch")) or _effective_scope(doc) != ASSIGNMENT_SCOPE_BRANCH:
        return
    scope = get_assignable_access_scope()
    if scope is None:
        return
    rows = frappe.get_all(
        "EduEdge User Branch Access",
        filters={
            "user": doc.get("user"),
            "is_default_branch": 1,
            "name": ["!=", doc.get("name") or ""],
        },
        fields=[
            "name",
            "access_scope",
            "hq_all_branch_access",
            "company",
            "institution",
            "school_branch",
        ],
        limit_page_length=0,
    )
    if any(not _scope_allowed(row, scope) for row in rows):
        frappe.throw(
            _(
                "This user already has a default Branch outside your governed access scope. "
                "A platform administrator must change the cross-scope default."
            ),
            frappe.PermissionError,
        )

def has_user_branch_access_permission(doc, user=None, permission_type=None) -> bool:
    resolved = user or frappe.session.user
    if _is_privileged(resolved) or not is_branch_access_enforced():
        return True
    if not doc:
        return True
    return _scope_allowed(doc, get_assignable_access_scope(resolved))


def _sql_in(values: set[str]) -> str:
    if not values:
        return ""
    return ", ".join(frappe.db.escape(value) for value in sorted(values))


def user_branch_access_query(user: str | None = None) -> str:
    resolved = user or frappe.session.user
    scope = get_assignable_access_scope(resolved)
    if scope is None:
        return ""
    table = "`tabEduEdge User Branch Access`"
    parts: list[str] = []

    companies = _sql_in(scope["companies"])
    if companies:
        parts.append(
            f"(({table}.access_scope = 'Company' or "
            f"(coalesce({table}.access_scope, '') not in ('Company','Institution','Branch') "
            f"and coalesce({table}.hq_all_branch_access, 0) = 1)) "
            f"and {table}.company in ({companies}))"
        )

    institutions = _sql_in(scope["institutions"])
    if institutions:
        parts.append(
            f"(({table}.access_scope = 'Institution' or "
            f"(coalesce({table}.access_scope, '') not in ('Company','Institution','Branch') "
            f"and coalesce({table}.hq_all_branch_access, 0) = 0 "
            f"and coalesce({table}.institution, '') != '' "
            f"and coalesce({table}.school_branch, '') = '')) "
            f"and {table}.institution in ({institutions}))"
        )

    branches = _sql_in(scope["branches"])
    if branches:
        parts.append(
            f"(({table}.access_scope = 'Branch' or "
            f"coalesce({table}.access_scope, '') not in ('Company','Institution','Branch')) "
            f"and coalesce({table}.hq_all_branch_access, 0) = 0 "
            f"and {table}.school_branch in ({branches}))"
        )

    return "(" + " or ".join(parts) + ")" if parts else "1=0"


def assignable_company_names(access_scope: str | None = None) -> set[str] | None:
    scope = get_assignable_access_scope()
    if scope is None:
        return None
    resolved_scope = str(access_scope or ASSIGNMENT_SCOPE_BRANCH)
    if resolved_scope == ASSIGNMENT_SCOPE_COMPANY:
        return set(scope["companies"])

    if resolved_scope == ASSIGNMENT_SCOPE_INSTITUTION:
        if not scope["institutions"]:
            return set()
        return {
            str(value)
            for value in frappe.get_all(
                "EduEdge Institution",
                filters={"name": ["in", sorted(scope["institutions"])]},
                pluck="company",
                limit_page_length=0,
            )
            if value
        }

    if not scope["branches"]:
        return set()
    return {
        str(value)
        for value in frappe.get_all(
            "EduEdge School Branch",
            filters={"name": ["in", sorted(scope["branches"])]},
            pluck="company",
            limit_page_length=0,
        )
        if value
    }


def assignable_institution_names(access_scope: str | None = None, company: str | None = None) -> set[str] | None:
    scope = get_assignable_access_scope()
    if scope is None:
        return None
    resolved_scope = str(access_scope or ASSIGNMENT_SCOPE_BRANCH)
    if resolved_scope == ASSIGNMENT_SCOPE_INSTITUTION:
        names = set(scope["institutions"])
    else:
        if not scope["branches"]:
            return set()
        names = {
            str(value)
            for value in frappe.get_all(
                "EduEdge School Branch",
                filters={"name": ["in", sorted(scope["branches"])]},
                pluck="institution",
                limit_page_length=0,
            )
            if value
        }
    if company and names:
        names = {
            str(row.name)
            for row in frappe.get_all(
                "EduEdge Institution",
                filters={"name": ["in", sorted(names)], "company": company, "enabled": 1},
                fields=["name"],
                limit_page_length=0,
            )
        }
    return names


def manageable_user_names(company: str | None = None) -> set[str] | None:
    """Bound user selectors for non-platform administrators.

    Existing governed users remain selectable even when they are not Employee-linked.
    New discovery is limited to active Employees in an assignable Company, preventing
    site-wide System User enumeration from the Branch Governance form.
    """
    scope = get_assignable_access_scope()
    if scope is None:
        return None

    companies = assignable_company_names(ASSIGNMENT_SCOPE_BRANCH) or set()
    if company:
        companies &= {company}
    names: set[str] = {frappe.session.user} if frappe.session.user else set()

    if companies and frappe.db.exists("DocType", "Employee"):
        names.update(
            str(row.user_id)
            for row in frappe.get_all(
                "Employee",
                filters={
                    "status": "Active",
                    "company": ["in", sorted(companies)],
                    "user_id": ["is", "set"],
                },
                fields=["user_id"],
                limit_page_length=0,
            )
            if row.user_id
        )

    rows = frappe.get_all(
        "EduEdge User Branch Access",
        fields=[
            "user",
            "access_scope",
            "hq_all_branch_access",
            "company",
            "institution",
            "school_branch",
        ],
        limit_page_length=0,
    )
    for row in rows:
        if _scope_allowed(row, scope) and row.user:
            if not company or row.company == company:
                names.add(str(row.user))
    return names
