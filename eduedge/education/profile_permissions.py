from __future__ import annotations

import frappe


PROFILE_DOCTYPE = "EduEdge User Profile"


def user_profile_query(user: str | None = None) -> str:
	resolved_user = user or frappe.session.user
	if resolved_user == "Administrator":
		return ""
	if not resolved_user or resolved_user == "Guest":
		return "1=0"
	return f"`tab{PROFILE_DOCTYPE}`.user = {frappe.db.escape(resolved_user)}"


def has_user_profile_permission(doc, user=None, permission_type=None) -> bool:
	resolved_user = user or frappe.session.user
	if resolved_user == "Administrator":
		return True
	if not resolved_user or resolved_user == "Guest":
		return False
	# Keep DocType-level permission checks usable; list queries are still reduced
	# to the session User by user_profile_query and record checks below.
	if not doc:
		return permission_type in {"read", "create", "write"}
	profile_user = (
		frappe.db.get_value(PROFILE_DOCTYPE, doc, "user")
		if isinstance(doc, str)
		else doc.get("user")
	)
	return profile_user == resolved_user
