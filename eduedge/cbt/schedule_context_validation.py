from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint


SCHOOL_EXAM = "School Examination"


def validate_schedule_academic_scope(doc, method=None) -> None:
	"""Fail closed when sitting-specific academic masters cross Institution context."""
	if doc.get("exam_scope") != SCHOOL_EXAM or not doc.get("school_branch"):
		return
	branch = frappe.db.get_value(
		"EduEdge School Branch",
		doc.school_branch,
		["institution", "company", "enabled"],
		as_dict=True,
	)
	if not branch or not cint(branch.enabled):
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

	for doctype, fieldname, label in (
		("Program", "program", _("Programme")),
		("Assessment Group", "assessment_group", _("Assessment Group")),
	):
		value = doc.get(fieldname)
		if not value:
			continue
		_validate_owned_master(
			doctype=doctype,
			name=value,
			institution=branch.institution,
			company=branch.company,
			label=label,
		)


def _validate_owned_master(
	*,
	doctype: str,
	name: str,
	institution: str | None,
	company: str | None,
	label: str,
) -> None:
	meta = frappe.get_meta(doctype)
	ownership_field = None
	expected = None
	for fieldname, value in (
		("eduedge_institution", institution),
		("institution", institution),
		("company", company),
	):
		if value and meta.has_field(fieldname):
			ownership_field = fieldname
			expected = value
			break
	if not ownership_field:
		frappe.throw(
			_("{0} ownership is not configured for Institution-safe CBT scheduling.").format(label),
			frappe.ValidationError,
		)
	actual = frappe.db.get_value(doctype, name, ownership_field)
	if actual != expected:
		frappe.throw(
			_("The selected {0} does not belong to the Schedule Institution context.").format(label),
			frappe.ValidationError,
		)
