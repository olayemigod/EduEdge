from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe.utils import nowdate

from eduedge.api import admission_resource
from eduedge.api import resource_center as base
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches

RESOURCE_FEATURES = {
	"school_branches": "school_branch",
	"admissions": "admission",
	"applicants": "admission",
	"students": "student_management",
	"programs": "academics",
	"program_offerings": "academics",
}


def _is_branch_scoped(config: dict) -> bool:
	return config.get("doctype") == "EduEdge School Branch" or bool(config.get("branch_field"))


def _feature_key(resource: str) -> str:
	return RESOURCE_FEATURES.get(str(resource or "").strip(), "foundation")


def _smart_filters(config: dict, allowed_branches: list[dict]) -> list[dict]:
	filters = deepcopy(base._filter_definitions(config, allowed_branches))
	for field in filters:
		if str(field.get("type") or "").lower() != "link":
			continue
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
	return {
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


@frappe.whitelist()
def get_resource_page(
	resource: str,
	search: str = "",
	filters: str | dict | None = None,
	start: int | str = 0,
	page_length: int | str = 20,
) -> dict:
	config = base._config(resource)
	allowed_branches = get_allowed_school_branches() if _is_branch_scoped(config) else []
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
	return result


def _resolve_today(values: dict[str, Any]) -> dict[str, Any]:
	return {
		key: nowdate() if value == "Today" else value
		for key, value in values.items()
	}


@frappe.whitelist()
def get_resource_editor(resource: str, name: str | None = None, context: str | dict | None = None) -> dict:
	result = base.get_resource_editor(resource=resource, name=name, context=context)
	result["values"] = _resolve_today(result.get("values") or {})
	if str(resource or "").strip() == "admissions":
		result = admission_resource.enrich_editor(result, name=name)
	return result


@frappe.whitelist()
def search_resource_options(
	resource: str,
	fieldname: str,
	txt: str = "",
	values: str | dict | None = None,
) -> list[dict]:
	if (
		str(resource or "").strip() == "admissions"
		and str(fieldname or "").strip() == admission_resource.PROGRAMS_FIELD
	):
		return admission_resource.search_program_options(values=values, txt=txt)
	return base.search_resource_options(
		resource=resource,
		fieldname=fieldname,
		txt=txt,
		values=values,
	)


@frappe.whitelist()
def save_resource_record(resource: str, values: str | dict, name: str | None = None) -> dict:
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
