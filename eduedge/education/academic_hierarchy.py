from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education import academic_validation as base
from eduedge.education.academic_fields import INSTITUTION_FIELD


def before_validate_program(doc, method=None) -> None:
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
