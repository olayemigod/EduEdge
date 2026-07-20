from __future__ import annotations

import frappe

from eduedge.platform.runtime_context import get_product_identity
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)


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
	"""Expose permission-safe identity metadata for the shared EdgeSuite shell.

	School identity remains on ERPNext Company. EduEdge product identity is
	centrally managed by CoreEdge and inherited through the cached runtime
	context; standalone sites use the packaged EduEdge mark. Tenants cannot
	override the product logo from EduEdge Settings.
	"""
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
		"tenant_subtitle": "School workspace",
		"companies": companies,
		"user": _get_user_identity(),
	}

	# Retain the legacy key while making the shared EdgeSuite contract
	# authoritative for identity, notifications, and context switching.
	bootinfo["eduedge_ui_identity"] = identity
	shared = bootinfo.get("edgesuite_ui_identity") or {}
	shared["eduedge"] = identity
	bootinfo["edgesuite_ui_identity"] = shared
