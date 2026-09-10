from __future__ import annotations

import frappe

from eduedge.education.teaching_assignments import current_user_instructors
from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

BYPASS_ROLES = {"System Manager", "EduEdge Super Administrator", "EduEdge Administrator"}
ASSIGNMENT_MANAGER_ROLES = BYPASS_ROLES | {
    "School Administrator",
    "Academic Administrator",
    "Education Manager",
    "Academics User",
}


def _roles(user: str) -> set[str]:
    return set(frappe.get_roles(user))


def _scope_applies(user: str) -> bool:
    if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
        return False
    return not bool(BYPASS_ROLES.intersection(_roles(user)))


def _is_assignment_manager(user: str) -> bool:
    return user == "Administrator" or bool(ASSIGNMENT_MANAGER_ROLES.intersection(_roles(user)))


def _allowed(user: str) -> set[str]:
    return {row.get("name") for row in get_allowed_school_branches(user=user) if row.get("name")}


def _branch_query(doctype: str, user: str) -> str:
    if not _scope_applies(user):
        return ""
    allowed = _allowed(user)
    if not allowed:
        return "1=0"
    values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
    return f"`tab{doctype}`.`school_branch` in ({values})"


def _and_conditions(*conditions: str) -> str:
    parts = [condition.strip() for condition in conditions if condition and condition.strip()]
    return " and ".join(f"({condition})" for condition in parts)


def instructor_assignment_query(user: str | None = None) -> str:
    resolved = user or frappe.session.user
    branch_condition = _branch_query("EduEdge Instructor Assignment", resolved)
    if _is_assignment_manager(resolved):
        return branch_condition
    instructors = current_user_instructors(resolved)
    if not instructors:
        return "1=0"
    values = ", ".join(frappe.db.escape(value) for value in instructors)
    return _and_conditions(
        branch_condition,
        f"`tabEduEdge Instructor Assignment`.`instructor` in ({values})",
    )


def student_photo_review_log_query(user: str | None = None) -> str:
    resolved = user or frappe.session.user
    return _branch_query("EduEdge Student Photo Review Log", resolved)


def has_people_branch_permission(doc, user=None, permission_type=None) -> bool:
    resolved = user or frappe.session.user
    if not doc:
        return True
    if _scope_applies(resolved) and doc.get("school_branch") not in _allowed(resolved):
        return False
    if doc.doctype == "EduEdge Instructor Assignment" and not _is_assignment_manager(resolved):
        return doc.get("instructor") in current_user_instructors(resolved)
    return True
