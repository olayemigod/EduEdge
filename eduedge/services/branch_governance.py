from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.services.branch_accounting import ACCOUNTING_FIELDS, get_missing_core_defaults
from eduedge.services.branch_context import (
	invalidate_user_branch_context,
	is_branch_access_enforced,
	is_hq_all_branch_view_enabled,
)

ACCESS_FIELDS = (
	"user",
	"branch_role",
	"hq_all_branch_access",
	"company",
	"school_branch",
	"is_default_branch",
	"can_switch_branch",
	"enabled",
	"valid_from",
	"valid_to",
)

MISSING_ACCOUNTING_LABELS = {
	"cost_center": "Default Cost Center",
	"school_fees_income_account": "School Fees Income Account",
	"default_receivable_account": "Default Receivable Account",
	"default_cash_or_bank_account": "Cash, Bank, or Payment Gateway Account",
}


def get_branch_governance_context(*, company: str | None = None) -> dict:
	branches = _get_branch_rows(company=company)
	assignments = _get_access_rows(company=company)
	active_assignments = [row for row in assignments if row["status"] == "Active"]

	hq_companies = {
		row["company"]
		for row in active_assignments
		if row.get("hq_all_branch_access") and row.get("company")
	}
	direct_assignment_count: dict[str, int] = {}
	for row in active_assignments:
		if row.get("school_branch"):
			direct_assignment_count[row["school_branch"]] = (
				direct_assignment_count.get(row["school_branch"], 0) + 1
			)

	covered_branch_count = 0
	accounting_ready_count = 0
	for branch in branches:
		branch["direct_assignment_count"] = direct_assignment_count.get(branch["name"], 0)
		branch["covered_by_hq"] = branch["company"] in hq_companies
		branch["access_covered"] = bool(
			branch["direct_assignment_count"] or branch["covered_by_hq"]
		)
		if branch["access_covered"]:
			covered_branch_count += 1

		missing = get_missing_core_defaults(branch)
		branch["missing_accounting_defaults"] = missing
		branch["missing_accounting_labels"] = [
			MISSING_ACCOUNTING_LABELS.get(fieldname, fieldname.replace("_", " ").title())
			for fieldname in missing
		]
		branch["accounting_ready"] = not missing
		if branch["accounting_ready"]:
			accounting_ready_count += 1

	activation_checks = [
		{
			"key": "branches",
			"label": "At least one enabled School Branch / Campus exists",
			"passed": bool(branches),
			"blocking": True,
		},
		{
			"key": "assignments",
			"label": "At least one active User Branch Access assignment exists",
			"passed": bool(active_assignments),
			"blocking": True,
		},
		{
			"key": "coverage",
			"label": "Every enabled campus is covered by a direct or company HQ assignment",
			"passed": bool(branches) and covered_branch_count == len(branches),
			"blocking": True,
		},
		{
			"key": "accounting",
			"label": "Every enabled campus has core accounting defaults",
			"passed": bool(branches) and accounting_ready_count == len(branches),
			"blocking": False,
		},
	]
	blocking_failures = [row for row in activation_checks if row["blocking"] and not row["passed"]]

	return {
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name")
			or frappe.session.user,
		},
		"companies": _get_companies(),
		"selected_company": company,
		"branches": branches,
		"assignments": assignments,
		"settings": {
			"enforcement_enabled": is_branch_access_enforced(),
			"hq_all_branch_view_enabled": is_hq_all_branch_view_enabled(),
		},
		"counts": {
			"enabled_branches": len(branches),
			"active_assignments": len(active_assignments),
			"covered_branches": covered_branch_count,
			"accounting_ready_branches": accounting_ready_count,
		},
		"activation_checks": activation_checks,
		"can_enable_enforcement": not blocking_failures,
	}


def save_branch_access(payload: str | dict) -> dict:
	values = json.loads(payload) if isinstance(payload, str) else dict(payload or {})
	name = values.pop("name", None)

	if name:
		doc = frappe.get_doc("EduEdge User Branch Access", name)
		if not doc.has_permission("write"):
			frappe.throw(_("You are not permitted to update this branch assignment."), frappe.PermissionError)
	else:
		if not frappe.has_permission("EduEdge User Branch Access", "create"):
			frappe.throw(_("You are not permitted to create branch assignments."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge User Branch Access")

	for fieldname in ACCESS_FIELDS:
		if fieldname in values:
			doc.set(fieldname, values.get(fieldname))
	doc.save()
	return _serialize_access_doc(doc)


def set_branch_access_enabled(name: str, enabled: int | str) -> dict:
	doc = frappe.get_doc("EduEdge User Branch Access", name)
	if not doc.has_permission("write"):
		frappe.throw(_("You are not permitted to change this branch assignment."), frappe.PermissionError)
	doc.enabled = cint(enabled)
	doc.save()
	invalidate_user_branch_context(doc.user)
	return _serialize_access_doc(doc)


def set_branch_enforcement(enabled: int | str, *, confirmed: int | str = 0) -> dict:
	target = bool(cint(enabled))
	if not cint(confirmed):
		frappe.throw(_("Confirm this branch-enforcement change before continuing."), frappe.ValidationError)

	if target:
		context = get_branch_governance_context()
		failures = [
			row["label"]
			for row in context["activation_checks"]
			if row["blocking"] and not row["passed"]
		]
		if failures:
			frappe.throw(
				_("Branch enforcement cannot be enabled until these checks pass: {0}").format(
					"; ".join(failures)
				),
				frappe.ValidationError,
			)

	settings = frappe.get_single("EduEdge Settings")
	if not settings.has_permission("write"):
		frappe.throw(_("You are not permitted to change EduEdge branch enforcement."), frappe.PermissionError)
	settings.enable_user_branch_access_enforcement = int(target)
	settings.save()
	return get_branch_governance_context()


def _get_companies() -> list[dict]:
	return frappe.get_all(
		"Company",
		filters={"is_group": 0},
		fields=["name", "company_name"],
		order_by="company_name asc",
	)


def _get_branch_rows(*, company: str | None = None) -> list[dict]:
	meta = frappe.get_meta("EduEdge School Branch")
	fields = [
		"name",
		"branch_name",
		"branch_code",
		"branch_type",
		"company",
		"is_main_branch",
		"is_default",
		"enabled",
	]
	fields.extend(fieldname for fieldname in ACCOUNTING_FIELDS if fieldname != "company" and meta.has_field(fieldname))
	filters: dict = {"enabled": 1}
	if company:
		filters["company"] = company
	return [
		dict(row)
		for row in frappe.get_all(
			"EduEdge School Branch",
			filters=filters,
			fields=fields,
			order_by="company asc, is_default desc, branch_name asc",
		)
	]


def _get_access_rows(*, company: str | None = None) -> list[dict]:
	if not frappe.db.exists("DocType", "EduEdge User Branch Access"):
		return []
	filters = {"company": company} if company else None
	rows = frappe.get_all(
		"EduEdge User Branch Access",
		filters=filters,
		fields=[
			"name",
			"user",
			"user_full_name",
			"branch_role",
			"hq_all_branch_access",
			"company",
			"school_branch",
			"branch_name",
			"is_default_branch",
			"can_switch_branch",
			"enabled",
			"valid_from",
			"valid_to",
			"modified",
		],
		order_by="enabled desc, user_full_name asc, company asc, branch_name asc",
	)
	user_names = sorted({row.user for row in rows if row.user})
	enabled_users = set(
		frappe.get_all(
			"User",
			filters={"name": ["in", user_names], "enabled": 1},
			pluck="name",
		)
	) if user_names else set()
	enabled_branches = set(
		frappe.get_all(
			"EduEdge School Branch",
			filters={"enabled": 1},
			pluck="name",
		)
	)
	today = getdate(nowdate())
	return [
		{
			**dict(row),
			"status": _get_assignment_status(
				row,
				today=today,
				enabled_users=enabled_users,
				enabled_branches=enabled_branches,
			),
		}
		for row in rows
	]


def _get_assignment_status(row, *, today, enabled_users: set[str], enabled_branches: set[str]) -> str:
	if not row.enabled:
		return "Disabled"
	if row.user not in enabled_users:
		return "User Disabled"
	if row.valid_from and getdate(row.valid_from) > today:
		return "Not Yet Active"
	if row.valid_to and getdate(row.valid_to) < today:
		return "Expired"
	if row.school_branch and row.school_branch not in enabled_branches:
		return "Branch Disabled"
	return "Active"


def _serialize_access_doc(doc) -> dict:
	return {
		"name": doc.name,
		**{fieldname: doc.get(fieldname) for fieldname in ACCESS_FIELDS},
		"user_full_name": doc.get("user_full_name")
		or frappe.db.get_value("User", doc.user, "full_name"),
		"branch_name": doc.get("branch_name")
		or (frappe.db.get_value("EduEdge School Branch", doc.school_branch, "branch_name") if doc.school_branch else None),
	}
