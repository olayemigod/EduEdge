from __future__ import annotations

import frappe
from frappe.utils import cint

from eduedge.api import student_enrollments as core
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.enrollment_lifecycle import count_capacity_consuming_enrollments


@frappe.whitelist()
def get_student_enrollments_page(
	branch: str | None = None,
	student: str | None = None,
	enrollment: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	"""Lightweight Enrollment page payload; Link choices are searched on demand."""
	core._require_permission("read")
	resolved, selected_branch, allowed = core._resolve_branch(branch)
	institution = selected_branch.get("institution")
	selected_student_name = str(student or "").strip()
	selected_student = None
	if selected_student_name:
		row = core._student_row(selected_student_name)
		if not cint(row.enabled) or core._student_institution(row) != institution:
			frappe.throw(
				"The selected Student is not eligible for this Institution.",
				frappe.ValidationError,
			)
		if row.get(BRANCH_FIELD) not in core._same_institution_allowed_branches(institution, allowed):
			frappe.throw(
				"You do not have access to the Student's home Branch.",
				frappe.PermissionError,
			)
		selected_student = dict(row)

	length = min(max(cint(page_length), 1), core.MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	rows, has_more = core._enrollment_rows(
		resolved,
		selected_student_name or None,
		start,
		length,
	)
	detail = core._enrollment_detail(enrollment) if enrollment else None
	if detail and detail.get(BRANCH_FIELD) != resolved:
		frappe.throw(
			"The selected Enrollment does not belong to this Branch.",
			frappe.PermissionError,
		)
	if detail and detail.get("student") and not selected_student:
		selected_student = dict(core._student_row(detail.get("student")))

	return {
		"allowed_branches": allowed,
		"selected_branch": selected_branch,
		"selected_student": selected_student,
		"enrollments": rows,
		"enrollment": detail,
		"student_categories": (
			frappe.get_list(
				"Student Category",
				fields=["name"],
				order_by="name asc",
				limit_page_length=200,
			)
			if frappe.db.exists("DocType", "Student Category")
			and frappe.has_permission("Student Category", "read")
			else []
		),
		"school_houses": (
			frappe.get_list(
				"School House",
				fields=["name"],
				order_by="name asc",
				limit_page_length=200,
			)
			if frappe.db.exists("DocType", "School House")
			and frappe.has_permission("School House", "read")
			else []
		),
		"permissions": {
			"can_create": frappe.has_permission("Program Enrollment", "create"),
			"can_write": frappe.has_permission("Program Enrollment", "write"),
			"can_submit": frappe.has_permission("Program Enrollment", "submit"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


@frappe.whitelist()
def get_student_enrollment_context(student: str, branch: str, offering: str) -> dict:
	"""Return authoritative context for one selected Student + Branch + Offering."""
	core._require_permission("read")
	student_row, branch_row, offering_row = core._validate_enrollment_context(
		student,
		branch,
		offering,
	)
	capacity = cint(
		frappe.db.get_value("EduEdge Program Offering", offering, "capacity") or 0
	)
	consumed = count_capacity_consuming_enrollments(offering)
	context = dict(offering_row)
	context["capacity"] = capacity
	context["capacity_consumed"] = consumed
	context["available_slots"] = max(capacity - consumed, 0) if capacity > 0 else None
	context["student_batch"] = frappe.db.get_value(
		"EduEdge Program Offering", offering, "student_batch"
	)
	context["offering_title"] = frappe.db.get_value(
		"EduEdge Program Offering", offering, "offering_title"
	)
	return {
		"student": dict(student_row),
		"branch": dict(branch_row),
		"context": context,
		"courses": core._programme_courses(offering_row.get("program")),
	}
