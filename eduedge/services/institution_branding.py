from __future__ import annotations

from typing import Any

import frappe


INSTITUTION_BRANDING_FIELDS = (
	"name",
	"institution_name",
	"official_name",
	"short_name",
	"company",
	"institution_type",
	"logo",
	"motto",
	"address",
	"phone",
	"whatsapp_number",
	"email",
	"website",
	"report_card_letter_head",
	"report_footer",
)


def get_institution_branding(
	institution: str | None,
	*,
	branch: str | None = None,
) -> dict[str, Any]:
	"""Resolve Institution identity with Branch contact/address overrides.

	This service performs no permission elevation. Callers must validate access to the
	Institution or Branch before exposing the returned payload.
	"""
	institution_row = _get_institution(institution)
	branch_row = _get_branch(branch)

	address_name = (branch_row or {}).get("address") or (institution_row or {}).get("address")
	address = _get_address(address_name)
	company = _get_company((institution_row or {}).get("company") or (branch_row or {}).get("company"))

	institution_name = (
		(institution_row or {}).get("institution_name")
		or (institution_row or {}).get("official_name")
		or (company or {}).get("company_name")
		or (branch_row or {}).get("branch_name")
		or ""
	)
	official_name = (
		(institution_row or {}).get("official_name")
		or institution_name
	)
	logo = (institution_row or {}).get("logo") or (company or {}).get("company_logo") or ""
	phone = (branch_row or {}).get("phone") or (institution_row or {}).get("phone") or ""
	email = (branch_row or {}).get("email") or (institution_row or {}).get("email") or ""

	return {
		"institution": (institution_row or {}).get("name") or "",
		"institution_name": institution_name,
		"official_name": official_name,
		"short_name": (institution_row or {}).get("short_name") or "",
		"company": (institution_row or {}).get("company") or (branch_row or {}).get("company") or "",
		"institution_type": (institution_row or {}).get("institution_type") or "",
		"logo": logo,
		"motto": (institution_row or {}).get("motto") or "",
		"phone": phone,
		"whatsapp_number": (institution_row or {}).get("whatsapp_number") or "",
		"email": email,
		"website": (institution_row or {}).get("website") or "",
		"report_card_letter_head": (institution_row or {}).get("report_card_letter_head") or "",
		"report_footer": (institution_row or {}).get("report_footer") or "",
		"branch": (branch_row or {}).get("name") or "",
		"branch_name": (branch_row or {}).get("branch_name") or "",
		"branch_code": (branch_row or {}).get("branch_code") or "",
		"address_name": address_name or "",
		"address": dict(address or {}),
		"formatted_address": format_address(address),
	}


def get_active_communication_identity(
	*,
	institution: str | None = None,
	branch: str | None = None,
) -> dict[str, Any]:
	"""Return the approved sender identity for reports and communication services."""
	payload = get_institution_branding(institution, branch=branch)
	return {
		"name": payload["institution_name"],
		"official_name": payload["official_name"],
		"short_name": payload["short_name"],
		"logo": payload["logo"],
		"motto": payload["motto"],
		"phone": payload["phone"],
		"whatsapp_number": payload["whatsapp_number"],
		"email": payload["email"],
		"website": payload["website"],
		"address": payload["address"],
		"formatted_address": payload["formatted_address"],
		"report_footer": payload["report_footer"],
		"institution": payload["institution"],
		"branch": payload["branch"],
	}


def format_address(address: dict | frappe._dict | None) -> str:
	if not address:
		return ""
	parts = [
		address.get("address_line1"),
		address.get("address_line2"),
		address.get("city"),
		address.get("state"),
		address.get("pincode"),
		address.get("country"),
	]
	return ", ".join(str(value).strip() for value in parts if str(value or "").strip())


def _get_institution(name: str | None) -> frappe._dict | None:
	if not name or not frappe.db.exists("EduEdge Institution", name):
		return None
	meta = frappe.get_meta("EduEdge Institution")
	fields = [field for field in INSTITUTION_BRANDING_FIELDS if field == "name" or meta.has_field(field)]
	return frappe.db.get_value("EduEdge Institution", name, fields, as_dict=True)


def _get_branch(name: str | None) -> frappe._dict | None:
	if not name or not frappe.db.exists("EduEdge School Branch", name):
		return None
	fields = ["name", "branch_name", "branch_code", "company", "institution", "address", "phone", "email"]
	return frappe.db.get_value("EduEdge School Branch", name, fields, as_dict=True)


def _get_company(name: str | None) -> frappe._dict | None:
	if not name or not frappe.db.exists("Company", name):
		return None
	fields = ["name", "company_name"]
	if frappe.get_meta("Company").has_field("company_logo"):
		fields.append("company_logo")
	return frappe.db.get_value("Company", name, fields, as_dict=True)


def _get_address(name: str | None) -> frappe._dict | None:
	if not name or not frappe.db.exists("Address", name):
		return None
	return frappe.db.get_value(
		"Address",
		name,
		[
			"name",
			"address_title",
			"address_type",
			"address_line1",
			"address_line2",
			"city",
			"county",
			"state",
			"country",
			"pincode",
			"phone",
			"email_id",
		],
		as_dict=True,
	)
