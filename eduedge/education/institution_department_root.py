from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD


INSTITUTION_ROOT_FLAG = "eduedge_is_institution_root"
INSTITUTION_ROOT_OWNER = "eduedge_root_institution"


def ensure_institution_department_root_fields() -> None:
	if not frappe.db.exists("DocType", "Department"):
		return
	create_custom_fields(
		{
			"Department": [
				{
					"fieldname": INSTITUTION_ROOT_FLAG,
					"fieldtype": "Check",
					"label": "EduEdge Institution Academic Root",
					"default": "0",
					"hidden": 1,
					"read_only": 1,
					"insert_after": INSTITUTION_FIELD,
					"description": "System-managed container for one Institution's academic Department hierarchy.",
				},
				{
					"fieldname": INSTITUTION_ROOT_OWNER,
					"fieldtype": "Link",
					"label": "EduEdge Root Institution",
					"options": "EduEdge Institution",
					"hidden": 1,
					"read_only": 1,
					"insert_after": INSTITUTION_ROOT_FLAG,
					"description": "Institution represented by this system-managed academic root.",
				},
			],
		},
		update=True,
	)


def is_managed_institution_root(doc) -> bool:
	return bool(
		doc.meta.has_field(INSTITUTION_ROOT_FLAG)
		and cint(doc.get(INSTITUTION_ROOT_FLAG))
	)


def get_company_department_roots(company: str) -> list[str]:
	if not company:
		return []
	fields = ["name", "lft"]
	if frappe.get_meta("Department").has_field(INSTITUTION_ROOT_FLAG):
		fields.append(INSTITUTION_ROOT_FLAG)
	rows = frappe.get_all(
		"Department",
		filters={"company": company, "parent_department": ["is", "not set"]},
		fields=fields,
		order_by="lft asc, creation asc",
		limit_page_length=0,
	)
	return [
		row.name
		for row in rows
		if not cint(row.get(INSTITUTION_ROOT_FLAG))
	]


def get_company_department_root(company: str) -> str:
	roots = get_company_department_roots(company)
	if not roots:
		frappe.throw(
			_("Create the ERPNext root Department for Company {0} before configuring the Institution academic hierarchy.").format(company),
			frappe.ValidationError,
		)
	return roots[0]


def ensure_institution_department_root(
	institution: str,
	*,
	ignore_permissions: bool = False,
) -> str:
	ensure_institution_department_root_fields()
	institution_row = frappe.db.get_value(
		"EduEdge Institution",
		institution,
		["name", "institution_name", "institution_code", "company"],
		as_dict=True,
	)
	if not institution_row or not institution_row.company:
		frappe.throw(_("Select an Institution with a valid Company."), frappe.ValidationError)

	existing = frappe.db.get_value(
		"Department",
		{
			INSTITUTION_ROOT_FLAG: 1,
			INSTITUTION_ROOT_OWNER: institution,
		},
		"name",
	)
	if existing:
		return existing

	company_root = get_company_department_root(institution_row.company)
	department_name = _available_root_name(
		institution_row.institution_name or institution,
		institution_row.institution_code or institution,
		institution_row.company,
	)
	doc = frappe.new_doc("Department")
	doc.department_name = department_name
	doc.company = institution_row.company
	doc.parent_department = company_root
	doc.is_group = 1
	doc.set(INSTITUTION_FIELD, None)
	doc.set(INSTITUTION_ROOT_FLAG, 1)
	doc.set(INSTITUTION_ROOT_OWNER, institution)
	doc.flags.eduedge_managed_institution_root = True
	doc.insert(ignore_permissions=ignore_permissions)
	return doc.name


def normalise_institution_department_roots(*, ignore_permissions: bool = True) -> None:
	if not (
		frappe.db.exists("DocType", "Department")
		and frappe.db.exists("DocType", "EduEdge Institution")
	):
		return
	ensure_institution_department_root_fields()
	institutions = frappe.get_all(
		"EduEdge Institution",
		filters={"company": ["is", "set"]},
		fields=["name", "company"],
		order_by="creation asc",
		limit_page_length=0,
	)
	for institution in institutions:
		company_roots = set(get_company_department_roots(institution.company))
		if not company_roots:
			continue
		institution_root = ensure_institution_department_root(
			institution.name,
			ignore_permissions=ignore_permissions,
		)
		rows = frappe.get_all(
			"Department",
			filters={INSTITUTION_FIELD: institution.name},
			fields=["name", "parent_department", INSTITUTION_ROOT_FLAG],
			order_by="lft asc, creation asc",
			limit_page_length=0,
		)
		for row in rows:
			if cint(row.get(INSTITUTION_ROOT_FLAG)):
				continue
			if row.parent_department and row.parent_department not in company_roots:
				continue
			doc = frappe.get_doc("Department", row.name)
			doc.parent_department = institution_root
			doc.flags.eduedge_root_normalisation = True
			doc.save(ignore_permissions=ignore_permissions)
	frappe.clear_cache(doctype="Department")


def _available_root_name(institution_name: str, institution_code: str, company: str) -> str:
	base = f"{str(institution_name or '').strip()} Academic Structure".strip()
	code = re.sub(r"[^A-Za-z0-9]+", "-", str(institution_code or "").strip()).strip("-") or "Institution"
	candidate = base
	counter = 1
	while frappe.db.exists("Department", {"department_name": candidate, "company": company}):
		suffix = f" ({code})" if counter == 1 else f" ({code}-{counter})"
		candidate = f"{base}{suffix}"
		counter += 1
	return candidate
