from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint
from frappe.utils.nestedset import get_root_of

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


def _native_department_root() -> str | None:
	"""Return ERPNext's native Department tree root.

	ERPNext v16 creates one global ``All Departments`` root without a Company and
	places Company Departments below it. Older/custom sites can still contain a
	Company-specific top-level group, so callers retain a compatibility path before
	falling back to this native global root.
	"""
	if not frappe.db.exists("DocType", "Department"):
		return None
	try:
		root = get_root_of("Department")
	except Exception:
		root = None
	if root:
		return str(root)
	return frappe.db.get_value(
		"Department",
		{"parent_department": ["is", "not set"]},
		"name",
		order_by="lft asc, creation asc",
	)


def get_company_department_roots(company: str) -> list[str]:
	"""Return the native root(s) beneath which this Company's academic tree may sit.

	Historically EduEdge assumed ERPNext created a top-level Department per Company.
	ERPNext v16 instead uses a global ``All Departments`` root and Company-specific
	children. Preserve any older Company-specific group root when present; otherwise
	use the native global Department root.
	"""
	if not company:
		return []
	fields = ["name", "lft"]
	if frappe.get_meta("Department").has_field(INSTITUTION_ROOT_FLAG):
		fields.append(INSTITUTION_ROOT_FLAG)
	legacy_rows = frappe.get_all(
		"Department",
		filters={
			"company": company,
			"is_group": 1,
			"parent_department": ["is", "not set"],
		},
		fields=fields,
		order_by="lft asc, creation asc",
		limit_page_length=0,
	)
	legacy_roots = [
		row.name
		for row in legacy_rows
		if not cint(row.get(INSTITUTION_ROOT_FLAG))
	]
	if legacy_roots:
		return legacy_roots
	native_root = _native_department_root()
	return [native_root] if native_root else []


def get_company_department_root(company: str) -> str:
	roots = get_company_department_roots(company)
	if not roots:
		frappe.throw(
			_("Create the ERPNext Department tree before configuring the Institution academic hierarchy."),
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
	root_company = frappe.db.get_value("Department", company_root, "company")
	department_name = _available_root_name(
		institution_row.institution_name or institution,
		institution_row.institution_code or institution,
		institution_row.company,
	)
	doc = frappe.new_doc("Department")
	doc.department_name = department_name
	doc.company = institution_row.company
	# ERPNext v16's native root has no Company. Leaving the parent blank on initial
	# insert lets Department.validate_parent_department() attach this Company-owned
	# group to the native global root without triggering its same-Company parent gate.
	# Older sites with a genuine Company-owned top-level group keep that root directly.
	doc.parent_department = company_root if root_company == institution_row.company else None
	doc.is_group = 1
	doc.set(INSTITUTION_FIELD, None)
	doc.set(INSTITUTION_ROOT_FLAG, 1)
	doc.set(INSTITUTION_ROOT_OWNER, institution)
	doc.flags.eduedge_managed_institution_root = True
	doc.insert(ignore_permissions=ignore_permissions)
	if doc.parent_department != company_root:
		frappe.throw(
			_("ERPNext did not attach the Institution academic root beneath the expected Department root."),
			frappe.ValidationError,
		)
	return doc.name


def _department_is_ancestor_of(ancestor: str, descendant: str) -> bool:
	"""Return True when moving ``ancestor`` below ``descendant`` would form a cycle.

	Use the stored parent chain instead of lft/rgt values because this helper runs
	during migration and may encounter a partially-normalised nested set.
	"""
	ancestor = str(ancestor or "").strip()
	current = str(descendant or "").strip()
	if not ancestor or not current:
		return False
	if ancestor == current:
		return True

	visited: set[str] = set()
	while current and current not in visited:
		visited.add(current)
		parent = frappe.db.get_value("Department", current, "parent_department")
		if not parent:
			return False
		if parent == ancestor:
			return True
		current = str(parent)
	return False


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

			# The native ERPNext root is a technical container shared by every Company
			# and Institution. Earlier foundation data could leave an Institution value
			# on a root. Clear stale ownership without nested-set movement.
			if row.name in company_roots:
				frappe.db.set_value(
					"Department",
					row.name,
					INSTITUTION_FIELD,
					None,
					update_modified=False,
				)
				continue

			if row.parent_department and row.parent_department not in company_roots:
				continue

			# A partially-normalised site can already have the managed Institution
			# root below this row. Moving the row beneath that target would create a
			# nested-set cycle. Leave such ancestors untouched for a safe, idempotent
			# migration rather than forcing an invalid move.
			if _department_is_ancestor_of(row.name, institution_root):
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
