from __future__ import annotations

import frappe

from eduedge.platform.runtime_context import get_product_identity
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)
from eduedge.services.institution_context import get_effective_institution_context


def _get_company_identity(company: str) -> dict:
	if not company or not frappe.db.exists("Company", company):
		return {"name": company or "", "label": company or "", "logo": ""}

	fields = ["name", "company_name"]
	meta = frappe.get_meta("Company")
	if meta.has_field("company_logo"):
		fields.append("company_logo")
	row = frappe.db.get_value("Company", company, fields, as_dict=True) or {}
	return {
		"name": row.get("name") or company,
		"label": row.get("company_name") or row.get("name") or company,
		"logo": row.get("company_logo") or "",
	}


def _get_user_identity() -> dict:
	user = frappe.session.user
	row = frappe.db.get_value(
		"User",
		user,
		["name", "full_name", "email", "user_image"],
		as_dict=True,
	) or {}
	return {
		"name": row.get("name") or user,
		"full_name": row.get("full_name") or user,
		"email": row.get("email") or user,
		"image": row.get("user_image") or "",
	}


def extend_bootinfo(bootinfo) -> None:
	"""Expose permission-safe identity and institution terminology for EdgeSuite UI."""
	if frappe.session.user == "Guest":
		return

	allowed_branches = []
	current_branch = None
	try:
		allowed_branches = get_allowed_school_branches()
		current_branch = get_current_school_branch()
	except Exception:
		# Boot must remain available even while a site is being configured or migrated.
		allowed_branches = []
		current_branch = None

	company_names = {
		row.get("company")
		for row in allowed_branches
		if row.get("company")
	}
	if (current_branch or {}).get("company"):
		company_names.add(current_branch["company"])

	companies = {
		company: _get_company_identity(company)
		for company in sorted(company_names)
	}
	active_company = (current_branch or {}).get("company")
	active_identity = companies.get(active_company) or {
		"name": active_company or "",
		"label": active_company or "",
		"logo": "",
	}
	product_identity = get_product_identity()
	try:
		institution_context = get_effective_institution_context(
			company=active_company,
			branch=(current_branch or {}).get("name"),
		)
	except Exception:
		institution_context = {
			"institution_type": "SECONDARY",
			"institution_type_name": "Secondary School",
			"source": "system_fallback",
			"company": active_company or "",
			"branch": (current_branch or {}).get("name") or "",
			"branch_name": (current_branch or {}).get("branch_name") or "",
			"terms": {},
			"uses_secondary_fallback": 1,
		}

	identity = {
		"product_code": product_identity["product_code"],
		"product_name": product_identity["product_name"],
		"product_logo": product_identity["product_logo"],
		"product_identity_source": product_identity["source"],
		"product_icon": "graduation",
		"product_subtitle": "Education Management",
		"tenant_name": active_identity.get("label") or active_identity.get("name") or "",
		"tenant_logo": active_identity.get("logo") or "",
		"tenant_icon": "building",
		"tenant_subtitle": institution_context.get("institution_type_name") or "School workspace",
		"companies": companies,
		"user": _get_user_identity(),
		"institution_context": institution_context,
	}

	bootinfo["eduedge_institution_context"] = institution_context
	bootinfo["eduedge_ui_identity"] = identity
	shared = bootinfo.get("edgesuite_ui_identity") or {}
	shared["eduedge"] = identity
	bootinfo["edgesuite_ui_identity"] = shared
