from __future__ import annotations

import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc

from eduedge.api.programmes import _assert_department_context, _assert_institution_access, _require_login
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.platform.access import require_eduedge_access


def _clean(value) -> str:
	return str(value or "").strip()


def _assert_programme_name_available(current_name: str, requested_name: str) -> None:
	by_name = frappe.db.exists("Program", requested_name)
	if by_name and str(by_name) != current_name:
		frappe.throw(
			_("A Class / Programme named {0} already exists.").format(frappe.bold(requested_name)),
			frappe.DuplicateEntryError,
		)

	by_title = frappe.db.exists("Program", {"program_name": requested_name})
	if by_title and str(by_title) != current_name:
		frappe.throw(
			_("A Class / Programme named {0} already exists.").format(frappe.bold(requested_name)),
			frappe.DuplicateEntryError,
		)


@frappe.whitelist(methods=["POST"])
def save_programme(
	program_name: str,
	institution: str,
	department: str,
	programme: str | None = None,
	program_abbreviation: str | None = None,
	**_legacy_values,
) -> dict:
	"""Create or update a native Education Program from the EduEdge Class modal.

	Existing Program records are renamed through Frappe's rename engine when the
	Class name changes. This preserves linked Programme Offerings, Student Groups,
	assessments and other Link/Dynamic Link references instead of creating a new
	Class record or leaving the document name out of sync with ``program_name``.
	"""

	_require_login()
	require_eduedge_access(feature_key="academics", action="save_programme")

	requested_name = _clean(program_name)
	institution = _clean(institution)
	department = _clean(department)
	abbreviation = _clean(program_abbreviation) or None
	current_name = _clean(programme)

	if not requested_name:
		frappe.throw(_("Class / Programme name is required."), frappe.ValidationError)
	if not institution:
		frappe.throw(_("Institution is required."), frappe.ValidationError)
	if not department:
		frappe.throw(_("Academic unit is required."), frappe.ValidationError)

	_assert_institution_access(institution)
	_assert_department_context(department, institution)

	renamed_from = None
	if current_name:
		doc = frappe.get_doc("Program", current_name)
		doc.check_permission("write")

		if requested_name != current_name:
			_assert_programme_name_available(current_name, requested_name)
			new_name = rename_doc(
				"Program",
				current_name,
				requested_name,
				force=False,
				merge=False,
				ignore_permissions=False,
				show_alert=False,
			)
			renamed_from = current_name
			current_name = _clean(new_name) or requested_name
			doc = frappe.get_doc("Program", current_name)
			doc.check_permission("write")
	else:
		if not frappe.has_permission("Program", "create"):
			frappe.throw(_("You are not permitted to create Classes / Programmes."), frappe.PermissionError)
		doc = frappe.new_doc("Program")

	doc.program_name = requested_name
	doc.program_abbreviation = abbreviation
	doc.department = department
	doc.set(INSTITUTION_FIELD, institution)
	doc.save()

	return {
		"name": doc.name,
		"program_name": doc.program_name,
		"program_abbreviation": doc.program_abbreviation,
		"institution": doc.get(INSTITUTION_FIELD),
		"department": doc.department,
		"renamed": bool(renamed_from),
		"renamed_from": renamed_from,
	}
