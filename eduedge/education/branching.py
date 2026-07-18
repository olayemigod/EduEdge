from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)


def before_validate_student_applicant(doc, method=None) -> None:
	_assign_branch(doc)
	_validate_branch(doc)


def before_validate_student(doc, method=None) -> None:
	applicant_branch = _linked_value(
		"Student Applicant", getattr(doc, "student_applicant", None), BRANCH_FIELD
	)
	_assign_branch(doc, preferred_branch=applicant_branch)
	_validate_branch(doc)
	if applicant_branch and doc.get(BRANCH_FIELD) != applicant_branch:
		frappe.throw(
			_("Student Branch must match the originating Student Applicant Branch."),
			frappe.ValidationError,
		)
	_validate_student_branch_change(doc)


def before_validate_program_enrollment(doc, method=None) -> None:
	student_branch = _linked_value("Student", getattr(doc, "student", None), BRANCH_FIELD)
	_assign_branch(doc, preferred_branch=student_branch)
	_validate_branch(doc)
	if student_branch and doc.get(BRANCH_FIELD) != student_branch:
		frappe.throw(
			_("Program Enrollment Branch must match the selected Student Branch."),
			frappe.ValidationError,
		)


def _assign_branch(doc, preferred_branch: str | None = None) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return
	if doc.get(BRANCH_FIELD):
		return
	branch = preferred_branch or _get_context_branch()
	if branch:
		doc.set(BRANCH_FIELD, branch)


def _get_context_branch() -> str | None:
	if frappe.session.user != "Guest":
		try:
			current = get_current_school_branch()
			if current:
				return current.get("name")
		except (frappe.PermissionError, frappe.DoesNotExistError):
			pass
	return _get_public_default_branch()


def _get_public_default_branch() -> str | None:
	settings_branch = frappe.db.get_single_value("EduEdge Settings", "default_school_branch")
	if settings_branch and frappe.db.get_value(
		"EduEdge School Branch", settings_branch, "enabled"
	):
		return settings_branch
	branches = frappe.get_all(
		"EduEdge School Branch", filters={"enabled": 1}, pluck="name", limit=2
	)
	return branches[0] if len(branches) == 1 else None


def _validate_branch(doc) -> None:
	if not frappe.get_meta(doc.doctype).has_field(BRANCH_FIELD):
		return
	branch = doc.get(BRANCH_FIELD)
	configured_branch_count = frappe.db.count("EduEdge School Branch", {"enabled": 1})
	if not branch:
		if configured_branch_count:
			frappe.throw(
				_("Select a School Branch / Campus before saving this record."),
				frappe.ValidationError,
			)
		return

	branch_row = frappe.db.get_value(
		"EduEdge School Branch", branch, ["name", "enabled"], as_dict=True
	)
	if not branch_row or not branch_row.enabled:
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

	if frappe.session.user in {"Guest", "Administrator"}:
		return
	if "System Manager" in set(frappe.get_roles(frappe.session.user)):
		return
	allowed = {row["name"] for row in get_allowed_school_branches()}
	if branch not in allowed:
		frappe.throw(
			_("You do not have access to School Branch / Campus {0}.").format(branch),
			frappe.PermissionError,
		)


def _validate_student_branch_change(doc) -> None:
	if doc.is_new() or not doc.has_value_changed(BRANCH_FIELD):
		return
	conflicting = frappe.get_all(
		"Program Enrollment",
		filters={
			"student": doc.name,
			"docstatus": 1,
			BRANCH_FIELD: ["!=", doc.get(BRANCH_FIELD)],
		},
		pluck="name",
		limit=1,
	)
	if conflicting:
		frappe.throw(
			_(
				"Student Branch cannot be changed while submitted Program Enrollment {0} belongs to another branch."
			).format(conflicting[0]),
			frappe.ValidationError,
		)


def _linked_value(doctype: str, name: str | None, fieldname: str) -> str | None:
	if not name:
		return None
	return frappe.db.get_value(doctype, name, fieldname)
