from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

USER_DEFAULT_KEY = "eduedge_school_branch"
USER_SCOPE_KEY = "eduedge_branch_scope"
USER_COMPANY_KEY = "eduedge_branch_company"
ALL_BRANCHES_KEY = "__all__"

PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}


def _assert_user_scope(user: str) -> None:
	if user == frappe.session.user:
		return
	if not _is_privileged_user(frappe.session.user):
		frappe.throw(_("You cannot manage another user's EduEdge branch context."), frappe.PermissionError)


def _is_privileged_user(user: str) -> bool:
	if user == "Administrator":
		return True
	return bool(PRIVILEGED_ROLES.intersection(frappe.get_roles(user)))


def is_branch_access_enforced() -> bool:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return False
	if not frappe.get_meta("EduEdge Settings").has_field("enable_user_branch_access_enforcement"):
		return False
	return bool(
		cint(frappe.db.get_single_value("EduEdge Settings", "enable_user_branch_access_enforcement"))
	)


def is_hq_all_branch_view_enabled() -> bool:
	if not frappe.get_meta("EduEdge Settings").has_field("allow_hq_all_branch_view"):
		return True
	value = frappe.db.get_single_value("EduEdge Settings", "allow_hq_all_branch_view")
	return True if value in (None, "") else bool(cint(value))


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

	if _is_privileged_user(resolved_user):
		return _get_branch_rows(filters=filters)

	if not is_branch_access_enforced():
		if resolved_user != frappe.session.user:
			return frappe.get_all(
				"EduEdge School Branch",
				filters=filters,
				fields=_branch_fields(),
				order_by="is_default desc, branch_name asc",
			)
		return frappe.get_list(
			"EduEdge School Branch",
			filters=filters,
			fields=_branch_fields(),
			order_by="is_default desc, branch_name asc",
		)

	access_rows = _get_active_access_rows(resolved_user)
	direct_branches = {
		row.school_branch
		for row in access_rows
		if not row.hq_all_branch_access and row.school_branch
	}
	hq_companies = {
		row.company
		for row in access_rows
		if row.hq_all_branch_access and row.company
	}
	if company:
		hq_companies = {value for value in hq_companies if value == company}

	or_filters = []
	if direct_branches:
		or_filters.append(["name", "in", sorted(direct_branches)])
	if hq_companies:
		or_filters.append(["company", "in", sorted(hq_companies)])
	if not or_filters:
		return []

	return frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		or_filters=or_filters,
		fields=_branch_fields(),
		order_by="is_default desc, branch_name asc",
	)


def get_branch_access_profile(*, user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	allowed = get_allowed_school_branches(user=resolved_user)
	access_rows = _get_active_access_rows(resolved_user) if is_branch_access_enforced() else []
	privileged = _is_privileged_user(resolved_user)
	hq_companies = sorted(
		{
			row.company
			for row in access_rows
			if row.hq_all_branch_access and row.company
		}
	)
	if privileged:
		hq_companies = sorted({row.get("company") for row in allowed if row.get("company")})

	assignment_default = next(
		(
			row.school_branch
			for row in access_rows
			if row.is_default_branch and row.school_branch
		),
		None,
	)
	branch_default = next((row["name"] for row in allowed if row.get("is_default")), None)
	default_branch = assignment_default or branch_default or (allowed[0]["name"] if len(allowed) == 1 else None)
	can_switch = (
		privileged
		or not is_branch_access_enforced()
		or len(allowed) <= 1
		or any(row.can_switch_branch for row in access_rows)
		or bool(hq_companies)
	)
	if not default_branch and allowed and not can_switch:
		default_branch = allowed[0]["name"]
	can_view_all = bool(is_hq_all_branch_view_enabled() and (privileged or hq_companies))

	active_scope = frappe.defaults.get_user_default(USER_SCOPE_KEY, user=resolved_user) or "branch"
	active_company = frappe.defaults.get_user_default(USER_COMPANY_KEY, user=resolved_user)
	if active_scope == "all" and not can_view_all:
		frappe.defaults.clear_default(USER_SCOPE_KEY, parent=resolved_user)
		active_scope = "branch"
	if active_scope == "all" and hq_companies and active_company not in hq_companies:
		active_company = hq_companies[0] if len(hq_companies) == 1 else None

	return {
		"enforcement_enabled": is_branch_access_enforced(),
		"legacy_fallback": not is_branch_access_enforced(),
		"allowed_branch_count": len(allowed),
		"allowed_branches": allowed,
		"default_branch": default_branch,
		"can_switch_branch": can_switch,
		"can_view_all_branches": can_view_all,
		"all_branch_companies": hq_companies,
		"active_scope": active_scope,
		"active_company": active_company,
	}


def get_current_school_branch(*, user: str | None = None) -> dict | None:
	resolved_user = user or frappe.session.user
	profile = get_branch_access_profile(user=resolved_user)
	if profile["active_scope"] == "all":
		return {
			"name": None,
			"branch_name": _("All Branches"),
			"company": profile.get("active_company"),
			"is_all_branches": 1,
		}

	allowed = {row["name"]: row for row in profile["allowed_branches"]}
	branch_name = frappe.defaults.get_user_default(USER_DEFAULT_KEY, user=resolved_user)
	if branch_name:
		if branch_name in allowed:
			return allowed[branch_name]
		frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)

	default_branch = profile.get("default_branch")
	return allowed.get(default_branch) if default_branch else None


def get_active_branch_context(*, user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	profile = get_branch_access_profile(user=resolved_user)
	current_branch = get_current_school_branch(user=resolved_user)
	active_company = profile.get("active_company")
	if current_branch:
		active_company = current_branch.get("company")
	return {
		**profile,
		"current_branch": current_branch,
		"active_company": active_company,
		"all_branches_key": ALL_BRANCHES_KEY,
		"active_label": _("All Branches") if profile["active_scope"] == "all" else (
			(current_branch or {}).get("branch_name") or _("Select Branch")
		),
	}


def switch_school_branch(
	branch: str,
	*,
	company: str | None = None,
	user: str | None = None,
) -> dict:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	profile = get_branch_access_profile(user=resolved_user)

	if branch == ALL_BRANCHES_KEY:
		if not profile["can_view_all_branches"]:
			frappe.throw(_("You are not authorised to use the All Branches view."), frappe.PermissionError)
		companies = profile["all_branch_companies"]
		selected_company = company or profile.get("active_company")
		if companies and selected_company not in companies:
			selected_company = companies[0] if len(companies) == 1 else None
		if not selected_company:
			frappe.throw(_("Select the Company for the All Branches view."), frappe.ValidationError)
		frappe.defaults.set_user_default(USER_SCOPE_KEY, "all", user=resolved_user)
		frappe.defaults.set_user_default(USER_COMPANY_KEY, selected_company, user=resolved_user)
		frappe.defaults.set_user_default("company", selected_company, user=resolved_user)
		return {
			"name": ALL_BRANCHES_KEY,
			"branch_name": _("All Branches"),
			"company": selected_company,
			"is_all_branches": 1,
		}

	allowed = {row["name"]: row for row in profile["allowed_branches"]}
	if branch not in allowed:
		frappe.throw(_("You do not have access to the selected School Branch."), frappe.PermissionError)
	if (
		len(allowed) > 1
		and not profile["can_switch_branch"]
		and branch != profile.get("default_branch")
	):
		frappe.throw(_("Your branch access does not allow switching to another campus."), frappe.PermissionError)

	frappe.defaults.set_user_default(USER_DEFAULT_KEY, branch, user=resolved_user)
	frappe.defaults.set_user_default(USER_SCOPE_KEY, "branch", user=resolved_user)
	frappe.defaults.set_user_default(USER_COMPANY_KEY, allowed[branch]["company"], user=resolved_user)
	frappe.defaults.set_user_default("company", allowed[branch]["company"], user=resolved_user)
	return allowed[branch]


def clear_school_branch(*, user: str | None = None) -> None:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
	frappe.defaults.clear_default(USER_SCOPE_KEY, parent=resolved_user)
	frappe.defaults.clear_default(USER_COMPANY_KEY, parent=resolved_user)


def invalidate_user_branch_context(user: str) -> None:
	if not user or user == "Guest":
		return
	allowed = {row["name"] for row in get_allowed_school_branches(user=user)}
	current = frappe.defaults.get_user_default(USER_DEFAULT_KEY, user=user)
	if current and current not in allowed:
		frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=user)
	profile = get_branch_access_profile(user=user)
	if profile["active_scope"] == "all" and not profile["can_view_all_branches"]:
		frappe.defaults.clear_default(USER_SCOPE_KEY, parent=user)
		frappe.defaults.clear_default(USER_COMPANY_KEY, parent=user)


def _get_active_access_rows(user: str) -> list[frappe._dict]:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return []
	rows = frappe.get_all(
		"EduEdge User Branch Access",
		filters={"user": user, "enabled": 1},
		fields=[
			"name",
			"user",
			"company",
			"school_branch",
			"hq_all_branch_access",
			"is_default_branch",
			"can_switch_branch",
			"valid_from",
			"valid_to",
		],
		order_by="is_default_branch desc, modified desc",
	)
	today = getdate(nowdate())
	return [
		row
		for row in rows
		if (not row.valid_from or getdate(row.valid_from) <= today)
		and (not row.valid_to or getdate(row.valid_to) >= today)
	]


def _get_branch_rows(*, filters: dict) -> list[dict]:
	return frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		fields=_branch_fields(),
		order_by="is_default desc, branch_name asc",
	)


def _branch_fields() -> list[str]:
	return [
		"name",
		"branch_name",
		"branch_code",
		"branch_type",
		"company",
		"cost_center",
		"default_warehouse",
		"platform_branch_id",
		"is_main_branch",
		"is_default",
	]
