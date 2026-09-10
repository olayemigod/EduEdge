from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import instructor_assignments as core
from eduedge.api import teacher_assignments as legacy
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.teaching_assignments import current_user_instructors


def _selected_instructor(name: str | None) -> dict | None:
	resolved = str(name or "").strip()
	if not resolved:
		return None
	filters = {"name": resolved, "status": "Active"}
	if not core._can_manage_assignments():
		own = current_user_instructors()
		if resolved not in own:
			frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	row = frappe.db.get_value(
		"Instructor",
		filters,
		["name", "instructor_name", "department", "employee", INSTITUTION_FIELD],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	return dict(row)


@frappe.whitelist()
def get_instructor_assignments_page(
	instructor: str | None = None,
	branches: str | list | None = None,
) -> dict:
	"""Return the assignment register without preloading large selector datasets."""
	legacy._require_read()
	allowed = legacy._allowed_branches()
	allowed_names = [row["name"] for row in allowed]
	selected = legacy._list_values(branches)
	if selected and any(name not in allowed_names for name in selected):
		frappe.throw(
			_("One or more selected Branches are not available to your user."),
			frappe.PermissionError,
		)
	if not selected:
		current = str((legacy.get_current_school_branch() or {}).get("name") or "").strip()
		selected = [current] if current else (allowed_names[:] if len(allowed_names) == 1 else [])

	selected_instructor = _selected_instructor(instructor)
	if not selected_instructor and not core._can_manage_assignments():
		own = current_user_instructors()
		if len(own) == 1:
			selected_instructor = _selected_instructor(own[0])

	resolved_instructor = selected_instructor.get("name") if selected_instructor else None
	register_branches = selected or allowed_names
	return {
		"allowed_branches": allowed,
		"selected_branches": selected,
		"selected_instructor": selected_instructor,
		"assignments": legacy._assignment_rows(resolved_instructor, register_branches),
		"branch_assignments": (
			legacy._branch_assignment_rows(resolved_instructor, register_branches)
			if core._can_manage_assignments()
			else []
		),
		"assignment_types": list(core.ASSIGNMENT_TYPES),
		"assignment_scopes": list(core.BULK_SCOPES),
		"subject_required_types": sorted(core.SUBJECT_REQUIRED_TYPES),
		"class_responsibility_types": sorted(core.CLASS_RESPONSIBILITY_TYPES),
		"permissions": {
			"can_manage": core._can_manage_assignments(),
			"can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
			"can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
			"can_manage_branch_access": bool(
				frappe.has_permission("EduEdge Instructor Branch Assignment", "create")
				or frappe.has_permission("EduEdge Instructor Branch Assignment", "write")
			),
		},
	}
