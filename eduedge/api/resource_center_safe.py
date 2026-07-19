from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe.utils import nowdate

from eduedge.api import resource_center as base
from eduedge.services.branch_context import get_allowed_school_branches


def _is_branch_scoped(config: dict) -> bool:
	return config.get("doctype") == "EduEdge School Branch" or bool(config.get("branch_field"))


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
	return result


@frappe.whitelist()
def save_resource_record(resource: str, values: str | dict, name: str | None = None) -> dict:
	parsed = base._parse_json(values)
	return base.save_resource_record(
		resource=resource,
		values=_resolve_today(parsed),
		name=name,
	)
