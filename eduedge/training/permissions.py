from __future__ import annotations

import frappe

TRAINING_OVERSIGHT_ROLES = {
	"EduEdge Super Administrator",
	"System Manager",
	"EduEdge Administrator",
}


def training_progress_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if user == "Administrator" or TRAINING_OVERSIGHT_ROLES.intersection(frappe.get_roles(user)):
		return ""
	return f"`tabEduEdge Training Progress`.`user` = {frappe.db.escape(user)}"


def has_training_progress_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if doc.get("user") == user:
		return True
	roles = set(frappe.get_roles(user))
	return bool(
		TRAINING_OVERSIGHT_ROLES.intersection(roles)
		and permission_type in {None, "read", "report", "export", "print"}
	)
