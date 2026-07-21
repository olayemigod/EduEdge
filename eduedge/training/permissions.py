from __future__ import annotations

import frappe

TRAINING_PROGRESS_DOCTYPE = "EduEdge Training Progress"


def _has_oversight(user: str) -> bool:
	if user == "Administrator":
		return True
	try:
		# Delete is reserved for oversight roles in the default matrix. Using a
		# configured DocType right keeps Role Permission Manager authoritative.
		return bool(
			frappe.has_permission(
				TRAINING_PROGRESS_DOCTYPE,
				"delete",
				user=user,
				print_logs=False,
			)
		)
	except (frappe.DoesNotExistError, frappe.PermissionError):
		return False


def training_progress_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if _has_oversight(resolved_user):
		return ""
	return f"`tabEduEdge Training Progress`.`user` = {frappe.db.escape(resolved_user)}"


def has_training_progress_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if _has_oversight(resolved_user):
		return True
	return bool(doc and doc.get("user") == resolved_user)
