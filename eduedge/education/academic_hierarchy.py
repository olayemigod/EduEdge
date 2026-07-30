from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education import academic_validation as base
from eduedge.education.academic_fields import ACADEMIC_SECTION_FIELD, INSTITUTION_FIELD


def before_validate_program(doc, method=None) -> None:
	base.before_validate_program(doc, method)
	institution = doc.get(INSTITUTION_FIELD) if doc.meta.has_field(INSTITUTION_FIELD) else None
	section = doc.get(ACADEMIC_SECTION_FIELD) if doc.meta.has_field(ACADEMIC_SECTION_FIELD) else None
	if not institution:
		return

	context_changed = doc.is_new() or any(
		doc.has_value_changed(fieldname)
		for fieldname in (INSTITUTION_FIELD, ACADEMIC_SECTION_FIELD)
		if doc.meta.has_field(fieldname)
	)
	if not context_changed:
		return

	has_sections = bool(
		frappe.db.exists(
			"EduEdge Academic Section",
			{"institution": institution, "enabled": 1},
		)
	)
	if has_sections and not section:
		frappe.throw(
			_("Select the Programme's Academic Section before saving. For a secondary school this is the School Section, such as Junior Secondary or Senior Secondary."),
			frappe.ValidationError,
		)
	if section:
		row = frappe.db.get_value(
			"EduEdge Academic Section",
			section,
			["institution", "enabled"],
			as_dict=True,
		)
		if not row or row.institution != institution:
			frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)
		if not cint(row.enabled):
			frappe.throw(_("Select an enabled Academic Section."), frappe.ValidationError)
