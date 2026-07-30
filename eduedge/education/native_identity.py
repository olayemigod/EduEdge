from __future__ import annotations

import hashlib
import re

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD

DISPLAY_FIELD = "eduedge_display_name"
MAX_NATIVE_NAME_LENGTH = 140

IDENTITY_CONFIG = {
	"Department": {"source": "department_name", "label": "Department / School Section Name"},
	"Program": {"source": "program_name", "label": "Programme / Class Name"},
	"Course": {"source": "course_name", "label": "Course / Subject Name"},
	"Student Group": {"source": "student_group_name", "label": "Class Arm / Level Name"},
	"Student Batch Name": {"source": "batch_name", "label": "Student Batch / Cohort Name"},
}


def display_name_field(*, insert_after: str, label: str, description: str) -> dict:
	return {
		"fieldname": DISPLAY_FIELD,
		"fieldtype": "Data",
		"label": label,
		"insert_after": insert_after,
		"in_list_view": 1,
		"in_standard_filter": 1,
		"description": description,
	}


def ensure_native_identity_foundation() -> None:
	"""Keep collision-prone native masters usable on shared multi-Institution sites."""
	for doctype in IDENTITY_CONFIG:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if not meta.has_field(DISPLAY_FIELD):
			continue
		_ensure_doctype_property(doctype, "title_field", DISPLAY_FIELD, "Data")
		_ensure_doctype_property(doctype, "show_title_field_in_link", "1", "Check")
		_backfill_display_names(doctype, IDENTITY_CONFIG[doctype]["source"])
		frappe.clear_cache(doctype=doctype)


def _ensure_doctype_property(doctype: str, property_name: str, value: str, property_type: str) -> None:
	filters = {
		"doc_type": doctype,
		"doctype_or_field": "DocType",
		"property": property_name,
	}
	existing = frappe.db.get_value("Property Setter", filters, ["name", "value"], as_dict=True)
	if existing and str(existing.value or "") == str(value):
		return
	make_property_setter(
		doctype,
		None,
		property_name,
		value,
		property_type,
		for_doctype=True,
		validate_fields_for_doctype=False,
	)


def _backfill_display_names(doctype: str, source_field: str) -> None:
	frappe.db.sql(
		f"""
		update `tab{doctype}`
		set `{DISPLAY_FIELD}` = `{source_field}`
		where coalesce(`{DISPLAY_FIELD}`, '') = ''
			and coalesce(`{source_field}`, '') != ''
		"""
	)


def before_naming_native_master(doc, method=None) -> None:
	config = IDENTITY_CONFIG.get(doc.doctype)
	if not config or not doc.meta.has_field(DISPLAY_FIELD):
		return
	friendly = _clean_display_name(doc.get(DISPLAY_FIELD) or doc.get(config["source"]))
	if not friendly:
		return
	_resolve_early_context(doc)
	doc.set(DISPLAY_FIELD, friendly)
	# Serialise collision checks for this native DocType. Creation is infrequent and
	# this avoids two concurrent tenants both selecting the same unsuffixed identity.
	frappe.db.sql("select name from `tabDocType` where name = %s for update", (doc.doctype,))
	doc.set(config["source"], _available_native_name(doc, friendly, config["source"]))


def before_validate_native_master_identity(doc, method=None) -> None:
	config = IDENTITY_CONFIG.get(doc.doctype)
	if not config or not doc.meta.has_field(DISPLAY_FIELD):
		return
	friendly = _clean_display_name(doc.get(DISPLAY_FIELD) or doc.get(config["source"]))
	if friendly:
		doc.set(DISPLAY_FIELD, friendly)
	if doc.is_new() or not doc.meta.has_field(config["source"]):
		return
	old_source = doc.get_db_value(config["source"])
	new_source = doc.get(config["source"])
	if old_source and new_source != old_source:
		frappe.throw(
			_("The technical identity of this {0} cannot be edited directly. Use Rename if the document identity must change.").format(doc.doctype),
			frappe.ValidationError,
		)


def friendly_name(row: dict | frappe._dict | None, source_field: str = "name") -> str:
	if not row:
		return ""
	return str(row.get(DISPLAY_FIELD) or row.get(source_field) or row.get("name") or "")


def _resolve_early_context(doc) -> None:
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if not institution and doc.doctype == "Student Group" and doc.get("program"):
		institution = frappe.db.get_value("Program", doc.program, INSTITUTION_FIELD)
		if institution:
			doc.set(INSTITUTION_FIELD, institution)
	if doc.doctype == "Department" and institution and doc.meta.has_field("company"):
		company = frappe.db.get_value("EduEdge Institution", institution, "company")
		if company:
			doc.company = company


def _available_native_name(doc, friendly: str, source_field: str) -> str:
	if not _identity_exists(doc, friendly, source_field):
		return friendly
	context = _context_token(doc)
	candidate = _fit_name(friendly, f" [{context}]")
	counter = 2
	while _identity_exists(doc, candidate, source_field):
		candidate = _fit_name(friendly, f" [{context}-{counter}]")
		counter += 1
	return candidate


def _identity_exists(doc, candidate: str, source_field: str) -> bool:
	filters: dict = {source_field: candidate}
	if doc.doctype == "Department" and doc.meta.has_field("company"):
		filters["company"] = doc.get("company")
	if doc.name:
		filters["name"] = ["!=", doc.name]
	return bool(frappe.db.exists(doc.doctype, filters))


def _context_token(doc) -> str:
	parts: list[str] = []
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	if institution:
		code = frappe.db.get_value("EduEdge Institution", institution, "institution_code") or institution
		parts.append(_slug(code, 24))
	if doc.doctype == "Student Group":
		branch = doc.get(BRANCH_FIELD) if doc.meta.has_field(BRANCH_FIELD) else None
		if branch:
			branch_code = frappe.db.get_value("EduEdge School Branch", branch, "branch_code") or branch
			parts.append(_slug(branch_code, 16))
		if doc.get("academic_year"):
			parts.append(_slug(doc.academic_year, 16))
		if doc.get("program"):
			programme = frappe.db.get_value(
				"Program",
				doc.program,
				["program_abbreviation", DISPLAY_FIELD, "program_name"],
				as_dict=True,
			) or {}
			parts.append(_slug(programme.get("program_abbreviation") or programme.get(DISPLAY_FIELD) or programme.get("program_name"), 16))
	if not parts:
		seed = "::".join(str(doc.get(field) or "") for field in ("company", "program", "academic_year", "academic_term"))
		parts.append(hashlib.sha1(seed.encode()).hexdigest()[:8].upper())
	return "-".join(part for part in parts if part)[:64] or "EDUEDGE"


def _clean_display_name(value: str | None) -> str:
	return " ".join(str(value or "").split())[:120]


def _slug(value: str | None, limit: int) -> str:
	return re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")[:limit]


def _fit_name(friendly: str, suffix: str) -> str:
	available = max(MAX_NATIVE_NAME_LENGTH - len(suffix), 1)
	return f"{friendly[:available].rstrip()}{suffix}"
