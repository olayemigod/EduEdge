from __future__ import annotations

import frappe

from eduedge.education.custom_fields import (
	backfill_education_branch_context,
	ensure_education_custom_fields,
)
from eduedge.permissions_baseline import (
	apply_default_permission_baseline,
	ensure_eduedge_page_role_baseline,
)

ROLE_DESK_ACCESS = {
	"EduEdge Super Administrator": 1,
	"EduEdge Public Exam Administrator": 1,
	"EduEdge Administrator": 1,
	"School Administrator": 1,
	"Academic Administrator": 1,
	"Bursar": 1,
	"Teacher": 1,
	"CBT Invigilator": 1,
	"Student Safety Officer": 1,
	"Registrar": 1,
	"Admission Officer": 1,
	"School HR Officer": 1,
	"Procurement Officer": 1,
	"School Operations Manager": 1,
	"EduEdge Parent": 0,
}


def after_install() -> None:
	ensure_roles()
	ensure_education_custom_fields()
	apply_default_permission_baseline()
	ensure_eduedge_page_role_baseline()
	backfill_education_branch_context()


def after_migrate() -> None:
	"""Maintain schema/runtime foundations without overwriting permission choices."""
	ensure_roles()
	ensure_education_custom_fields()
	backfill_education_branch_context()


def ensure_roles() -> None:
	for role_name, desk_access in ROLE_DESK_ACCESS.items():
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": desk_access,
				}
			).insert(ignore_permissions=True)
		elif role_name == "EduEdge Parent":
			# Parent access belongs to the website portal, not Desk administration.
			frappe.db.set_value("Role", role_name, "desk_access", 0, update_modified=False)
