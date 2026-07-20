from __future__ import annotations

import frappe
from frappe.permissions import add_permission, update_permission_property

from eduedge.education.custom_fields import (
	backfill_education_branch_context,
	ensure_education_custom_fields,
)

ROLES = (
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Bursar",
	"Teacher",
	"CBT Invigilator",
	"Student Safety Officer",
)

ADMISSION_MANAGER_ROLES = (
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
)

ADMISSION_PERMISSION_TYPES = (
	"read",
	"write",
	"create",
	"delete",
	"report",
	"export",
	"print",
	"email",
	"share",
)


def after_install() -> None:
	ensure_roles()
	ensure_education_custom_fields()
	ensure_admission_manager_permissions()
	backfill_education_branch_context()


def after_migrate() -> None:
	ensure_roles()
	ensure_education_custom_fields()
	ensure_admission_manager_permissions()
	backfill_education_branch_context()


def ensure_roles() -> None:
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": 1,
				}
			).insert(ignore_permissions=True)


def ensure_admission_manager_permissions() -> None:
	"""Grant intended EduEdge administrators normal Frappe admission permissions."""
	if not frappe.db.exists("DocType", "Student Admission"):
		return

	for role in ADMISSION_MANAGER_ROLES:
		if not frappe.db.exists(
			"Custom DocPerm",
			{
				"parent": "Student Admission",
				"role": role,
				"permlevel": 0,
				"if_owner": 0,
			},
		):
			add_permission("Student Admission", role, permlevel=0, ptype="read")
		for permission_type in ADMISSION_PERMISSION_TYPES:
			update_permission_property(
				"Student Admission",
				role,
				0,
				permission_type,
				1,
				validate=False,
			)

	frappe.clear_cache(doctype="Student Admission")
