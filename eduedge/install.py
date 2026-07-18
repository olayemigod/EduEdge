from __future__ import annotations

import frappe

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


def after_migrate() -> None:
	ensure_roles()


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
