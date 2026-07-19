from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.services.branch_context import get_allowed_school_branches

MAX_OPTIONS = 30

BRANCH_TYPES = [
	"Main Campus",
	"Campus",
	"Annex Campus",
	"Nursery",
	"Primary",
	"Secondary",
	"Boarding Campus",
	"Tutorial Centre",
	"CBT Centre",
	"Administrative Office",
	"Learning Centre",
	"Other",
]
BRANCH_ROLES = [
	"School Administrator",
	"Academic Administrator",
	"Bursar",
	"Teacher",
	"CBT Invigilator",
	"Student Safety Officer",
	"Transport Coordinator",
	"Admissions Officer",
	"Other",
]

RESOURCE_CONFIG: dict[str, dict[str, Any]] = {
	"school_branch": {
		"doctype": "EduEdge School Branch",
		"title": _("School Branch / Campus"),
		"create_title": _("Add School Branch / Campus"),
		"edit_title": _("Update School Branch / Campus"),
		"subtitle": _("Capture the branch identity and contact details. Accounting defaults remain available in the full form."),
		"full_form_route": "/app/eduedge-school-branch",
		"fields": [
			{"fieldname": "branch_name", "type": "Data", "label": _("Branch Name"), "required": True},
			{"fieldname": "branch_code", "type": "Data", "label": _("Branch Code"), "required": True, "description": _("Short unique code, for example MAIN or LEKKI.")},
			{"fieldname": "branch_type", "type": "Select", "label": _("Branch Type"), "options": BRANCH_TYPES, "default": "Campus"},
			{"fieldname": "company", "type": "Link", "label": _("School / Company"), "options_doctype": "Company", "required": True},
			{"fieldname": "is_main_branch", "type": "Check", "label": _("Main Branch / Campus"), "default": 0},
			{"fieldname": "is_default", "type": "Check", "label": _("Default Operational Branch"), "default": 0},
			{"fieldname": "enabled", "type": "Check", "label": _("Enabled"), "default": 1},
			{"fieldname": "contact_person", "type": "Data", "label": _("Contact Person")},
			{"fieldname": "phone", "type": "Phone", "label": _("Phone")},
			{"fieldname": "email", "type": "Email", "label": _("Email")},
			{"fieldname": "academic_levels_offered", "type": "Small Text", "label": _("Academic Levels Offered"), "description": _("Examples: Nursery, Primary, Junior Secondary, Senior Secondary, CBT Centre.")},
		],
	},
	"program_offering": {
		"doctype": "EduEdge Program Offering",
		"title": _("Programme Offering"),
		"create_title": _("Add Programme Offering"),
		"edit_title": _("Update Programme Offering"),
		"subtitle": _("Make a programme available for a branch and academic session."),
		"full_form_route": "/app/eduedge-program-offering",
		"fields": [
			{"fieldname": "school_branch", "type": "Link", "label": _("School Branch / Campus"), "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "program", "type": "Link", "label": _("Program"), "options_doctype": "Program", "required": True},
			{"fieldname": "academic_year", "type": "Link", "label": _("Academic Year"), "options_doctype": "Academic Year", "required": True, "clear_fields": ["academic_term"]},
			{"fieldname": "academic_term", "type": "Link", "label": _("Academic Term"), "options_doctype": "Academic Term"},
			{"fieldname": "is_active", "type": "Check", "label": _("Active"), "default": 1},
			{"fieldname": "admission_enabled", "type": "Check", "label": _("Available for Admission"), "default": 1},
			{"fieldname": "enrollment_enabled", "type": "Check", "label": _("Available for Enrollment"), "default": 1},
			{"fieldname": "capacity", "type": "Int", "label": _("Capacity"), "default": 0, "min": 0, "description": _("Zero means that no capacity limit is defined.")},
			{"fieldname": "application_start_date", "type": "Date", "label": _("Application Start Date")},
			{"fieldname": "application_end_date", "type": "Date", "label": _("Application End Date")},
			{"fieldname": "notes", "type": "Small Text", "label": _("Notes")},
		],
	},
	"user_branch_access": {
		"doctype": "EduEdge User Branch Access",
		"title": _("User Branch Access"),
		"create_title": _("Add User Branch Access"),
		"edit_title": _("Update User Branch Access"),
		"subtitle": _("Assign a system user to one campus or grant company-scoped HQ access."),
		"full_form_route": "/app/eduedge-user-branch-access",
		"fields": [
			{"fieldname": "user", "type": "Link", "label": _("User"), "options_doctype": "User", "required": True},
			{"fieldname": "branch_role", "type": "Select", "label": _("Role in Branch"), "options": BRANCH_ROLES, "required": True},
			{"fieldname": "hq_all_branch_access", "type": "Check", "label": _("HQ / All-Branch Access"), "default": 0, "clear_fields": ["school_branch", "is_default_branch"]},
			{"fieldname": "company", "type": "Link", "label": _("Company"), "options_doctype": "Company", "required": True, "clear_fields": ["school_branch"]},
			{"fieldname": "school_branch", "type": "Link", "label": _("School Branch / Campus"), "options_doctype": "EduEdge School Branch", "required_when": {"field": "hq_all_branch_access", "equals": 0}, "visible_when": {"field": "hq_all_branch_access", "equals": 0}},
			{"fieldname": "is_default_branch", "type": "Check", "label": _("Default Branch"), "default": 0, "visible_when": {"field": "hq_all_branch_access", "equals": 0}},
			{"fieldname": "can_switch_branch", "type": "Check", "label": _("Can Switch Branch"), "default": 1},
			{"fieldname": "enabled", "type": "Check", "label": _("Enabled"), "default": 1},
			{"fieldname": "valid_from", "type": "Date", "label": _("Valid From")},
			{"fieldname": "valid_to", "type": "Date", "label": _("Valid To")},
		],
	},
	"instructor_branch_assignment": {
		"doctype": "EduEdge Instructor Branch Assignment",
		"title": _("Instructor Branch Assignment"),
		"create_title": _("Assign Instructor to Branch"),
		"edit_title": _("Update Instructor Branch Assignment"),
		"subtitle": _("Connect an instructor to an enabled campus without changing the Instructor master."),
		"full_form_route": "/app/eduedge-instructor-branch-assignment",
		"fields": [
			{"fieldname": "instructor", "type": "Link", "label": _("Instructor"), "options_doctype": "Instructor", "required": True},
			{"fieldname": "school_branch", "type": "Link", "label": _("School Branch / Campus"), "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "enabled", "type": "Check", "label": _("Enabled"), "default": 1},
			{"fieldname": "is_primary", "type": "Check", "label": _("Primary Branch"), "default": 0},
			{"fieldname": "valid_from", "type": "Date", "label": _("Valid From")},
			{"fieldname": "valid_to", "type": "Date", "label": _("Valid To")},
		],
	},
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _parse_json(value: Any) -> dict:
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Expected a JSON object."), frappe.ValidationError)
	return parsed


def _resource(resource: str) -> dict[str, Any]:
	config = RESOURCE_CONFIG.get(str(resource or "").strip())
	if not config:
		frappe.throw(_("This record type is not available in the EduEdge quick editor."), frappe.PermissionError)
	if not frappe.db.exists("DocType", config["doctype"]):
		frappe.throw(_("{0} is not installed on this site.").format(config["doctype"]))
	return config


def _field_map(config: dict) -> dict[str, dict]:
	return {field["fieldname"]: field for field in config["fields"]}


def _defaults(config: dict) -> dict:
	return {
		field["fieldname"]: field.get("default", "")
		for field in config["fields"]
		if "default" in field
	}


def _record_values(doc, config: dict) -> dict:
	return {fieldname: doc.get(fieldname) for fieldname in _field_map(config)}


def _record_label(doc, config: dict) -> str:
	for fieldname in ("branch_name", "program", "user_full_name", "user", "instructor_name", "instructor", "name"):
		value = doc.get(fieldname)
		if value:
			return str(value)
	return str(doc.name)


def _full_form_route(config: dict, name: str | None = None) -> str:
	base = config["full_form_route"].rstrip("/")
	return f"{base}/{name}" if name else base


def _initial_link_options(config: dict, values: dict, context: dict) -> list[dict]:
	fields = deepcopy(config["fields"])
	for field in fields:
		if str(field.get("type", "")).lower() != "link":
			continue
		field["options"] = _search_options(config, field, "", values, context)
	return fields


@frappe.whitelist()
def get_modal_schema(resource: str, name: str | None = None, context: str | dict | None = None) -> dict:
	_require_login()
	config = _resource(resource)
	doctype = config["doctype"]
	parsed_context = _parse_json(context)
	values = _defaults(config)

	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("read")
		values.update(_record_values(doc, config))
		can_save = doc.has_permission("write")
	else:
		if not frappe.has_permission(doctype, "create"):
			frappe.throw(_("You are not permitted to create {0}.").format(doctype), frappe.PermissionError)
		can_save = True
		values.update({key: value for key, value in parsed_context.items() if key in _field_map(config)})

	return {
		"resource": resource,
		"doctype": doctype,
		"name": name,
		"title": config["edit_title"] if name else config["create_title"],
		"subtitle": config["subtitle"],
		"submit_label": _("Save Changes") if name else _("Create"),
		"fields": _initial_link_options(config, values, parsed_context),
		"values": values,
		"can_save": can_save,
		"full_form_route": _full_form_route(config, name),
	}


@frappe.whitelist()
def search_modal_options(
	resource: str,
	fieldname: str,
	txt: str = "",
	values: str | dict | None = None,
	context: str | dict | None = None,
) -> list[dict]:
	_require_login()
	config = _resource(resource)
	field = _field_map(config).get(fieldname)
	if not field or str(field.get("type", "")).lower() != "link":
		frappe.throw(_("This field does not support option search."), frappe.ValidationError)
	return _search_options(config, field, txt, _parse_json(values), _parse_json(context))


def _search_options(config: dict, field: dict, txt: str, values: dict, context: dict) -> list[dict]:
	fieldname = field["fieldname"]
	query = str(txt or "").strip()
	company = values.get("company") or context.get("company")

	if fieldname == "school_branch":
		rows = get_allowed_school_branches(company=company)
		if query:
			needle = query.lower()
			rows = [row for row in rows if needle in str(row.get("name") or "").lower() or needle in str(row.get("branch_name") or "").lower()]
		return [
			{"value": row.get("name"), "label": row.get("branch_name") or row.get("name"), "description": row.get("company") or ""}
			for row in rows[:MAX_OPTIONS]
		]

	if fieldname == "company":
		return _link_rows("Company", query, ["name", "company_name"], filters={"is_group": 0}, label_field="company_name")
	if fieldname == "user":
		return _link_rows(
			"User",
			query,
			["name", "full_name"],
			filters={"enabled": 1, "user_type": "System User"},
			label_field="full_name",
		)
	if fieldname == "program":
		return _link_rows("Program", query, ["name", "program_name"], label_field="program_name")
	if fieldname == "academic_year":
		return _link_rows("Academic Year", query, ["name"], order_by="year_start_date desc, name desc")
	if fieldname == "academic_term":
		filters = {"academic_year": values.get("academic_year")} if values.get("academic_year") else {}
		return _link_rows("Academic Term", query, ["name", "term_name"], filters=filters, label_field="term_name")
	if fieldname == "instructor":
		return _link_rows("Instructor", query, ["name", "instructor_name"], label_field="instructor_name")

	return _link_rows(field.get("options_doctype") or "", query, ["name"])


def _link_rows(
	doctype: str,
	query: str,
	candidate_fields: list[str],
	*,
	filters: dict | None = None,
	label_field: str | None = None,
	order_by: str = "modified desc",
) -> list[dict]:
	if not doctype or not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	meta = frappe.get_meta(doctype)
	fields = [fieldname for fieldname in candidate_fields if fieldname == "name" or meta.has_field(fieldname)]
	if "name" not in fields:
		fields.insert(0, "name")
	or_filters = []
	if query:
		or_filters = [[fieldname, "like", f"%{query}%"] for fieldname in fields]
	rows = frappe.get_list(
		doctype,
		filters=filters or {},
		or_filters=or_filters or None,
		fields=fields,
		order_by=order_by,
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{
			"value": row.get("name"),
			"label": row.get(label_field) or row.get("name") if label_field else row.get("name"),
			"description": row.get("name") if label_field and row.get(label_field) and row.get(label_field) != row.get("name") else "",
		}
		for row in rows
	]


@frappe.whitelist()
def save_modal_record(
	resource: str,
	values: str | dict,
	name: str | None = None,
	context: str | dict | None = None,
) -> dict:
	_require_login()
	config = _resource(resource)
	doctype = config["doctype"]
	payload = _parse_json(values)
	parsed_context = _parse_json(context)
	allowed_fields = _field_map(config)
	clean_values = {
		fieldname: _coerce_value(allowed_fields[fieldname], value)
		for fieldname, value in payload.items()
		if fieldname in allowed_fields
	}
	for key, value in parsed_context.items():
		if key in allowed_fields and key not in clean_values:
			clean_values[key] = _coerce_value(allowed_fields[key], value)

	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("write")
	else:
		if not frappe.has_permission(doctype, "create"):
			frappe.throw(_("You are not permitted to create {0}.").format(doctype), frappe.PermissionError)
		doc = frappe.new_doc(doctype)

	if hasattr(doc, "docstatus") and cint(doc.docstatus) == 1:
		frappe.throw(_("Submitted records cannot be changed from the quick editor."), frappe.ValidationError)

	doc.update(clean_values)
	if name:
		doc.save()
	else:
		doc.insert()

	return {
		"resource": resource,
		"doctype": doctype,
		"name": doc.name,
		"label": _record_label(doc, config),
		"values": _record_values(doc, config),
		"full_form_route": _full_form_route(config, doc.name),
	}


def _coerce_value(field: dict, value: Any) -> Any:
	fieldtype = str(field.get("type") or "").lower()
	if fieldtype == "check":
		return cint(value)
	if fieldtype == "int":
		return cint(value)
	if value is None:
		return ""
	return value
