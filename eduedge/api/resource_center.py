from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_active_branch_context, get_allowed_school_branches

MAX_PAGE_LENGTH = 50
MAX_OPTIONS = 30

RESOURCE_CONFIG: dict[str, dict[str, Any]] = {
	"school_branches": {
		"doctype": "EduEdge School Branch",
		"title": _("School Branches"),
		"eyebrow": _("School Foundation"),
		"subtitle": _("Manage campuses, contact details, availability, and operational defaults."),
		"icon": "building",
		"route": "/app/eduedge-school-branches",
		"full_form_route": "/app/eduedge-school-branch",
		"title_field": "branch_name",
		"search_fields": ["name", "branch_name", "branch_code", "company"],
		"columns": [
			{"fieldname": "branch_name", "label": _("Campus")},
			{"fieldname": "branch_code", "label": _("Code")},
			{"fieldname": "branch_type", "label": _("Type")},
			{"fieldname": "company", "label": _("Company")},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Check"},
		],
		"filters": [
			{"fieldname": "company", "label": _("Company"), "type": "Link", "options_doctype": "Company"},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Select", "options": ["", "1", "0"]},
		],
		"editor_fields": [
			{"fieldname": "branch_name", "label": _("Branch Name"), "type": "Data", "required": True},
			{"fieldname": "branch_code", "label": _("Branch Code"), "type": "Data", "required": True},
			{"fieldname": "branch_type", "label": _("Branch Type"), "type": "Select", "options": ["Main Campus", "Campus", "Annex Campus", "Nursery", "Primary", "Secondary", "Boarding Campus", "Tutorial Centre", "CBT Centre", "Administrative Office", "Learning Centre", "Other"], "default": "Campus"},
			{"fieldname": "company", "label": _("School / Company"), "type": "Link", "options_doctype": "Company", "required": True},
			{"fieldname": "is_main_branch", "label": _("Main Branch / Campus"), "type": "Check", "default": 0},
			{"fieldname": "is_default", "label": _("Default Operational Branch"), "type": "Check", "default": 0},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Check", "default": 1},
			{"fieldname": "contact_person", "label": _("Contact Person"), "type": "Data"},
			{"fieldname": "phone", "label": _("Phone"), "type": "Phone"},
			{"fieldname": "email", "label": _("Email"), "type": "Email"},
			{"fieldname": "academic_levels_offered", "label": _("Academic Levels Offered"), "type": "Small Text"},
		],
		"advanced_note": _("Accounting defaults and stock settings remain in the full School Branch form."),
	},
	"admissions": {
		"doctype": "Student Admission",
		"title": _("Admissions"),
		"eyebrow": _("School Operations"),
		"subtitle": _("Manage admission windows and branch-specific application availability."),
		"icon": "clipboard",
		"route": "/app/eduedge-admissions",
		"full_form_route": "/app/student-admission",
		"title_field": "title",
		"branch_field": BRANCH_FIELD,
		"search_fields": ["name", "title", "academic_year"],
		"columns": [
			{"fieldname": "title", "label": _("Admission")},
			{"fieldname": "academic_year", "label": _("Academic Year")},
			{"fieldname": BRANCH_FIELD, "label": _("Branch")},
			{"fieldname": "admission_start_date", "label": _("Starts")},
			{"fieldname": "admission_end_date", "label": _("Ends")},
			{"fieldname": "enable_admission_application", "label": _("Applications"), "type": "Check"},
		],
		"filters": [
			{"fieldname": "branch", "label": _("Branch / Campus"), "type": "Branch"},
			{"fieldname": "academic_year", "label": _("Academic Year"), "type": "Link", "options_doctype": "Academic Year"},
			{"fieldname": "enable_admission_application", "label": _("Applications Enabled"), "type": "Select", "options": ["", "1", "0"]},
		],
		"editor_fields": [
			{"fieldname": "title", "label": _("Title"), "type": "Data", "required": True},
			{"fieldname": "academic_year", "label": _("Academic Year"), "type": "Link", "options_doctype": "Academic Year", "required": True},
			{"fieldname": BRANCH_FIELD, "label": _("School Branch / Campus"), "type": "Link", "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "admission_start_date", "label": _("Admission Start Date"), "type": "Date"},
			{"fieldname": "admission_end_date", "label": _("Admission End Date"), "type": "Date"},
			{"fieldname": "published", "label": _("Publish on Website"), "type": "Check", "default": 0},
			{"fieldname": "enable_admission_application", "label": _("Enable Admission Application"), "type": "Check", "default": 0},
			{"fieldname": "introduction", "label": _("Introduction"), "type": "Small Text"},
		],
		"advanced_note": _("Programme eligibility rows and public website content remain in the full form."),
	},
	"applicants": {
		"doctype": "Student Applicant",
		"title": _("Applicants"),
		"eyebrow": _("School Operations"),
		"subtitle": _("Review prospective students within the selected branch and academic session."),
		"icon": "user",
		"route": "/app/eduedge-applicants",
		"full_form_route": "/app/student-applicant",
		"title_field": "title",
		"branch_field": BRANCH_FIELD,
		"search_fields": ["name", "title", "first_name", "last_name", "student_email_id", "program"],
		"columns": [
			{"fieldname": "title", "label": _("Applicant")},
			{"fieldname": "program", "label": _("Programme")},
			{"fieldname": BRANCH_FIELD, "label": _("Branch")},
			{"fieldname": "academic_year", "label": _("Academic Year")},
			{"fieldname": "application_status", "label": _("Status"), "type": "Status"},
			{"fieldname": "application_date", "label": _("Applied")},
		],
		"filters": [
			{"fieldname": "branch", "label": _("Branch / Campus"), "type": "Branch"},
			{"fieldname": "program", "label": _("Programme"), "type": "Link", "options_doctype": "Program"},
			{"fieldname": "application_status", "label": _("Status"), "type": "Select", "options": ["", "Applied", "Approved", "Rejected", "Admitted"]},
		],
		"editor_fields": [
			{"fieldname": "naming_series", "label": _("Naming Series"), "type": "Data", "default": "EDU-APP-.YYYY.-", "hidden": True},
			{"fieldname": "first_name", "label": _("First Name"), "type": "Data", "required": True},
			{"fieldname": "middle_name", "label": _("Middle Name"), "type": "Data"},
			{"fieldname": "last_name", "label": _("Last Name"), "type": "Data"},
			{"fieldname": "program", "label": _("Programme"), "type": "Link", "options_doctype": "Program", "required": True},
			{"fieldname": BRANCH_FIELD, "label": _("School Branch / Campus"), "type": "Link", "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "academic_year", "label": _("Academic Year"), "type": "Link", "options_doctype": "Academic Year", "required": True, "clear_fields": ["academic_term"]},
			{"fieldname": "academic_term", "label": _("Academic Term"), "type": "Link", "options_doctype": "Academic Term"},
			{"fieldname": "application_date", "label": _("Application Date"), "type": "Date", "default": "Today"},
			{"fieldname": "student_email_id", "label": _("Email"), "type": "Email"},
			{"fieldname": "student_mobile_number", "label": _("Mobile Number"), "type": "Phone"},
			{"fieldname": "date_of_birth", "label": _("Date of Birth"), "type": "Date"},
			{"fieldname": "gender", "label": _("Gender"), "type": "Link", "options_doctype": "Gender"},
			{"fieldname": "paid", "label": _("Application Fee Paid"), "type": "Check", "default": 0},
		],
		"advanced_note": _("Approval, admission conversion, guardians, siblings, and attachments use the full Frappe form."),
	},
	"students": {
		"doctype": "Student",
		"title": _("Students"),
		"eyebrow": _("School Operations"),
		"subtitle": _("Search and maintain active student profiles within permitted branches."),
		"icon": "students",
		"route": "/app/eduedge-students",
		"full_form_route": "/app/student",
		"title_field": "student_name",
		"branch_field": BRANCH_FIELD,
		"search_fields": ["name", "student_name", "first_name", "last_name", "student_email_id", "student_mobile_number"],
		"columns": [
			{"fieldname": "student_name", "label": _("Student")},
			{"fieldname": BRANCH_FIELD, "label": _("Branch")},
			{"fieldname": "student_email_id", "label": _("Email")},
			{"fieldname": "student_mobile_number", "label": _("Mobile")},
			{"fieldname": "joining_date", "label": _("Joined")},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Check"},
		],
		"filters": [
			{"fieldname": "branch", "label": _("Branch / Campus"), "type": "Branch"},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Select", "options": ["", "1", "0"]},
			{"fieldname": "gender", "label": _("Gender"), "type": "Link", "options_doctype": "Gender"},
		],
		"editor_fields": [
			{"fieldname": "naming_series", "label": _("Naming Series"), "type": "Data", "default": "EDU-STU-.YYYY.-", "hidden": True},
			{"fieldname": "enabled", "label": _("Enabled"), "type": "Check", "default": 1},
			{"fieldname": "first_name", "label": _("First Name"), "type": "Data", "required": True},
			{"fieldname": "middle_name", "label": _("Middle Name"), "type": "Data"},
			{"fieldname": "last_name", "label": _("Last Name"), "type": "Data"},
			{"fieldname": BRANCH_FIELD, "label": _("School Branch / Campus"), "type": "Link", "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "joining_date", "label": _("Joining Date"), "type": "Date", "default": "Today"},
			{"fieldname": "student_email_id", "label": _("Student Email"), "type": "Email", "required": True},
			{"fieldname": "student_mobile_number", "label": _("Mobile Number"), "type": "Phone"},
			{"fieldname": "date_of_birth", "label": _("Date of Birth"), "type": "Date"},
			{"fieldname": "gender", "label": _("Gender"), "type": "Link", "options_doctype": "Gender"},
			{"fieldname": "nationality", "label": _("Nationality"), "type": "Data"},
			{"fieldname": "country", "label": _("Country"), "type": "Link", "options_doctype": "Country"},
		],
		"advanced_note": _("Guardians, customer linkage, exit records, and applicant conversion remain in the full form."),
	},
	"programs": {
		"doctype": "Program",
		"title": _("Programmes"),
		"eyebrow": _("Academics and Outcomes"),
		"subtitle": _("Maintain the school programme catalogue before assigning branch offerings."),
		"icon": "book",
		"route": "/app/eduedge-programs",
		"full_form_route": "/app/program",
		"title_field": "program_name",
		"search_fields": ["name", "program_name", "program_abbreviation", "department"],
		"columns": [
			{"fieldname": "program_name", "label": _("Programme")},
			{"fieldname": "program_abbreviation", "label": _("Abbreviation")},
			{"fieldname": "department", "label": _("Department")},
			{"fieldname": "modified", "label": _("Last Updated")},
		],
		"filters": [
			{"fieldname": "department", "label": _("Department"), "type": "Link", "options_doctype": "Department"},
		],
		"editor_fields": [
			{"fieldname": "program_name", "label": _("Program Name"), "type": "Data", "required": True},
			{"fieldname": "program_abbreviation", "label": _("Program Abbreviation"), "type": "Data"},
			{"fieldname": "department", "label": _("Department"), "type": "Link", "options_doctype": "Department"},
		],
		"advanced_note": _("Course rows and connected academic records remain in the full Program form."),
	},
	"program_offerings": {
		"doctype": "EduEdge Program Offering",
		"title": _("Programme Offerings"),
		"eyebrow": _("Academics and Outcomes"),
		"subtitle": _("Control which programmes are available by campus, session, and admission window."),
		"icon": "layers",
		"route": "/app/eduedge-program-offerings",
		"full_form_route": "/app/eduedge-program-offering",
		"title_field": "program",
		"branch_field": "school_branch",
		"search_fields": ["name", "program", "school_branch", "academic_year", "academic_term"],
		"columns": [
			{"fieldname": "program", "label": _("Programme")},
			{"fieldname": "school_branch", "label": _("Branch")},
			{"fieldname": "academic_year", "label": _("Academic Year")},
			{"fieldname": "academic_term", "label": _("Term")},
			{"fieldname": "is_active", "label": _("Active"), "type": "Check"},
			{"fieldname": "admission_enabled", "label": _("Admissions"), "type": "Check"},
		],
		"filters": [
			{"fieldname": "branch", "label": _("Branch / Campus"), "type": "Branch"},
			{"fieldname": "academic_year", "label": _("Academic Year"), "type": "Link", "options_doctype": "Academic Year"},
			{"fieldname": "is_active", "label": _("Active"), "type": "Select", "options": ["", "1", "0"]},
		],
		"editor_fields": [
			{"fieldname": "school_branch", "label": _("School Branch / Campus"), "type": "Link", "options_doctype": "EduEdge School Branch", "required": True},
			{"fieldname": "program", "label": _("Program"), "type": "Link", "options_doctype": "Program", "required": True},
			{"fieldname": "academic_year", "label": _("Academic Year"), "type": "Link", "options_doctype": "Academic Year", "required": True, "clear_fields": ["academic_term"]},
			{"fieldname": "academic_term", "label": _("Academic Term"), "type": "Link", "options_doctype": "Academic Term"},
			{"fieldname": "is_active", "label": _("Active"), "type": "Check", "default": 1},
			{"fieldname": "admission_enabled", "label": _("Available for Admission"), "type": "Check", "default": 1},
			{"fieldname": "enrollment_enabled", "label": _("Available for Enrollment"), "type": "Check", "default": 1},
			{"fieldname": "capacity", "label": _("Capacity"), "type": "Int", "default": 0, "min": 0},
			{"fieldname": "application_start_date", "label": _("Application Start Date"), "type": "Date"},
			{"fieldname": "application_end_date", "label": _("Application End Date"), "type": "Date"},
			{"fieldname": "notes", "label": _("Notes"), "type": "Small Text"},
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


def _config(resource: str) -> dict[str, Any]:
	config = RESOURCE_CONFIG.get(str(resource or "").strip())
	if not config:
		frappe.throw(_("This EduEdge resource is not available."), frappe.PermissionError)
	if not frappe.db.exists("DocType", config["doctype"]):
		frappe.throw(_("{0} is not installed on this site.").format(config["doctype"]))
	return config


def _available_fields(doctype: str, requested: list[str]) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [field for field in requested if field == "name" or field == "modified" or meta.has_field(field)]


def _field_map(config: dict) -> dict[str, dict]:
	return {field["fieldname"]: field for field in config.get("editor_fields", [])}


def _defaults(config: dict) -> dict:
	return {
		field["fieldname"]: field.get("default", "")
		for field in config.get("editor_fields", [])
		if "default" in field
	}


def _allowed_branches() -> list[dict]:
	return get_allowed_school_branches()


def _apply_branch_scope(config: dict, filters: dict, requested_branch: str | None) -> tuple[dict, list[dict]]:
	allowed = _allowed_branches()
	allowed_names = [row.get("name") for row in allowed if row.get("name")]
	allowed_map = {row.get("name"): row for row in allowed if row.get("name")}
	context = get_active_branch_context()
	selected = requested_branch or (context.get("current_branch") or {}).get("name")
	if selected and selected not in allowed_map:
		frappe.throw(_("You are not permitted to use the selected School Branch."), frappe.PermissionError)

	if config["doctype"] == "EduEdge School Branch":
		if selected:
			filters["name"] = selected
		elif allowed_names:
			filters["name"] = ["in", allowed_names]
		return filters, allowed

	branch_field = config.get("branch_field")
	if branch_field and frappe.get_meta(config["doctype"]).has_field(branch_field):
		if selected:
			filters[branch_field] = selected
		elif allowed_names:
			filters[branch_field] = ["in", allowed_names]
	return filters, allowed


def _filter_definitions(config: dict, allowed: list[dict]) -> list[dict]:
	result = deepcopy(config.get("filters", []))
	for field in result:
		if field.get("type") == "Branch":
			field["options"] = [
				{"value": row.get("name"), "label": row.get("branch_name") or row.get("name")}
				for row in allowed
			]
	return result


@frappe.whitelist()
def get_resource_page(
	resource: str,
	search: str = "",
	filters: str | dict | None = None,
	start: int | str = 0,
	page_length: int | str = 20,
) -> dict:
	_require_login()
	config = _config(resource)
	doctype = config["doctype"]
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You are not permitted to view {0}.").format(doctype), frappe.PermissionError)

	parsed_filters = _parse_json(filters)
	query_filters: dict[str, Any] = {}
	requested_branch = parsed_filters.pop("branch", None)
	allowed_filter_names = {field["fieldname"] for field in config.get("filters", [])}
	for key, value in parsed_filters.items():
		if key not in allowed_filter_names or value in (None, ""):
			continue
		query_filters[key] = cint(value) if str(value) in {"0", "1"} else value
	query_filters, allowed = _apply_branch_scope(config, query_filters, requested_branch)

	columns = deepcopy(config["columns"])
	fieldnames = _available_fields(doctype, ["name", *[column["fieldname"] for column in columns]])
	columns = [column for column in columns if column["fieldname"] in fieldnames]
	search_fields = _available_fields(doctype, config.get("search_fields", []))
	or_filters = None
	if str(search or "").strip() and search_fields:
		needle = f"%{str(search).strip()}%"
		or_filters = [[field, "like", needle] for field in search_fields]

	resolved_start = max(0, cint(start))
	resolved_length = min(MAX_PAGE_LENGTH, max(5, cint(page_length) or 20))
	rows = frappe.get_list(
		doctype,
		filters=query_filters,
		or_filters=or_filters,
		fields=fieldnames,
		order_by="modified desc",
		limit_start=resolved_start,
		limit_page_length=resolved_length + 1,
	)
	has_more = len(rows) > resolved_length
	rows = rows[:resolved_length]
	return {
		"resource": resource,
		"doctype": doctype,
		"title": config["title"],
		"eyebrow": config["eyebrow"],
		"subtitle": config["subtitle"],
		"icon": config["icon"],
		"route": config["route"],
		"columns": columns,
		"rows": rows,
		"filters": _filter_definitions(config, allowed),
		"start": resolved_start,
		"page_length": resolved_length,
		"has_more": has_more,
		"advanced_note": config.get("advanced_note", ""),
		"permissions": {
			"can_create": bool(frappe.has_permission(doctype, "create")),
			"can_write": bool(frappe.has_permission(doctype, "write")),
			"can_delete": bool(frappe.has_permission(doctype, "delete")),
		},
	}


def _record_values(doc, config: dict) -> dict:
	return {fieldname: doc.get(fieldname) for fieldname in _field_map(config)}


def _full_form_route(config: dict, name: str | None = None) -> str:
	base = config["full_form_route"].rstrip("/")
	return f"{base}/{name}" if name else base


def _link_options(field: dict, query: str, values: dict) -> list[dict]:
	fieldname = field["fieldname"]
	if fieldname in {"school_branch", BRANCH_FIELD}:
		company = values.get("company")
		rows = get_allowed_school_branches(company=company)
		needle = str(query or "").strip().lower()
		if needle:
			rows = [row for row in rows if needle in str(row.get("name") or "").lower() or needle in str(row.get("branch_name") or "").lower()]
		return [
			{"value": row.get("name"), "label": row.get("branch_name") or row.get("name"), "description": row.get("company") or ""}
			for row in rows[:MAX_OPTIONS]
		]

	doctype = field.get("options_doctype")
	if not doctype or not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	filters: dict[str, Any] = {}
	if doctype == "Company":
		filters["is_group"] = 0
	if doctype == "User":
		filters.update({"enabled": 1, "user_type": "System User"})
	if doctype == "Academic Term" and values.get("academic_year"):
		filters["academic_year"] = values.get("academic_year")
	meta = frappe.get_meta(doctype)
	candidate_fields = ["name"]
	for candidate in ("company_name", "full_name", "program_name", "term_name", "instructor_name", "department_name", "title"):
		if meta.has_field(candidate):
			candidate_fields.append(candidate)
	or_filters = None
	if str(query or "").strip():
		needle = f"%{str(query).strip()}%"
		or_filters = [[fieldname, "like", needle] for fieldname in candidate_fields]
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=candidate_fields,
		order_by="modified desc",
		limit_page_length=MAX_OPTIONS,
	)
	label_fields = [field for field in candidate_fields if field != "name"]
	return [
		{
			"value": row.get("name"),
			"label": next((row.get(field) for field in label_fields if row.get(field)), row.get("name")),
			"description": row.get("name") if label_fields else "",
		}
		for row in rows
	]


def _editor_fields(config: dict, values: dict) -> list[dict]:
	fields = deepcopy(config.get("editor_fields", []))
	for field in fields:
		if str(field.get("type", "")).lower() == "link":
			field["options"] = _link_options(field, "", values)
	return fields


@frappe.whitelist()
def get_resource_editor(resource: str, name: str | None = None, context: str | dict | None = None) -> dict:
	_require_login()
	config = _config(resource)
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
		"title": _("Update {0}").format(config["title"]) if name else _("Add {0}").format(config["title"]),
		"subtitle": config["subtitle"],
		"submit_label": _("Save Changes") if name else _("Create"),
		"fields": _editor_fields(config, values),
		"values": values,
		"can_save": can_save,
		"full_form_route": _full_form_route(config, name),
		"advanced_note": config.get("advanced_note", ""),
	}


@frappe.whitelist()
def search_resource_options(
	resource: str,
	fieldname: str,
	txt: str = "",
	values: str | dict | None = None,
) -> list[dict]:
	_require_login()
	config = _config(resource)
	field = _field_map(config).get(fieldname)
	if not field or str(field.get("type", "")).lower() != "link":
		frappe.throw(_("This field does not support option search."), frappe.ValidationError)
	return _link_options(field, txt, _parse_json(values))


def _coerce(field: dict, value: Any) -> Any:
	fieldtype = str(field.get("type") or "").lower()
	if fieldtype in {"check", "int"}:
		return cint(value)
	return "" if value is None else value


def _validate_branch_value(config: dict, values: dict) -> None:
	branch_field = config.get("branch_field")
	if not branch_field:
		return
	branch = values.get(branch_field)
	if not branch:
		return
	allowed = {row.get("name") for row in get_allowed_school_branches()}
	if branch not in allowed:
		frappe.throw(_("You are not permitted to use the selected School Branch."), frappe.PermissionError)


@frappe.whitelist()
def save_resource_record(resource: str, values: str | dict, name: str | None = None) -> dict:
	_require_login()
	config = _config(resource)
	doctype = config["doctype"]
	payload = _parse_json(values)
	allowed_fields = _field_map(config)
	clean_values = {
		fieldname: _coerce(allowed_fields[fieldname], value)
		for fieldname, value in payload.items()
		if fieldname in allowed_fields
	}
	_validate_branch_value(config, clean_values)
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
		"full_form_route": _full_form_route(config, doc.name),
	}


@frappe.whitelist()
def delete_resource_record(resource: str, name: str) -> dict:
	_require_login()
	config = _config(resource)
	doc = frappe.get_doc(config["doctype"], name)
	doc.check_permission("delete")
	if hasattr(doc, "docstatus") and cint(doc.docstatus) == 1:
		frappe.throw(_("Submitted records cannot be deleted from the EduEdge resource page."), frappe.ValidationError)
	doc.delete()
	return {"deleted": True, "name": name}
