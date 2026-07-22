from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.institution_types import (
	COMPANY_INSTITUTION_TYPE_FIELD,
	DEFAULT_INSTITUTION_TYPE,
	normalize_institution_type_code,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches
from eduedge.services.institution_context import (
	get_effective_institution_context,
	get_institution_type_options,
)

MAX_OPTIONS = 100


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _validate_institution_type(value: str | None, *, required: bool) -> str:
	code = normalize_institution_type_code(value)
	if not code:
		if required:
			frappe.throw(_("Institution Type is required for an EduEdge School Branch."), frappe.ValidationError)
		return ""
	if not frappe.db.exists("EduEdge Institution Type", {"name": code, "enabled": 1}):
		frappe.throw(_("Select an enabled EduEdge Institution Type."), frappe.ValidationError)
	return code


def build_institution_type_setup() -> dict:
	companies = []
	if frappe.has_permission("Company", "read"):
		company_fields = ["name", "company_name"]
		if frappe.get_meta("Company").has_field(COMPANY_INSTITUTION_TYPE_FIELD):
			company_fields.append(COMPANY_INSTITUTION_TYPE_FIELD)
		rows = frappe.get_list(
			"Company",
			filters={"is_group": 0},
			fields=company_fields,
			order_by="company_name asc",
			limit_page_length=MAX_OPTIONS,
		)
		for row in rows:
			configured = row.get(COMPANY_INSTITUTION_TYPE_FIELD) or ""
			context = get_effective_institution_context(company=row.name)
			companies.append(
				{
					"name": row.name,
					"label": row.company_name or row.name,
					"configured_institution_type": configured,
					"effective_institution_type": context["institution_type"],
					"effective_institution_type_name": context["institution_type_name"],
					"uses_secondary_fallback": context["uses_secondary_fallback"],
				}
			)

	branches = []
	for row in get_allowed_school_branches()[:MAX_OPTIONS]:
		context = get_effective_institution_context(branch=row.get("name"))
		branches.append(
			{
				"name": row.get("name"),
				"label": row.get("branch_name") or row.get("name"),
				"company": row.get("company") or "",
				"institution_type": row.get("institution_type") or context["institution_type"],
				"institution_type_name": context["institution_type_name"],
				"enabled": int(row.get("enabled", 1) or 0),
			}
		)

	return {
		"institution_types": get_institution_type_options(),
		"companies": companies,
		"branches": branches,
		"active_context": get_effective_institution_context(),
		"fallback_institution_type": DEFAULT_INSTITUTION_TYPE,
		"can_write_company": bool(frappe.has_permission("Company", "write")),
		"can_write_branch": bool(frappe.has_permission("EduEdge School Branch", "write")),
	}


@frappe.whitelist()
def get_institution_type_setup() -> dict:
	_require_login()
	if not frappe.has_permission("EduEdge Institution Type", "read"):
		frappe.throw(_("You are not permitted to view EduEdge Institution Types."), frappe.PermissionError)
	return build_institution_type_setup()


@frappe.whitelist()
def save_company_institution_type(company: str, institution_type: str | None = None) -> dict:
	_require_login()
	if not frappe.get_meta("Company").has_field(COMPANY_INSTITUTION_TYPE_FIELD):
		frappe.throw(_("EduEdge Company Institution Type is not installed."), frappe.ValidationError)
	code = _validate_institution_type(institution_type, required=False)
	company_doc = frappe.get_doc("Company", company)
	company_doc.check_permission("write")
	if company_doc.is_group:
		frappe.throw(_("A group Company cannot be configured as an EduEdge institution owner."), frappe.ValidationError)
	require_eduedge_access(feature_key="foundation", action="save_company_institution_type")
	company_doc.set(COMPANY_INSTITUTION_TYPE_FIELD, code or None)
	company_doc.save()
	frappe.clear_cache(doctype="Company")
	return {
		"company": company_doc.name,
		"configured_institution_type": code,
		"context": get_effective_institution_context(company=company_doc.name),
	}


@frappe.whitelist()
def save_branch_institution_type(branch: str, institution_type: str) -> dict:
	_require_login()
	code = _validate_institution_type(institution_type, required=True)
	allowed = {row.get("name") for row in get_allowed_school_branches()}
	if branch not in allowed:
		frappe.throw(_("You are not permitted to configure this School Branch."), frappe.PermissionError)
	branch_doc = frappe.get_doc("EduEdge School Branch", branch)
	branch_doc.check_permission("write")
	require_eduedge_access(feature_key="foundation", action="save_branch_institution_type")
	branch_doc.institution_type = code
	branch_doc.save()
	frappe.clear_cache(doctype="EduEdge School Branch")
	return {
		"branch": branch_doc.name,
		"institution_type": code,
		"context": get_effective_institution_context(branch=branch_doc.name),
	}
