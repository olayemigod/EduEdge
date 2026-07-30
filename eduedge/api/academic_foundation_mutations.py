from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_hierarchy import _validate_department
from eduedge.education.native_identity import DISPLAY_FIELD
from eduedge.platform.access import require_eduedge_access


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def save_department(
	institution: str,
	department_name: str,
	department: str | None = None,
	parent_department: str | None = None,
	is_group: int | str = 1,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_department")
	institution_doc = frappe.get_doc("EduEdge Institution", institution)
	institution_doc.check_permission("read")
	friendly = " ".join(str(department_name or "").split())
	if not friendly:
		frappe.throw(_("Department / School Section Name is required."), frappe.ValidationError)
	if department:
		doc = frappe.get_doc("Department", department)
		doc.check_permission("write")
		doc.set(DISPLAY_FIELD, friendly)
	else:
		if not frappe.has_permission("Department", "create"):
			frappe.throw(_("You are not permitted to create Departments / School Sections."), frappe.PermissionError)
		doc = frappe.new_doc("Department")
		doc.department_name = friendly
		doc.set(DISPLAY_FIELD, friendly)
	doc.company = institution_doc.company
	doc.parent_department = parent_department or None
	doc.is_group = cint(is_group)
	doc.set(INSTITUTION_FIELD, institution)
	doc.save()
	_validate_department(doc.name, institution)
	return {
		"name": doc.name,
		"department_name": doc.get(DISPLAY_FIELD) or doc.department_name,
		"technical_name": doc.department_name,
		"parent_department": doc.parent_department,
		"is_group": cint(doc.is_group),
	}
