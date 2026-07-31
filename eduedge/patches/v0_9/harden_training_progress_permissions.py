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
KNOWN_LEGACY_RIGHTS = {"read", "create", "write", "delete", "report", "export", "print"}


def execute() -> None:
	"""Repair historical Training Progress grants without touching other DocTypes.

	Managed EduEdge roles receive the exact current baseline, known portal and
	unrelated ERPNext legacy rows are removed, and Delete is disabled for every
	remaining custom role to preserve the progress audit trail.
	"""
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	setup_custom_perms(DOCTYPE)
	matrix = get_default_permission_matrix().get(DOCTYPE, {})
	for role, rights in matrix.items():
		if frappe.db.exists("Role", role):
			_set_exact_permission_row(role, set(rights))

	for role in PORTAL_ONLY_ROLES + NO_EDUEDGE_DEFAULT_GRANTS:
		_remove_known_legacy_rows(role)

	# Delete is never a valid Training Progress capability, including for custom
	# roles. Other custom rights remain available for deliberate school policy.
	for row in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": DOCTYPE, "permlevel": 0},
		fields=["name", "delete"],
	):
		if int(row.get("delete") or 0):
			frappe.db.set_value("Custom DocPerm", row.name, "delete", 0, update_modified=False)

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


def _remove_known_legacy_rows(role: str) -> None:
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
		if active_rights and active_rights.issubset(KNOWN_LEGACY_RIGHTS):
			frappe.db.delete("Custom DocPerm", {"name": row.name})
