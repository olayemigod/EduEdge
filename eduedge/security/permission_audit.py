from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.permissions import get_valid_perms

from eduedge.permissions_baseline import (
	AUDIT_PERMISSION_TYPES,
	NO_EDUEDGE_DEFAULT_GRANTS,
	PLATFORM_MANAGERS,
	PORTAL_ONLY_ROLES,
	get_default_permission_matrix,
	get_eduedge_page_names,
)
from eduedge.security.permission_policy import (
	HIGH_RISK_DEFAULT_RIGHTS,
	MANAGED_NON_PLATFORM_ROLES,
	SENSITIVE_DOCTYPES,
)


def get_safe_default_permission_matrix() -> dict[str, dict[str, set[str]]]:
	"""Return the effective EduEdge default matrix after least-privilege hardening.

	The legacy baseline intentionally remains the source for normal operational
	rights. The security policy then removes Delete, Email and Share from known
	sensitive records for managed non-platform school roles. Platform managers
	and custom roles remain governed by their explicit authority.
	"""
	matrix = get_default_permission_matrix()
	restricted_roles = set(MANAGED_NON_PLATFORM_ROLES)
	for doctype in SENSITIVE_DOCTYPES:
		for role, rights in matrix.get(doctype, {}).items():
			if role in restricted_roles:
				rights.difference_update(HIGH_RISK_DEFAULT_RIGHTS)
	return matrix


def _role_classification(role: str, managed_roles: set[str]) -> str:
	if role in PORTAL_ONLY_ROLES:
		return "portal_only"
	if role in NO_EDUEDGE_DEFAULT_GRANTS:
		return "native_erpnext_no_eduedge_default"
	if role in managed_roles:
		return "eduedge_managed_default"
	return "custom_or_unclassified"


def _effective_role_rights(audited_doctypes: list[str]) -> dict[str, list[dict]]:
	rights_by_role: dict[str, list[dict]] = defaultdict(list)
	for doctype in audited_doctypes:
		for row in get_valid_perms(doctype):
			if int(row.permlevel or 0) != 0:
				continue
			rights = [
				permission
				for permission in AUDIT_PERMISSION_TYPES
				if int(row.get(permission) or 0)
			]
			if rights:
				rights_by_role[row.role].append({"doctype": doctype, "rights": rights})
	return rights_by_role


def _sensitive_permission_warnings(rights_by_role: dict[str, list[dict]]) -> list[dict]:
	warnings = []
	for role in PORTAL_ONLY_ROLES + NO_EDUEDGE_DEFAULT_GRANTS:
		for permission in rights_by_role.get(role, []):
			if permission["doctype"].startswith("EduEdge "):
				warnings.append(
					{
						"role": role,
						"doctype": permission["doctype"],
						"rights": permission["rights"],
						"reason": "Role should not receive automatic EduEdge Desk permissions.",
					}
				)

	restricted_roles = set(MANAGED_NON_PLATFORM_ROLES)
	sensitive_doctypes = set(SENSITIVE_DOCTYPES)
	high_risk = set(HIGH_RISK_DEFAULT_RIGHTS)
	for role, permissions in rights_by_role.items():
		for permission in permissions:
			doctype = permission["doctype"]
			rights = set(permission["rights"])
			if doctype == "EduEdge Training Progress" and "delete" in rights:
				warnings.append(
					{
						"role": role,
						"doctype": doctype,
						"rights": sorted(rights),
						"reason": "Training progress history must not be deletable.",
					}
				)
			if (
				role in restricted_roles
				and doctype in sensitive_doctypes
				and rights.intersection(high_risk)
			):
				warnings.append(
					{
						"role": role,
						"doctype": doctype,
						"rights": sorted(rights),
						"unsafe_rights": sorted(rights.intersection(high_risk)),
						"reason": (
							"Managed school roles must not receive Delete, Email or Share "
							"on sensitive records by default."
						),
					}
				)
	return warnings


@frappe.whitelist()
def get_role_permission_audit() -> dict:
	"""Audit installed permissions against EduEdge's hardened default policy."""
	matrix = get_safe_default_permission_matrix()
	missing_doctypes = sorted(
		doctype for doctype in matrix if not frappe.db.exists("DocType", doctype)
	)
	audited_doctypes = sorted(
		doctype for doctype in matrix if frappe.db.exists("DocType", doctype)
	)
	missing_defaults = []
	for doctype in audited_doctypes:
		valid_rows = get_valid_perms(doctype)
		for role, expected in matrix[doctype].items():
			if not frappe.db.exists("Role", role):
				continue
			role_rows = [
				row
				for row in valid_rows
				if row.role == role and int(row.permlevel or 0) == 0
			]
			actual = {
				permission_type
				for permission_type in expected
				if any(int(row.get(permission_type) or 0) for row in role_rows)
			}
			missing = sorted(set(expected) - actual)
			if missing:
				missing_defaults.append(
					{"doctype": doctype, "role": role, "missing": missing}
				)

	rights_by_role = _effective_role_rights(audited_doctypes)
	managed_roles = {
		role for role_permissions in matrix.values() for role in role_permissions
	}
	installed_roles = frappe.get_all(
		"Role",
		fields=["name", "desk_access", "disabled"],
		order_by="name asc",
		page_length=0,
	)
	roles = []
	unclassified_desk_roles = []
	portal_roles_with_desk_access = []
	for row in installed_roles:
		classification = _role_classification(row.name, managed_roles)
		role_payload = {
			"role": row.name,
			"desk_access": bool(row.desk_access),
			"disabled": bool(row.disabled),
			"classification": classification,
			"audited_permissions": rights_by_role.get(row.name, []),
		}
		roles.append(role_payload)
		if classification == "custom_or_unclassified" and row.desk_access and not row.disabled:
			unclassified_desk_roles.append(row.name)
		if classification == "portal_only" and row.desk_access and not row.disabled:
			portal_roles_with_desk_access.append(row.name)

	page_names = get_eduedge_page_names()
	remaining_page_role_gates = frappe.get_all(
		"Has Role",
		filters={
			"parent": ["in", page_names],
			"parenttype": "Page",
			"parentfield": "roles",
		},
		fields=["parent", "role"],
		order_by="parent asc, role asc",
		page_length=0,
	)
	return {
		"audit_policy": "least_privilege_v1",
		"audited_doctypes": audited_doctypes,
		"audited_pages": page_names,
		"missing_doctypes": missing_doctypes,
		"missing_defaults": missing_defaults,
		"sensitive_permission_warnings": _sensitive_permission_warnings(rights_by_role),
		"roles": roles,
		"unclassified_desk_roles": unclassified_desk_roles,
		"portal_roles_with_desk_access": portal_roles_with_desk_access,
		"remaining_page_role_gates": remaining_page_role_gates,
		"no_eduedge_default_grants": list(NO_EDUEDGE_DEFAULT_GRANTS),
		"portal_only_roles": list(PORTAL_ONLY_ROLES),
		"platform_managers": list(PLATFORM_MANAGERS),
	}
