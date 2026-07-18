from __future__ import annotations

import frappe

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


def after_install() -> None:
	ensure_roles()
	ensure_education_custom_fields()
	backfill_education_branch_context()


def after_migrate() -> None:
	ensure_roles()
	ensure_education_custom_fields()
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
