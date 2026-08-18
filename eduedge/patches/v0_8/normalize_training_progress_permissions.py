from __future__ import annotations

import frappe
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

from eduedge.permissions_baseline import (
	AUDIT_PERMISSION_TYPES,
	NO_EDUEDGE_DEFAULT_GRANTS,
	PORTAL_ONLY_ROLES,
	get_default_permission_matrix,
)

DOCTYPE = "EduEdge Training Progress"
LEGACY_NO_DEFAULT_RIGHTS = {"read", "create", "write", "delete", "export"}


def execute() -> None:
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	# The V0.8 role audit changes Report into the explicit oversight capability.
	# Normalise known EduEdge role rows once so historical Delete/Report grants do
	# not silently become broader access. Custom roles are deliberately untouched.
	setup_custom_perms(DOCTYPE)
	role_permissions = get_default_permission_matrix().get(DOCTYPE, {})
	for role, rights in role_permissions.items():
		if frappe.db.exists("Role", role):
			_set_exact_permission_row(role, set(rights))

	# Earlier Training Centre defaults leaked progress rights to portal and
	# unrelated ERPNext roles. Remove only rows matching the known legacy shape;
	# deliberately customised rows remain visible in the permission audit.
	for role in PORTAL_ONLY_ROLES + NO_EDUEDGE_DEFAULT_GRANTS:
		_remove_known_legacy_row(role)

	frappe.clear_cache(doctype=DOCTYPE)


def _set_exact_permission_row(role: str, rights: set[str]) -> None:
	filters = {
		"parent": DOCTYPE,
		"role": role,
		"permlevel": 0,
		"if_owner": 0,
	}
	frappe.db.delete("Custom DocPerm", filters)
	initial = "read" if "read" in rights else sorted(rights)[0]
	add_permission(DOCTYPE, role, permlevel=0, ptype=initial)
	for permission_type in AUDIT_PERMISSION_TYPES:
		update_permission_property(
			DOCTYPE,
			role,
			0,
			permission_type,
			int(permission_type in rights),
			validate=False,
		)


def _remove_known_legacy_row(role: str) -> None:
	rows = frappe.get_all(
		"Custom DocPerm",
		filters={
			"parent": DOCTYPE,
			"role": role,
			"permlevel": 0,
			"if_owner": 0,
		},
		fields=["name", *AUDIT_PERMISSION_TYPES],
	)
	for row in rows:
		active_rights = {
			permission_type
			for permission_type in AUDIT_PERMISSION_TYPES
			if int(row.get(permission_type) or 0)
		}
		if active_rights and active_rights.issubset(LEGACY_NO_DEFAULT_RIGHTS):
			frappe.db.delete("Custom DocPerm", {"name": row.name})
