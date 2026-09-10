from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

USER_DEFAULT_KEY = "eduedge_school_branch"
USER_SCOPE_KEY = "eduedge_branch_scope"
USER_COMPANY_KEY = "eduedge_branch_company"
USER_INSTITUTION_KEY = "eduedge_branch_institution"
ALL_BRANCHES_KEY = "__all__"

ASSIGNMENT_SCOPE_COMPANY = "Company"
ASSIGNMENT_SCOPE_INSTITUTION = "Institution"
ASSIGNMENT_SCOPE_BRANCH = "Branch"
ASSIGNMENT_SCOPES = {
	ASSIGNMENT_SCOPE_COMPANY,
	ASSIGNMENT_SCOPE_INSTITUTION,
	ASSIGNMENT_SCOPE_BRANCH,
}

ACTIVE_SCOPE_BRANCH = "branch"
ACTIVE_SCOPE_INSTITUTION = "institution_all"
ACTIVE_SCOPE_COMPANY = "company_all"
LEGACY_ACTIVE_SCOPE_ALL = "all"

PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}


def _assert_user_scope(user: str) -> None:
	if user == frappe.session.user:
		return
	if not _is_privileged_user(frappe.session.user):
		frappe.throw(_("You cannot manage another user's EduEdge access context."), frappe.PermissionError)


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


def get_allowed_institutions(
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
		return _get_institution_rows(filters=filters)

	if not is_branch_access_enforced():
		method = frappe.get_all if resolved_user != frappe.session.user else frappe.get_list
		return method(
			"EduEdge Institution",
			filters=filters,
			fields=_institution_fields(),
			order_by="is_default desc, institution_name asc",
			limit_page_length=0,
		)

	access_rows = _get_active_access_rows(resolved_user)
	direct_institutions = {
		row.institution
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_INSTITUTION and row.institution
	}
	direct_branches = {
		row.school_branch
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_BRANCH and row.school_branch
	}
	if direct_branches:
		direct_institutions.update(
			value
			for value in frappe.get_all(
				"EduEdge School Branch",
				filters={"name": ["in", sorted(direct_branches)]},
				pluck="institution",
				limit_page_length=0,
			)
			if value
		)
	company_scopes = {
		row.company
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_COMPANY and row.company
	}
	if company:
		direct_institutions = {
			value
			for value in direct_institutions
			if frappe.db.get_value("EduEdge Institution", value, "company") == company
		}
		company_scopes = {value for value in company_scopes if value == company}

	or_filters = []
	if direct_institutions:
		or_filters.append(["name", "in", sorted(direct_institutions)])
	if company_scopes:
		or_filters.append(["company", "in", sorted(company_scopes)])
	if not or_filters:
		return []

	return frappe.get_all(
		"EduEdge Institution",
		filters=filters,
		or_filters=or_filters,
		fields=_institution_fields(),
		order_by="is_default desc, institution_name asc",
		limit_page_length=0,
	)


def get_allowed_school_branches(
	*,
	user: str | None = None,
	company: str | None = None,
	institution: str | None = None,
) -> list[dict]:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	filters: dict = {"enabled": 1}
	if company:
		filters["company"] = company
	if institution:
		filters["institution"] = institution

	if _is_privileged_user(resolved_user):
		return _with_institution_names(_get_branch_rows(filters=filters))

	if not is_branch_access_enforced():
		method = frappe.get_all if resolved_user != frappe.session.user else frappe.get_list
		rows = method(
			"EduEdge School Branch",
			filters=filters,
			fields=_branch_fields(),
			order_by="is_default desc, branch_name asc",
			limit_page_length=0,
		)
		return _with_institution_names(rows)

	access_rows = _get_active_access_rows(resolved_user)
	direct_branches = {
		row.school_branch
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_BRANCH and row.school_branch
	}
	institution_scopes = {
		row.institution
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_INSTITUTION and row.institution
	}
	company_scopes = {
		row.company
		for row in access_rows
		if row.access_scope == ASSIGNMENT_SCOPE_COMPANY and row.company
	}
	if company:
		company_scopes = {value for value in company_scopes if value == company}
	if institution:
		institution_scopes = {value for value in institution_scopes if value == institution}

	or_filters = []
	if direct_branches:
		or_filters.append(["name", "in", sorted(direct_branches)])
	if institution_scopes:
		or_filters.append(["institution", "in", sorted(institution_scopes)])
	if company_scopes:
		or_filters.append(["company", "in", sorted(company_scopes)])
	if not or_filters:
		return []

	rows = frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		or_filters=or_filters,
		fields=_branch_fields(),
		order_by="is_default desc, branch_name asc",
		limit_page_length=0,
	)
	return _with_institution_names(rows)


def get_branch_access_profile(*, user: str | None = None) -> dict:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	allowed = get_allowed_school_branches(user=resolved_user)
	allowed_institutions = get_allowed_institutions(user=resolved_user)
	access_rows = _get_active_access_rows(resolved_user) if is_branch_access_enforced() else []
	privileged = _is_privileged_user(resolved_user)

	company_scopes = sorted(
		{
			row.company
			for row in access_rows
			if row.access_scope == ASSIGNMENT_SCOPE_COMPANY and row.company
		}
	)
	institution_scopes = sorted(
		{
			row.institution
			for row in access_rows
			if row.access_scope == ASSIGNMENT_SCOPE_INSTITUTION and row.institution
		}
	)
	if privileged:
		company_scopes = sorted({row.get("company") for row in allowed_institutions if row.get("company")})
		institution_scopes = sorted({row.get("name") for row in allowed_institutions if row.get("name")})

	assignment_default = next(
		(
			row.school_branch
			for row in access_rows
			if row.access_scope == ASSIGNMENT_SCOPE_BRANCH
			and row.is_default_branch
			and row.school_branch
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
		or bool(company_scopes)
		or bool(institution_scopes)
	)
	if not default_branch and allowed and not can_switch:
		default_branch = allowed[0]["name"]
	can_view_all = bool(
		is_hq_all_branch_view_enabled()
		and (privileged or company_scopes or institution_scopes)
	)

	saved_scope = frappe.defaults.get_user_default(USER_SCOPE_KEY, user=resolved_user)
	active_access_scope = _normalise_active_scope(saved_scope)
	active_company = frappe.defaults.get_user_default(USER_COMPANY_KEY, user=resolved_user)
	active_institution = frappe.defaults.get_user_default(USER_INSTITUTION_KEY, user=resolved_user)

	if not saved_scope and len(institution_scopes) == 1 and not assignment_default:
		active_access_scope = ACTIVE_SCOPE_INSTITUTION
		active_institution = institution_scopes[0]

	institution_map = {
		row["name"]: row
		for row in allowed_institutions
		if row.get("name")
	}
	if active_access_scope == ACTIVE_SCOPE_INSTITUTION:
		if not active_institution:
			active_institution = institution_scopes[0] if len(institution_scopes) == 1 else None
		if not active_institution or (
			not privileged and active_institution not in institution_scopes
		):
			active_access_scope = ACTIVE_SCOPE_BRANCH
			active_institution = None
		else:
			active_company = (institution_map.get(active_institution) or {}).get("company")
	elif active_access_scope == ACTIVE_SCOPE_COMPANY:
		if not active_company:
			active_company = company_scopes[0] if len(company_scopes) == 1 else None
		if not active_company or (
			not privileged and active_company not in company_scopes
		):
			active_access_scope = ACTIVE_SCOPE_BRANCH
			active_company = None
	else:
		active_access_scope = ACTIVE_SCOPE_BRANCH

	return {
		"enforcement_enabled": is_branch_access_enforced(),
		"legacy_fallback": not is_branch_access_enforced(),
		"allowed_branch_count": len(allowed),
		"allowed_branches": allowed,
		"allowed_institution_count": len(allowed_institutions),
		"allowed_institutions": allowed_institutions,
		"default_branch": default_branch,
		"can_switch_branch": can_switch,
		"can_view_all_branches": can_view_all,
		"all_branch_companies": company_scopes,
		"all_branch_institutions": institution_scopes,
		"active_scope": LEGACY_ACTIVE_SCOPE_ALL
		if active_access_scope in {ACTIVE_SCOPE_INSTITUTION, ACTIVE_SCOPE_COMPANY}
		else ACTIVE_SCOPE_BRANCH,
		"active_access_scope": active_access_scope,
		"active_company": active_company,
		"active_institution": active_institution,
	}


def get_current_school_branch(*, user: str | None = None) -> dict | None:
	resolved_user = user or frappe.session.user
	profile = get_branch_access_profile(user=resolved_user)
	active_access_scope = profile["active_access_scope"]

	if active_access_scope == ACTIVE_SCOPE_INSTITUTION:
		institution = next(
			(
				row
				for row in profile["allowed_institutions"]
				if row.get("name") == profile.get("active_institution")
			),
			{},
		)
		return {
			"name": None,
			"branch_name": _("All Branches — {0}").format(
				institution.get("institution_name") or institution.get("name")
			),
			"company": institution.get("company"),
			"institution": institution.get("name"),
			"institution_name": institution.get("institution_name"),
			"institution_type": institution.get("institution_type"),
			"is_all_branches": 1,
			"all_scope": ASSIGNMENT_SCOPE_INSTITUTION,
		}

	if active_access_scope == ACTIVE_SCOPE_COMPANY:
		return {
			"name": None,
			"branch_name": _("All Branches"),
			"company": profile.get("active_company"),
			"institution": None,
			"institution_name": None,
			"institution_type": None,
			"is_all_branches": 1,
			"all_scope": ASSIGNMENT_SCOPE_COMPANY,
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
	active_institution = profile.get("active_institution")
	if current_branch:
		active_company = current_branch.get("company") or active_company
		active_institution = current_branch.get("institution") or active_institution
	return {
		**profile,
		"current_branch": current_branch,
		"active_company": active_company,
		"active_institution": active_institution,
		"all_branches_key": ALL_BRANCHES_KEY,
		"active_label": (current_branch or {}).get("branch_name") or _("Select Branch"),
	}


def switch_school_branch(
	branch: str,
	*,
	company: str | None = None,
	institution: str | None = None,
	user: str | None = None,
) -> dict:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	profile = get_branch_access_profile(user=resolved_user)

	if branch == ALL_BRANCHES_KEY:
		if not profile["can_view_all_branches"]:
			frappe.throw(_("You are not authorised to use the All Branches view."), frappe.PermissionError)

		institutions = profile["all_branch_institutions"]
		selected_institution = institution or profile.get("active_institution")
		if not selected_institution and len(institutions) == 1:
			selected_institution = institutions[0]
		if selected_institution and selected_institution in institutions:
			institution_row = next(
				(
					row
					for row in profile["allowed_institutions"]
					if row.get("name") == selected_institution
				),
				None,
			)
			if not institution_row:
				frappe.throw(_("Select a permitted Institution for the All Branches view."), frappe.PermissionError)
			selected_company = institution_row.get("company")
			frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
			frappe.defaults.set_user_default(USER_SCOPE_KEY, ACTIVE_SCOPE_INSTITUTION, user=resolved_user)
			frappe.defaults.set_user_default(USER_INSTITUTION_KEY, selected_institution, user=resolved_user)
			frappe.defaults.set_user_default(USER_COMPANY_KEY, selected_company, user=resolved_user)
			frappe.defaults.set_user_default("company", selected_company, user=resolved_user)
			return {
				"name": ALL_BRANCHES_KEY,
				"branch_name": _("All Branches — {0}").format(
					institution_row.get("institution_name") or selected_institution
				),
				"company": selected_company,
				"institution": selected_institution,
				"institution_name": institution_row.get("institution_name"),
				"institution_type": institution_row.get("institution_type"),
				"is_all_branches": 1,
				"all_scope": ASSIGNMENT_SCOPE_INSTITUTION,
			}

		companies = profile["all_branch_companies"]
		selected_company = company or profile.get("active_company")
		if companies and selected_company not in companies:
			selected_company = companies[0] if len(companies) == 1 else None
		if not selected_company:
			frappe.throw(_("Select the Company for the All Branches view."), frappe.ValidationError)
		frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
		frappe.defaults.clear_default(USER_INSTITUTION_KEY, parent=resolved_user)
		frappe.defaults.set_user_default(USER_SCOPE_KEY, ACTIVE_SCOPE_COMPANY, user=resolved_user)
		frappe.defaults.set_user_default(USER_COMPANY_KEY, selected_company, user=resolved_user)
		frappe.defaults.set_user_default("company", selected_company, user=resolved_user)
		return {
			"name": ALL_BRANCHES_KEY,
			"branch_name": _("All Branches"),
			"company": selected_company,
			"institution": None,
			"is_all_branches": 1,
			"all_scope": ASSIGNMENT_SCOPE_COMPANY,
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

	selected = allowed[branch]
	frappe.defaults.set_user_default(USER_DEFAULT_KEY, branch, user=resolved_user)
	frappe.defaults.set_user_default(USER_SCOPE_KEY, ACTIVE_SCOPE_BRANCH, user=resolved_user)
	frappe.defaults.set_user_default(USER_COMPANY_KEY, selected["company"], user=resolved_user)
	if selected.get("institution"):
		frappe.defaults.set_user_default(USER_INSTITUTION_KEY, selected["institution"], user=resolved_user)
	else:
		frappe.defaults.clear_default(USER_INSTITUTION_KEY, parent=resolved_user)
	frappe.defaults.set_user_default("company", selected["company"], user=resolved_user)
	return selected


def clear_school_branch(*, user: str | None = None) -> None:
	resolved_user = user or frappe.session.user
	_assert_user_scope(resolved_user)
	frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=resolved_user)
	frappe.defaults.clear_default(USER_SCOPE_KEY, parent=resolved_user)
	frappe.defaults.clear_default(USER_COMPANY_KEY, parent=resolved_user)
	frappe.defaults.clear_default(USER_INSTITUTION_KEY, parent=resolved_user)


def invalidate_user_branch_context(user: str) -> None:
	if not user or user == "Guest":
		return
	allowed = {row["name"] for row in get_allowed_school_branches(user=user)}
	current = frappe.defaults.get_user_default(USER_DEFAULT_KEY, user=user)
	if current and current not in allowed:
		frappe.defaults.clear_default(USER_DEFAULT_KEY, parent=user)

	profile = get_branch_access_profile(user=user)
	saved_scope = _normalise_active_scope(
		frappe.defaults.get_user_default(USER_SCOPE_KEY, user=user)
	)
	if saved_scope != profile["active_access_scope"]:
		frappe.defaults.clear_default(USER_SCOPE_KEY, parent=user)
		frappe.defaults.clear_default(USER_COMPANY_KEY, parent=user)
		frappe.defaults.clear_default(USER_INSTITUTION_KEY, parent=user)


def _normalise_active_scope(value: str | None) -> str:
	if value == LEGACY_ACTIVE_SCOPE_ALL:
		return ACTIVE_SCOPE_COMPANY
	if value in {ACTIVE_SCOPE_BRANCH, ACTIVE_SCOPE_INSTITUTION, ACTIVE_SCOPE_COMPANY}:
		return value
	return ACTIVE_SCOPE_BRANCH


def _get_active_access_rows(user: str) -> list[frappe._dict]:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return []
	meta = frappe.get_meta("EduEdge User Branch Access")
	fields = [
		"name",
		"user",
		"company",
		"school_branch",
		"hq_all_branch_access",
		"is_default_branch",
		"can_switch_branch",
		"valid_from",
		"valid_to",
	]
	if meta.has_field("access_scope"):
		fields.append("access_scope")
	if meta.has_field("institution"):
		fields.append("institution")
	rows = frappe.get_all(
		"EduEdge User Branch Access",
		filters={"user": user, "enabled": 1},
		fields=fields,
		order_by="is_default_branch desc, modified desc",
		limit_page_length=0,
	)
	today = getdate(nowdate())
	active_rows = [
		row
		for row in rows
		if (not row.valid_from or getdate(row.valid_from) <= today)
		and (not row.valid_to or getdate(row.valid_to) >= today)
	]
	for row in active_rows:
		_normalise_access_row(row)
	return active_rows


def _normalise_access_row(row) -> None:
	scope = row.get("access_scope")
	if scope not in ASSIGNMENT_SCOPES:
		if cint(row.get("hq_all_branch_access")):
			scope = ASSIGNMENT_SCOPE_COMPANY
		elif row.get("institution") and not row.get("school_branch"):
			scope = ASSIGNMENT_SCOPE_INSTITUTION
		else:
			scope = ASSIGNMENT_SCOPE_BRANCH
	row.access_scope = scope

	if scope == ASSIGNMENT_SCOPE_BRANCH and row.get("school_branch"):
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			row.school_branch,
			["company", "institution"],
			as_dict=True,
		)
		if branch:
			row.company = branch.company
			row.institution = branch.institution
	elif scope == ASSIGNMENT_SCOPE_INSTITUTION and row.get("institution"):
		row.company = frappe.db.get_value("EduEdge Institution", row.institution, "company")


def _get_branch_rows(*, filters: dict) -> list[dict]:
	return frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		fields=_branch_fields(),
		order_by="is_default desc, branch_name asc",
		limit_page_length=0,
	)


def _get_institution_rows(*, filters: dict) -> list[dict]:
	return frappe.get_all(
		"EduEdge Institution",
		filters=filters,
		fields=_institution_fields(),
		order_by="is_default desc, institution_name asc",
		limit_page_length=0,
	)


def _with_institution_names(rows: list[dict]) -> list[dict]:
	institution_names = {
		row.name: row.institution_name
		for row in frappe.get_all(
			"EduEdge Institution",
			filters={
				"name": [
					"in",
					sorted({row.get("institution") for row in rows if row.get("institution")}),
				]
			},
			fields=["name", "institution_name"],
			limit_page_length=0,
		)
	} if rows else {}
	for row in rows:
		row["institution_name"] = institution_names.get(row.get("institution"))
	return rows


def _branch_fields() -> list[str]:
	return [
		"name",
		"branch_name",
		"branch_code",
		"branch_type",
		"company",
		"institution",
		"institution_type",
		"cost_center",
		"default_warehouse",
		"platform_branch_id",
		"is_main_branch",
		"is_default",
	]


def _institution_fields() -> list[str]:
	return [
		"name",
		"institution_name",
		"institution_code",
		"company",
		"institution_type",
		"is_default",
	]
