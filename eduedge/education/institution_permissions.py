from __future__ import annotations

import frappe

from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

STRUCTURE_MANAGER_ROLES = {"School Administrator", "Academic Administrator", "Bursar"}
PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}


def institution_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	branches = get_allowed_school_branches(user=resolved_user)
	if not branches:
		return "1=0" if frappe.db.count("EduEdge School Branch", {"enabled": 1}) else ""

	roles = set(frappe.get_roles(resolved_user))
	if roles.intersection(STRUCTURE_MANAGER_ROLES):
		companies = {row.get("company") for row in branches if row.get("company")}
		if not companies:
			return "1=0"
		values = ", ".join(frappe.db.escape(value) for value in sorted(companies))
		return f"`tabEduEdge Institution`.company in ({values})"

	branch_names = [row.get("name") for row in branches if row.get("name")]
	institutions = set(
		frappe.get_all(
			"EduEdge School Branch",
			filters={"name": ["in", branch_names]},
			pluck="institution",
		)
	)
	institutions.discard(None)
	institutions.discard("")
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	return f"`tabEduEdge Institution`.name in ({values})"


def has_institution_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user) or not doc:
		return None
	branches = get_allowed_school_branches(user=resolved_user)
	if not branches:
		return False if frappe.db.count("EduEdge School Branch", {"enabled": 1}) else None

	roles = set(frappe.get_roles(resolved_user))
	if roles.intersection(STRUCTURE_MANAGER_ROLES):
		companies = {row.get("company") for row in branches if row.get("company")}
		return None if doc.get("company") in companies else False

	branch_names = [row.get("name") for row in branches if row.get("name")]
	return None if frappe.db.exists(
		"EduEdge School Branch",
		{"name": ["in", branch_names], "institution": doc.name},
	) else False


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(user))
	return not bool(roles.intersection(PRIVILEGED_ROLES))
