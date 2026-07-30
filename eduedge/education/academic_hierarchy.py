from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import get_root_of

from eduedge.education import academic_validation as base
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_progression import validate_program_progression
from eduedge.education.native_identity import before_validate_native_master_identity


def before_validate_department(doc, method=None) -> None:
	before_validate_native_master_identity(doc, method)
	if not doc.meta.has_field(INSTITUTION_FIELD):
		return
	institution = doc.get(INSTITUTION_FIELD)
	if not institution:
		if doc.is_new():
			frappe.throw(_("Institution is required for an academic Department / School Section."), frappe.ValidationError)
		return
	institution_row = frappe.db.get_value(
		"EduEdge Institution", institution, ["company", "enabled"], as_dict=True
	)
	if not institution_row or not cint(institution_row.enabled):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
	if doc.meta.has_field("company"):
		if doc.company and institution_row.company and doc.company != institution_row.company:
			frappe.throw(
				_("Department / School Section must use the same Company as its Institution."),
				frappe.ValidationError,
			)
		doc.company = institution_row.company
	parent = doc.get("parent_department") if doc.meta.has_field("parent_department") else None
	if parent:
		fields = ["company"]
		if frappe.get_meta("Department").has_field(INSTITUTION_FIELD):
			fields.append(INSTITUTION_FIELD)
		parent_row = frappe.db.get_value("Department", parent, fields, as_dict=True)
		if not parent_row:
			frappe.throw(_("Select a valid Parent Department."), frappe.ValidationError)
		framework_root = get_root_of("Department")
		is_framework_root = bool(parent == framework_root and not parent_row.get(INSTITUTION_FIELD))
		if not is_framework_root:
			if parent_row.get(INSTITUTION_FIELD) != institution:
				frappe.throw(
					_("Parent Department must belong to the same Institution."),
					frappe.ValidationError,
				)
			if parent_row.company and institution_row.company and parent_row.company != institution_row.company:
				frappe.throw(
					_("Parent Department must belong to the same Company."),
					frappe.ValidationError,
				)
	if not doc.is_new():
		base._block_reassignment(doc, INSTITUTION_FIELD, _("Institution"))


def before_validate_program(doc, method=None) -> None:
	before_validate_native_master_identity(doc, method)
	base.validate_master_institution(doc, required=doc.is_new())
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	department = doc.get("department") if doc.meta.has_field("department") else None
	if not institution:
		return

	context_changed = doc.is_new() or any(
		doc.has_value_changed(fieldname)
		for fieldname in (INSTITUTION_FIELD, "department")
		if doc.meta.has_field(fieldname)
	)
	if context_changed and not department:
		frappe.throw(
			_("Select the Programme's Department, Faculty, School, or School Section before saving."),
			frappe.ValidationError,
		)
	if department:
		_validate_department(department, institution)

	validate_program_progression(doc)

	if not doc.is_new() and frappe.db.exists("EduEdge Program Offering", {"program": doc.name}):
		base._block_reassignment(doc, INSTITUTION_FIELD, _("Institution"))
		base._block_reassignment(doc, "department", _("Department / School Section"))


def _validate_department(department: str, institution: str) -> None:
	if not frappe.db.exists("Department", department):
		frappe.throw(_("Select a valid Department / School Section."), frappe.ValidationError)
	department_meta = frappe.get_meta("Department")
	fields = ["name", "company"]
	if department_meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	if department_meta.has_field("disabled"):
		fields.append("disabled")
	row = frappe.db.get_value("Department", department, fields, as_dict=True)
	if not row:
		frappe.throw(_("Select a valid Department / School Section."), frappe.ValidationError)
	if department_meta.has_field("disabled") and cint(row.get("disabled")):
		frappe.throw(_("Select an enabled Department / School Section."), frappe.ValidationError)
	institution_company = frappe.db.get_value("EduEdge Institution", institution, "company")
	if institution_company and row.get("company") and row.company != institution_company:
		frappe.throw(
			_("Department / School Section must belong to the same Company as the selected Institution."),
			frappe.ValidationError,
		)
	if department_meta.has_field(INSTITUTION_FIELD):
		owner = row.get(INSTITUTION_FIELD)
		if not owner:
			frappe.throw(
				_("Assign the Department / School Section to an Institution before using it on a Programme."),
				frappe.ValidationError,
			)
		if owner != institution:
			frappe.throw(
				_("Department / School Section must belong to the selected Institution."),
				frappe.ValidationError,
			)
