from __future__ import annotations

import frappe
from frappe import _

LIMITED_INSTRUCTOR_ROLES = {"Teacher", "Instructor"}
INSTRUCTOR_SCOPE_BYPASS_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}


def is_limited_instructor_user(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if not resolved_user or resolved_user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(resolved_user))
	return bool(roles.intersection(LIMITED_INSTRUCTOR_ROLES)) and not bool(
		roles.intersection(INSTRUCTOR_SCOPE_BYPASS_ROLES)
	)


def get_user_instructor_names(
	user: str | None = None,
	*,
	required: bool = False,
) -> list[str]:
	"""Resolve User → active Employee → active Instructor without new schema."""
	resolved_user = user or frappe.session.user
	if not is_limited_instructor_user(resolved_user):
		return []
	if not frappe.db.exists("DocType", "Employee") or not frappe.db.exists("DocType", "Instructor"):
		if required:
			frappe.throw(_("Instructor identity could not be resolved."), frappe.PermissionError)
		return []
	employees = frappe.get_all(
		"Employee",
		filters={"user_id": resolved_user, "status": "Active"},
		pluck="name",
	)
	instructors = (
		frappe.get_all(
			"Instructor",
			filters={"employee": ["in", employees], "status": "Active"},
			pluck="name",
		)
		if employees
		else []
	)
	instructors = list(dict.fromkeys(instructors))
	if required and not instructors:
		frappe.throw(
			_("Your User account is not linked to an active Employee and Instructor record. Contact an academic administrator."),
			frappe.PermissionError,
		)
	return instructors


def instructor_owns_schedule(schedule, user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if not is_limited_instructor_user(resolved_user):
		return True
	if not schedule:
		return False
	instructor = schedule.get("instructor") if hasattr(schedule, "get") else None
	return instructor in set(get_user_instructor_names(resolved_user))
