from __future__ import annotations

import frappe

from eduedge.access_control import build_access_manifest
from eduedge.platform.runtime_context import get_product_identity
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)
from eduedge.services.institution_branding import get_institution_branding
from eduedge.services.institution_context import get_effective_institution_context


FEATURE_FIELDS = {
	"cbt": ("enable_cbt", True),
	"student_pickup": ("enable_student_pickup", False),
	"school_intelligence": ("enable_school_intelligence", True),
	"edgefinder_publication": ("enable_edgefinder_publication", False),
}


def _get_feature_flags() -> dict[str, bool]:
	flags = {key: default for key, (_fieldname, default) in FEATURE_FIELDS.items()}
	try:
		if not frappe.db.exists("DocType", "EduEdge Settings"):
			return flags
		for key, (fieldname, default) in FEATURE_FIELDS.items():
			value = frappe.db.get_single_value("EduEdge Settings", fieldname)
			flags[key] = bool(default if value is None else frappe.utils.cint(value))
	except Exception:
		return flags
	return flags


def _get_eduedge_page_routes() -> list[str]:
	try:
		page_names = frappe.get_all(
			"Page",
			filters={"name": ["like", "eduedge-%"]},
			pluck="name",
			page_length=0,
		)
	except Exception:
		page_names = []
	return sorted({f"/app/{name}" for name in page_names if name})


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


def _get_institution_identity(institution: str) -> dict:
	if not institution or not frappe.db.exists("EduEdge Institution", institution):
		return {"name": institution or "", "label": institution or "", "logo": ""}
	row = frappe.db.get_value(
		"EduEdge Institution",
		institution,
		["name", "institution_name", "logo", "company", "institution_type"],
		as_dict=True,
	) or {}
	return {
		"name": row.get("name") or institution,
		"label": row.get("institution_name") or row.get("name") or institution,
		"logo": row.get("logo") or "",
		"company": row.get("company") or "",
		"institution_type": row.get("institution_type") or "",
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


def _attach_institution_branding(context: dict) -> dict:
	payload = dict(context or {})
	branding = get_institution_branding(
		payload.get("institution") or None,
		branch=payload.get("branch") or None,
	)
	payload["branding"] = branding
	for fieldname in (
		"logo",
		"motto",
		"phone",
		"whatsapp_number",
		"email",
		"website",
		"formatted_address",
		"report_footer",
	):
		payload[fieldname] = branding.get(fieldname) or ""
	return payload


def extend_bootinfo(bootinfo) -> None:
	"""Expose permission-safe identity, access, features, and terminology for EdgeSuite UI."""
	if frappe.session.user == "Guest":
		return

	allowed_branches = []
	current_branch = None
	try:
		allowed_branches = get_allowed_school_branches()
		current_branch = get_current_school_branch()
	except Exception:
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
	active_company_identity = companies.get(active_company) or {
		"name": active_company or "",
		"label": active_company or "",
		"logo": "",
	}
	product_identity = get_product_identity()
	features = _get_feature_flags()
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
			"institution": "",
			"institution_name": "",
			"branch": (current_branch or {}).get("name") or "",
			"branch_name": (current_branch or {}).get("branch_name") or "",
			"terms": {},
			"uses_secondary_fallback": 1,
		}
	try:
		institution_context = _attach_institution_branding(institution_context)
	except Exception:
		institution_context = dict(institution_context or {})
		institution_context.setdefault("branding", {})
		institution_context.setdefault("logo", "")

	active_institution_identity = _get_institution_identity(institution_context.get("institution"))
	institution_label = (
		active_institution_identity.get("label")
		or institution_context.get("institution_name")
		or active_company_identity.get("label")
		or active_company_identity.get("name")
		or ""
	)
	institution_logo = (
		institution_context.get("logo")
		or active_institution_identity.get("logo")
		or active_company_identity.get("logo")
		or ""
	)

	identity = {
		"product_code": product_identity["product_code"],
		"product_name": product_identity["product_name"],
		"product_logo": product_identity["product_logo"],
		"product_identity_source": product_identity["source"],
		"product_icon": "graduation",
		"product_subtitle": "Education Management",
		"tenant_name": institution_label,
		"tenant_logo": institution_logo,
		"tenant_icon": "building",
		"tenant_subtitle": institution_context.get("institution_type_name") or "Education workspace",
		"owner_company_name": active_company_identity.get("label") or active_company_identity.get("name") or "",
		"branch_name": institution_context.get("branch_name") or "",
		"companies": companies,
		"user": _get_user_identity(),
		"institution_context": institution_context,
		"features": features,
		"contact_identity": {
			"phone": institution_context.get("phone") or "",
			"whatsapp_number": institution_context.get("whatsapp_number") or "",
			"email": institution_context.get("email") or "",
			"website": institution_context.get("website") or "",
			"formatted_address": institution_context.get("formatted_address") or "",
		},
	}

	bootinfo["eduedge_institution_context"] = institution_context
	bootinfo["eduedge_features"] = features
	bootinfo["eduedge_page_routes"] = _get_eduedge_page_routes()
	bootinfo["eduedge_ui_identity"] = identity
	shared = bootinfo.get("edgesuite_ui_identity") or {}
	shared["eduedge"] = identity
	bootinfo["edgesuite_ui_identity"] = shared

	try:
		bootinfo["eduedge_access_manifest"] = build_access_manifest(frappe.session.user)
	except Exception:
		bootinfo["eduedge_access_manifest"] = {
			"resources": {},
			"routes": {},
			"can_access_eduedge": False,
		}
