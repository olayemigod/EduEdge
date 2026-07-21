from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission

TRAINING_PROGRESS_DOCTYPE = "EduEdge Training Progress"
TRAINING_OVERSIGHT_PERMISSION = "report"


def _has_oversight(user: str) -> bool:
	# Report is the configurable oversight capability. It allows school managers
	# and delegated HR roles to review staff progress without granting deletion.
	return user_has_role_permission(TRAINING_PROGRESS_DOCTYPE, TRAINING_OVERSIGHT_PERMISSION, user)


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
