from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe import _
from frappe.utils import nowdate

from eduedge.api import admission_resource
from eduedge.api import resource_center as base
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches
from eduedge.services.institution_context import get_effective_institution_context

RESOURCE_FEATURES = {
	"school_branches": "school_branch",
	"admissions": "admission",
	"applicants": "admission",
	"students": "student_management",
	"programs": "academics",
	"program_offerings": "academics",
}

RESOURCE_TITLE_TERMS = {
	"programs": ("programme", True),
	"program_offerings": ("programme_offering", True),
}

FIELD_TERM_KEYS = {
	"program": "programme",
	"program_name": "programme",
	"academic_year": "academic_year",
	"academic_term": "academic_term",
	"course": "course",
	"student_group": "student_group",
	"class_level": "class_level",
	"instructor": "instructor",
	"room": "room",
}

SCHOOL_BRANCH_RESOURCE = "school_branches"


def _ensure_school_branch_editor_contract() -> None:
	"""Keep the EdgeSuite quick editor aligned with the Company → Institution → Branch model."""
	config = base.RESOURCE_CONFIG.get(SCHOOL_BRANCH_RESOURCE)
	if not config:
		return

	fields = config.setdefault("editor_fields", [])
	if not any(field.get("fieldname") == "institution" for field in fields):
		company_index = next(
			(index for index, field in enumerate(fields) if field.get("fieldname") == "company"),
			len(fields) - 1,
		)
		company_field = fields[company_index]
		company_field["clear_fields"] = sorted(set([*(company_field.get("clear_fields") or []), "institution"]))
		company_field["refresh_fields"] = sorted(set([*(company_field.get("refresh_fields") or []), "institution"]))
		fields.insert(
			company_index + 1,
			{
				"fieldname": "institution",
				"label": _("Institution"),
				"type": "Link",
				"options_doctype": "EduEdge Institution",
				"required": True,
				description": _("Academic institution that owns this Branch or Campus."),
			},
		)

	columns = config.setdefault("columns", [])
	if not any(column.get("fieldname") == "institution" for column in columns):
		company_index = next(
			(index for index, column in enumerate(columns) if column.get("fieldname") == "company"),
			len(columns) - 1,
		)
		columns.insert(company_index + 1, {"fieldname": "institution", "label": _("Institution")})

	search_fields = config.setdefault("search_fields", [])
	if "institution" not in search_fields:
		search_fields.append("institution")

	filters = config.setdefault("filters", [])
	if not any(field.get("fieldname") == "institution" for field in filters):
		filters.insert(
			1,
			{
				"fieldname": "institution",
				"label": _("Institution"),
				"type": "Link",
				"options_doctype": "EduEdge Institution",
			},
		)

	config["advanced_note"] = _(
		"Select Company first, then the Institution that owns this Branch. Accounting defaults and stock settings remain in the full School Branch form."
	)


_ensure_school_branch_editor_contract()


def _is_branch_scoped(config: dict) -> bool:
	return config.get("doctype") == "EduEdge School Branch" or bool(config.get("branch_field"))


def _feature_key(resource: str) -> str:
	return RESOURCE_FEATURES.get(str(resource or "").strip(), "foundation")


def _smart_filters(config: dict, allowed_branches: list[dict]) -> list[dict]:
	filters = deepcopy(base._filter_definitions(config, allowed_branches))
	for field in filters:
		if str(field.get("type") or "").lower() != "link":
			continue
		if field.get("fieldname") == "institution":
			field["options"] = _institution_options(company=None, txt="")
		else:
			field["options"] = base._link_options(field, "", {})
	return filters


def _empty_page(resource: str, config: dict, page_length: int | str = 20) -> dict:
	doctype = config["doctype"]
	columns = [
		column
		for column in config.get("columns", [])
		if column.get("fieldname") in base._available_fields(
			doctype,
			[column.get("fieldname")],
		)
	]
	result = {
		"resource": resource,
		"doctype": doctype,
		"title": config["title"],
		"eyebrow": config["eyebrow"],
		"subtitle": config["subtitle"],
		"icon": config["icon"],
		"route": config["route"],
		"full_form_route": config["full_form_route"],
		"title_field": config.get("title_field") or "name",
		"branch_field": config.get("branch_field") or "",
		"columns": columns,
		"rows": [],
		"filters": _smart_filters(config, []),
		"start": 0,
		"page_length": min(base.MAX_PAGE_LENGTH, max(5, int(page_length or 20))),
		"has_more": False,
		"advanced_note": config.get("advanced_note", ""),
		"permissions": {
			"can_create": bool(frappe.has_permission(doctype, "create")),
			"can_write": bool(frappe.has_permission(doctype, "write")),
			"can_delete": bool(frappe.has_permission(doctype, "delete")),
		},
	}
	return _apply_terminology(result, resource, get_effective_institution_context())


def _institution_options(*, company: str | None, txt: str = "") -> list[dict]:
	if not frappe.db.exists("DocType", "EduEdge Institution") or not frappe.has_permission(
		"EduEdge Institution", "read"
	):
		return []
	filters: dict[str, Any] = {"enabled": 1}
	if company:
		filters["company"] = company
	or_filters = None
	if str(txt or "").strip():
		needle = f"%{str(txt).strip()}%"
		or_filters = [["name", "like", needle], ["institution_name", "like", needle], ["institution_code", "like", needle]]
	rows = frappe.get_list(
		"EduEdge Institution",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "institution_name", "institution_code", "institution_type", "company"],
		order_by="is_default desc, institution_name asc",
		limit_page_length=base.MAX_OPTIONS,
	)
	return [
		{
			"value": row.name,
			"label": row.institution_name or row.name,
			"description": " · ".join(value for value in (row.institution_type, row.company) if value),
		}
		for row in rows
	]


def _context_from_payload(payload: dict | None = None) -> dict:
	values = payload or {}
	branch = values.get(BRANCH_FIELD) or values.get("school_branch") or values.get("branch")
	return get_effective_institution_context(
		company=values.get("company"),
		institution=values.get("institution"),
		branch=branch,
	)


def _term_label(context: dict, canonical_key: str, *, plural: bool = False) -> str:
	term = (context.get("terms") or {}).get(canonical_key) or {}
	return term.get("plural" if plural else "singular") or canonical_key.replace("_", " ").title()


def _apply_terminology(result: dict, resource: str, context: dict) -> dict:
	result["institution_context"] = context
	if resource in RESOURCE_TITLE_TERMS:
		key, plural = RESOURCE_TITLE_TERMS[resource]
		result["title"] = _term_label(context, key, plural=plural)

	for collection_name in ("columns", "filters", "fields"):
		for field in result.get(collection_name) or []:
			key = FIELD_TERM_KEYS.get(field.get("fieldname"))
			if key:
				field["label"] = _term_label(context, key)
	return result


@frappe.whitelist()
def get_resource_page(
	resource: str,
	search: str = "",
	filters: str | dict | None = None,
	start: int | str = 0,
	page_length: int | str = 20,
) -> dict:
	_ensure_school_branch_editor_contract()
	config = base._config(resource)
	allowed_branches = get_allowed_school_branches() if _is_branch_scoped(config) else []
	parsed_filters = base._parse_json(filters)
	if _is_branch_scoped(config) and not allowed_branches:
		return _empty_page(resource, config, page_length)
	result = base.get_resource_page(
		resource=resource,
		search=search,
		filters=filters,
		start=start,
		page_length=page_length,
	)
	result["full_form_route"] = config["full_form_route"]
	result["title_field"] = config.get("title_field") or "name"
	result["branch_field"] = config.get("branch_field") or ""
	result["filters"] = _smart_filters(config, allowed_branches)
	return _apply_terminology(result, resource, _context_from_payload(parsed_filters))


def _resolve_today(values: dict[str, Any]) -> dict[str, Any]:
	return {
		key: nowdate() if value == "Today" else value
		for key, value in values.items()
	}


def _enrich_school_branch_editor(result: dict) -> dict:
	values = result.get("values") or {}
	company = values.get("company")
	for field in result.get("fields") or []:
		if field.get("fieldname") == "institution":
			field["options"] = _institution_options(company=company, txt="")
			field["required"] = True
	return result


@frappe.whitelist()
def get_resource_editor(resource: str, name: str | None = None, context: str | dict | None = None) -> dict:
	_ensure_school_branch_editor_contract()
	result = base.get_resource_editor(resource=resource, name=name, context=context)
	result["values"] = _resolve_today(result.get("values") or {})
	if str(resource or "").strip() == "admissions":
		result = admission_resource.enrich_editor(result, name=name)
	if str(resource or "").strip() == SCHOOL_BRANCH_RESOURCE:
		result = _enrich_school_branch_editor(result)
	return _apply_terminology(result, str(resource or "").strip(), _context_from_payload(result.get("values")))


@frappe.whitelist()
def search_resource_options(
	resource: str,
	fieldname: str,
	txt: str = "",
	values: str | dict | None = None,
) -> list[dict]:
	_ensure_school_branch_editor_contract()
	parsed_values = base._parse_json(values)
	if str(resource or "").strip() == SCHOOL_BRANCH_RESOURCE and str(fieldname or "").strip() == "institution":
		return _institution_options(company=parsed_values.get("company"), txt=txt)
	if (
		str(resource or "").strip() == "admissions"
		and str(fieldname or "").strip() == admission_resource.PROGRAMS_FIELD
	):
		return admission_resource.search_program_options(values=values, txt=txt)
	return base.search_resource_options(
		resource=resource,
		fieldname=fieldname,
		txt=txt,
		values=parsed_values,
	)


@frappe.whitelist()
def save_resource_record(resource: str, values: str | dict, name: str | None = None) -> dict:
	_ensure_school_branch_editor_contract()
	require_eduedge_access(
		feature_key=_feature_key(resource),
		action="update_resource_record" if name else "create_resource_record",
		reference_doctype=(base._config(resource) or {}).get("doctype"),
		reference_name=name,
	)
	parsed = _resolve_today(base._parse_json(values))
	if str(resource or "").strip() == "admissions":
		return admission_resource.save_admission(values=parsed, name=name)
	return base.save_resource_record(
		resource=resource,
		values=parsed,
		name=name,
	)


@frappe.whitelist()
def delete_resource_record(resource: str, name: str) -> dict:
	require_eduedge_access(
		feature_key=_feature_key(resource),
		action="delete_resource_record",
		reference_doctype=(base._config(resource) or {}).get("doctype"),
		reference_name=name,
	)
	return base.delete_resource_record(resource=resource, name=name)
