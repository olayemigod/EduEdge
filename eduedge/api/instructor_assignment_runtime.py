from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import instructor_assignments as core
from eduedge.api import teacher_assignments as legacy
from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.teaching_assignments import current_user_instructors
from eduedge.services.instructor_branch_governance import (
	eligible_branch_names,
	get_instructor_branch_eligibility_rows,
)


def _selected_instructor(name: str | None) -> dict | None:
	resolved = str(name or "").strip()
	if not resolved:
		return None
	manager = core._can_manage_assignments()
	filters = {"name": resolved}
	if manager:
		visible = core._manager_visible_instructor_names(include_history=True)
		if resolved not in visible:
			frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	else:
		own = current_user_instructors()
		if resolved not in own:
			frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
		filters["status"] = "Active"
	doc = frappe.get_doc("Instructor", resolved)
	doc.check_permission("read")
	if filters.get("status") and str(doc.status or "") != str(filters["status"]):
		frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
	return {
		"name": doc.name,
		"instructor_name": doc.instructor_name,
		"department": doc.department,
		"employee": doc.employee,
		"status": doc.status,
		INSTITUTION_FIELD: doc.get(INSTITUTION_FIELD),
	}


@frappe.whitelist()
def get_instructor_assignments_page(
	instructor: str | None = None,
	branches: str | list | None = None,
) -> dict:
	"""Return the assignment register with Branch Governance as the upstream scope."""
	legacy._require_read()
	permitted = legacy._allowed_branches()
	permitted_names = [row["name"] for row in permitted]

	selected_instructor = _selected_instructor(instructor)
	if not selected_instructor and not core._can_manage_assignments():
		own = current_user_instructors()
		if len(own) == 1:
			selected_instructor = _selected_instructor(own[0])

	resolved_instructor = selected_instructor.get("name") if selected_instructor else None
	authoring_available = bool(
		not selected_instructor or str(selected_instructor.get("status") or "") == "Active"
	)
	governed_names = (
		eligible_branch_names(resolved_instructor, within=permitted_names)
		if resolved_instructor and authoring_available
		else set()
	)
	allowed = [row for row in permitted if row["name"] in governed_names]
	allowed_names = [row["name"] for row in allowed]

	selected = legacy._list_values(branches) if authoring_available else []
	if selected and any(name not in allowed_names for name in selected):
		frappe.throw(
			_(
				"One or more selected Branches are not covered by this Instructor's Branch Governance eligibility."
			),
			frappe.PermissionError,
		)
	if not selected:
		current = str((legacy.get_current_school_branch() or {}).get("name") or "").strip()
		selected = [current] if current in allowed_names else (allowed_names[:] if len(allowed_names) == 1 else [])

	eligibility_rows = []
	if resolved_instructor and core._can_manage_assignments():
		eligibility_rows = [
			row
			for row in get_instructor_branch_eligibility_rows(
				resolved_instructor,
				enabled_only=False,
			)
			if row.get("school_branch") in permitted_names
		]

	return {
		"allowed_branches": allowed,
		"permitted_branches": permitted,
		"selected_branches": selected,
		"selected_instructor": selected_instructor,
		"authoring_available": authoring_available,
		"assignments": legacy._assignment_rows(resolved_instructor, permitted_names),
		"branch_assignments": eligibility_rows,
		"assignment_types": list(core.ASSIGNMENT_TYPES),
		"assignment_scopes": list(core.BULK_SCOPES),
		"subject_required_types": sorted(core.SUBJECT_REQUIRED_TYPES),
		"class_responsibility_types": sorted(core.CLASS_RESPONSIBILITY_TYPES),
		"governance": {
			"route": "/app/eduedge-branch-governance",
			"eligible_branch_count": len(governed_names),
			"eligibility_period_count": len(eligibility_rows),
		},
		"permissions": {
			"can_manage": core._can_manage_assignments(),
			"can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
			"can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
			"can_view_branch_governance": frappe.has_permission(
				"EduEdge Instructor Branch Assignment",
				"read",
			),
		},
	}
