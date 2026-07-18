from __future__ import annotations

import frappe
from frappe import _

USER_DEFAULT_KEY = "eduedge_school_branch"


def _assert_user_scope(user: str) -> None:
	if user == frappe.session.user:
		return
	roles = set(frappe.get_roles(frappe.session.user))
	if not roles.intersection({"System Manager", "EduEdge Administrator"}):
		frappe.throw(_("You cannot manage another user's EduEdge branch context."), frappe.PermissionError)


def get_allowed_school_branches(
	*,
	user: str | None = None,
	company: str | None = None,
) -> list[dict]:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	filters: dict = {"enabled": 1}
	if company:
		filters["company"] = company
	if resolved_user == frappe.session.user:
		return frappe.get_list(
			"EduEdge School Branch",
			filters=filters,
			fields=[
				"name",
				"branch_name",
				"branch_code",
				"branch_type",
				"company",
				"cost_center",
				"default_warehouse",
				"platform_branch_id",
				"is_default",
			],
			order_by="is_default desc, branch_name asc",
		)
	return frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		fields=[
			"name",
			"branch_name",
			"branch_code",
			"branch_type",
			"company",
			"cost_center",
			"default_warehouse",
			"platform_branch_id",
			"is_default",
		],
		order_by="is_default desc, branch_name asc",
	)


def get_current_school_branch(*, user: str | None = None) -> dict | None:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	branch_name = frappe.defaults.get_user_default(USER_DEFAULT_KEY, user=resolved_user)
	if branch_name:
		allowed = {row["name"]: row for row in get_allowed_school_branches(user=resolved_user)}
		if branch_name in allowed:
			return allowed[branch_name]
		frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
	allowed = get_allowed_school_branches(user=resolved_user)
	default_branch = next((row for row in allowed if row.get("is_default")), None)
	return default_branch or (allowed[0] if len(allowed) == 1 else None)


def switch_school_branch(branch: str, *, user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	allowed = {row["name"]: row for row in get_allowed_school_branches(user=resolved_user)}
	if branch not in allowed:
		frappe.throw(_("You do not have access to the selected School Branch."), frappe.PermissionError)
	frappe.defaults.set_user_default(USER_DEFAULT_KEY, branch, user=resolved_user)
	frappe.defaults.set_user_default("company", allowed[branch]["company"], user=resolved_user)
	return allowed[branch]


def clear_school_branch(*, user: str | None = None) -> None:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
