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

IDENTITY_READY = "Ready"
IDENTITY_NO_EMPLOYEE = "No Employee Link"
IDENTITY_MISSING_EMPLOYEE = "Missing Employee"
IDENTITY_INACTIVE_INSTRUCTOR = "Inactive Instructor"
IDENTITY_INACTIVE_EMPLOYEE = "Inactive Employee"
IDENTITY_NO_USER = "No User Login"
IDENTITY_INACTIVE_USER = "Inactive User"
IDENTITY_AMBIGUOUS_EMPLOYEE = "Ambiguous Employee Mapping"
IDENTITY_AMBIGUOUS_INSTRUCTOR = "Ambiguous Instructor Mapping"


def is_limited_instructor_user(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if not resolved_user or resolved_user in {"Guest", "Administrator"}:
		return False
	roles = set(frappe.get_roles(resolved_user))
	return bool(roles.intersection(LIMITED_INSTRUCTOR_ROLES)) and not bool(
		roles.intersection(INSTRUCTOR_SCOPE_BYPASS_ROLES)
	)


def get_active_instructor_names_for_user(user: str | None = None) -> list[str]:
	"""Resolve an authenticated User to active Instructor identities through Employee.

	This helper never grants access by itself. Exact Instructor Assignment capability
	checks consume it and fail closed unless the result is unique.
	"""
	resolved_user = user or frappe.session.user
	if not resolved_user or resolved_user == "Guest":
		return []
	if not frappe.db.exists("DocType", "Employee") or not frappe.db.exists("DocType", "Instructor"):
		return []
	if frappe.db.exists("User", resolved_user) and not frappe.db.get_value("User", resolved_user, "enabled"):
		return []
	employees = frappe.get_all(
		"Employee",
		filters={"user_id": resolved_user, "status": "Active"},
		pluck="name",
		limit_page_length=0,
	)
	if not employees:
		return []
	instructors = frappe.get_all(
		"Instructor",
		filters={"employee": ["in", employees], "status": "Active"},
		pluck="name",
		limit_page_length=0,
	)
	return list(dict.fromkeys(instructors))


def resolve_exact_instructor_for_user(
	user: str | None = None,
	*,
	required: bool = False,
) -> str:
	"""Return exactly one active Instructor identity or fail closed when required."""
	resolved_user = user or frappe.session.user
	instructors = get_active_instructor_names_for_user(resolved_user)
	if len(instructors) == 1:
		return instructors[0]
	if not required:
		return ""
	if not instructors:
		frappe.throw(
			_("Your User account is not linked to exactly one active Employee and Instructor record. Contact an academic administrator."),
			frappe.PermissionError,
		)
	frappe.throw(
		_("Your User account resolves to more than one active Instructor. Academic capability access is blocked until the identity mapping is corrected."),
		frappe.PermissionError,
	)


def get_user_instructor_names(
	user: str | None = None,
	*,
	required: bool = False,
) -> list[str]:
	"""Resolve limited Teacher/Instructor users without changing existing role behavior."""
	resolved_user = user or frappe.session.user
	if not is_limited_instructor_user(resolved_user):
		return []
	instructors = get_active_instructor_names_for_user(resolved_user)
	if required and not instructors:
		frappe.throw(
			_("Your User account is not linked to an active Employee and Instructor record. Contact an academic administrator."),
			frappe.PermissionError,
		)
	return instructors


def get_instructor_identity_states(instructor_names: list[str] | tuple[str, ...] | set[str]) -> dict[str, dict]:
	"""Return manager-facing teaching identity readiness without mutating history.

	A profile may legitimately exist without a login. Such a record remains usable for
	historical and administrative purposes, but assignment-driven operational access is
	not ready until User -> active Employee -> active Instructor resolves uniquely.
	"""
	names = list(dict.fromkeys(str(name or "").strip() for name in instructor_names if str(name or "").strip()))
	if not names or not frappe.db.exists("DocType", "Instructor"):
		return {}

	instructor_rows = frappe.get_all(
		"Instructor",
		filters={"name": ["in", names]},
		fields=["name", "instructor_name", "employee", "status"],
		limit_page_length=0,
	)
	instructor_map = {row.name: row for row in instructor_rows}
	employee_names = sorted({row.employee for row in instructor_rows if row.employee})
	employee_map: dict[str, object] = {}
	if employee_names and frappe.db.exists("DocType", "Employee"):
		employee_rows = frappe.get_all(
			"Employee",
			filters={"name": ["in", employee_names]},
			fields=["name", "employee_name", "status", "user_id"],
			limit_page_length=0,
		)
		employee_map = {row.name: row for row in employee_rows}

	user_ids = sorted({row.user_id for row in employee_map.values() if row.user_id})
	user_map: dict[str, object] = {}
	if user_ids:
		user_rows = frappe.get_all(
			"User",
			filters={"name": ["in", user_ids]},
			fields=["name", "full_name", "enabled"],
			limit_page_length=0,
		)
		user_map = {row.name: row for row in user_rows}

	active_employees_by_user: dict[str, list[str]] = {user: [] for user in user_ids}
	if user_ids and frappe.db.exists("DocType", "Employee"):
		for row in frappe.get_all(
			"Employee",
			filters={"user_id": ["in", user_ids], "status": "Active"},
			fields=["name", "user_id"],
			limit_page_length=0,
		):
			active_employees_by_user.setdefault(row.user_id, []).append(row.name)

	all_active_employee_names = sorted(
		{employee for values in active_employees_by_user.values() for employee in values}
	)
	active_instructors_by_user: dict[str, list[str]] = {user: [] for user in user_ids}
	if all_active_employee_names:
		active_instructors = frappe.get_all(
			"Instructor",
			filters={"employee": ["in", all_active_employee_names], "status": "Active"},
			fields=["name", "employee"],
			limit_page_length=0,
		)
		employee_to_user = {
			employee: user
			for user, employees in active_employees_by_user.items()
			for employee in employees
		}
		for row in active_instructors:
			user = employee_to_user.get(row.employee)
			if user:
				active_instructors_by_user.setdefault(user, []).append(row.name)

	states: dict[str, dict] = {}
	for name in names:
		instructor = instructor_map.get(name)
		if not instructor:
			continue
		employee = employee_map.get(instructor.employee) if instructor.employee else None
		user_id = str(getattr(employee, "user_id", "") or "").strip() if employee else ""
		user = user_map.get(user_id) if user_id else None
		active_employees = list(dict.fromkeys(active_employees_by_user.get(user_id, []))) if user_id else []
		active_instructors = list(dict.fromkeys(active_instructors_by_user.get(user_id, []))) if user_id else []

		status = IDENTITY_READY
		severity = "success"
		message = _("Teaching login resolves to this Instructor through one active Employee record.")
		if instructor.status != "Active":
			status = IDENTITY_INACTIVE_INSTRUCTOR
			severity = "neutral"
			message = _("This Instructor is historical/inactive and cannot receive current operational capabilities.")
		elif not instructor.employee:
			status = IDENTITY_NO_EMPLOYEE
			severity = "warning"
			message = _("Link an Employee before this Instructor can use assignment-driven teaching access.")
		elif not employee:
			status = IDENTITY_MISSING_EMPLOYEE
			severity = "danger"
			message = _("The linked Employee record could not be resolved. Correct the Instructor profile.")
		elif employee.status != "Active":
			status = IDENTITY_INACTIVE_EMPLOYEE
			severity = "warning"
			message = _("The linked Employee is inactive, so current teaching access fails closed.")
		elif not user_id:
			status = IDENTITY_NO_USER
			severity = "warning"
			message = _("The Employee has no User login. Historical records are safe, but interactive teaching access is not ready.")
		elif not user or not int(user.enabled or 0):
			status = IDENTITY_INACTIVE_USER
			severity = "warning"
			message = _("The Employee User login is missing or disabled, so interactive teaching access is not ready.")
		elif len(active_employees) != 1:
			status = IDENTITY_AMBIGUOUS_EMPLOYEE
			severity = "danger"
			message = _("This User is linked to more than one active Employee. Resolve the Employee mapping before enabling assignment-driven access.")
		elif len(active_instructors) != 1 or active_instructors[0] != name:
			status = IDENTITY_AMBIGUOUS_INSTRUCTOR
			severity = "danger"
			message = _("This User resolves to more than one active Instructor. Resolve the duplicate Instructor mapping before enabling assignment-driven access.")

		states[name] = {
			"status": status,
			"severity": severity,
			"operational_ready": status == IDENTITY_READY,
			"message": message,
			"employee": instructor.employee or "",
			"employee_name": getattr(employee, "employee_name", "") or "" if employee else "",
			"user": user_id,
			"user_full_name": getattr(user, "full_name", "") or "" if user else "",
			"active_employee_count": len(active_employees),
			"active_instructor_count": len(active_instructors),
		}
	return states


def get_instructor_identity_state(instructor: str) -> dict:
	return get_instructor_identity_states([instructor]).get(str(instructor or "").strip(), {})


def instructor_owns_schedule(schedule, user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	if not is_limited_instructor_user(resolved_user):
		return True
	if not schedule:
		return False
	instructor = schedule.get("instructor") if hasattr(schedule, "get") else None
	return instructor in set(get_user_instructor_names(resolved_user))
