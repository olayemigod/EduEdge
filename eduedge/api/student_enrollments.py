from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch
from eduedge.services.enrollment_lifecycle import count_capacity_consuming_enrollments

MAX_PAGE_LENGTH = 50


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission("Program Enrollment", permission_type):
		frappe.throw(
			_("You are not permitted to {0} Program Enrollment records.").format(permission_type),
			frappe.PermissionError,
		)


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid enrollment payload is required."), frappe.ValidationError)
	return payload


def _allowed_branches() -> list[dict]:
	rows = get_allowed_school_branches() or []
	result: list[dict] = []
	for source in rows:
		row = dict(source)
		name = str(row.get("name") or "").strip()
		if not name:
			continue
		details = frappe.db.get_value(
			"EduEdge School Branch",
			name,
			["branch_name", "institution", "enabled"],
			as_dict=True,
		) or {}
		row.update(details)
		if not cint(row.get("enabled", 1)):
			continue
		if row.get("institution"):
			row["institution_name"] = frappe.db.get_value(
				"EduEdge Institution", row["institution"], "institution_name"
			)
		result.append(row)
	return result


def _resolve_branch(branch: str | None) -> tuple[str, dict, list[dict]]:
	allowed = _allowed_branches()
	by_name = {row["name"]: row for row in allowed}
	resolved = str(branch or "").strip()
	if not resolved:
		resolved = str((get_current_school_branch() or {}).get("name") or "").strip()
	if not resolved and len(allowed) == 1:
		resolved = allowed[0]["name"]
	if not resolved:
		frappe.throw(_("Select a permitted School Branch / Campus."), frappe.ValidationError)
	assert_branch_access(resolved)
	if resolved not in by_name:
		frappe.throw(_("The selected Branch is not available to your user."), frappe.PermissionError)
	return resolved, by_name[resolved], allowed


def _row_fields(doctype: str, desired: list[str]) -> list[str]:
	meta = frappe.get_meta(doctype)
	return [fieldname for fieldname in desired if fieldname == "name" or meta.has_field(fieldname)]


def _same_institution_allowed_branches(institution: str, allowed: list[dict]) -> list[str]:
	return [row["name"] for row in allowed if row.get("institution") == institution]


def _student_row(student: str) -> frappe._dict:
	row = frappe.db.get_value(
		"Student",
		student,
		["name", "student_name", "enabled", "image", BRANCH_FIELD, "student_email_id", "student_mobile_number"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Student {0} does not exist.").format(student), frappe.DoesNotExistError)
	doc = frappe.get_doc("Student", student)
	doc.check_permission("read")
	return row


def _student_institution(student_row: frappe._dict) -> str | None:
	branch = student_row.get(BRANCH_FIELD)
	return frappe.db.get_value("EduEdge School Branch", branch, "institution") if branch else None


def _eligible_students(institution: str, allowed: list[dict]) -> list[dict]:
	branches = _same_institution_allowed_branches(institution, allowed)
	if not branches:
		return []
	return frappe.get_list(
		"Student",
		filters={BRANCH_FIELD: ["in", branches], "enabled": 1},
		fields=["name", "student_name", "image", BRANCH_FIELD, "student_email_id", "student_mobile_number"],
		order_by="student_name asc",
		limit_page_length=1000,
	)


def _offering_rows(branch: str) -> list[dict]:
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "is_active": 1, "enrollment_enabled": 1},
		fields=[
			"name", "offering_title", "offering_code", "school_branch", "institution", "program",
			"department", "academic_year", "academic_term", "student_batch", "capacity",
			"start_date", "end_date", "study_mode", "delivery_mode",
		],
		order_by="academic_year desc, offering_title asc",
		limit_page_length=500,
	)
	for row in rows:
		capacity = cint(row.get("capacity"))
		consumed = count_capacity_consuming_enrollments(row.name)
		row["capacity_consumed"] = consumed
		row["available_slots"] = max(capacity - consumed, 0) if capacity > 0 else None
	return rows


def _programme_courses(program: str | None) -> list[dict]:
	if not program:
		return []
	return frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		fields=["course", "course_name", "required"],
		order_by="idx asc",
		limit_page_length=500,
	)


def _enrollment_detail(name: str) -> dict:
	doc = frappe.get_doc("Program Enrollment", name)
	doc.check_permission("read")	
	result = doc.as_dict(no_nulls=False)
	result["status_label"] = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(doc.docstatus, "Unknown")
	result["can_edit"] = bool(doc.docstatus == 0 and frappe.has_permission("Program Enrollment", "write", doc=doc))
	result["can_submit"] = bool(doc.docstatus == 0 and frappe.has_permission("Program Enrollment", "submit", doc=doc))
	return result


def _enrollment_rows(branch: str, student: str | None, start: int, page_length: int) -> tuple[list[dict], bool]:
	filters: dict[str, Any] = {BRANCH_FIELD: branch, "docstatus": ["<", 2]}
	if student:
		filters["student"] = student
	rows = frappe.get_list(
		"Program Enrollment",
		filters=filters,
		fields=_row_fields(
			"Program Enrollment",
			[
				"name", "student", "student_name", "program", "academic_year", "academic_term",
				"enrollment_date", "student_batch_name", OFFERING_FIELD, BRANCH_FIELD, "docstatus",
			],
		),
		order_by="creation desc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	for row in rows:
		row["status_label"] = {0: "Draft", 1: "Submitted"}.get(cint(row.docstatus), "Unknown")
	return rows, has_more


@frappe.whitelist()
def get_student_enrollments_page(
	branch: str | None = None,
	student: str | None = None,
	enrollment: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	_require_permission("read")
	resolved, selected_branch, allowed = _resolve_branch(branch)
	institution = selected_branch.get("institution")
	students = _eligible_students(institution, allowed)
	student_names = {row.name for row in students}
	selected_student = str(student or "").strip()
	if selected_student and selected_student not in student_names:
		row = _student_row(selected_student)
		if not cint(row.enabled) or _student_institution(row) != institution:
			frappe.throw(_("The selected Student is not eligible for this Institution."), frappe.ValidationError)
		if row.get(BRANCH_FIELD) not in _same_institution_allowed_branches(institution, allowed):
			frappe.throw(_("You do not have access to the Student's home Branch."), frappe.PermissionError)
		students.append(dict(row))
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	rows, has_more = _enrollment_rows(resolved, selected_student or None, start, length)
	detail = _enrollment_detail(enrollment) if enrollment else None
	if detail and detail.get(BRANCH_FIELD) != resolved:
		frappe.throw(_("The selected Enrollment does not belong to this Branch."), frappe.PermissionError)
	offerings = _offering_rows(resolved)
	selected_offering = None
	if detail and detail.get(OFFERING_FIELD):
		selected_offering = next((row for row in offerings if row.name == detail.get(OFFERING_FIELD)), None)
	return {
		"allowed_branches": allowed,
		"selected_branch": selected_branch,
		"students": students,
		"offerings": offerings,
		"enrollments": rows,
		"enrollment": detail,
		"courses": _programme_courses((selected_offering or {}).get("program") if selected_offering else None),
		"student_categories": frappe.get_list("Student Category", fields=["name"], order_by="name asc", limit_page_length=200) if frappe.db.exists("DocType", "Student Category") and frappe.has_permission("Student Category", "read") else [],
		"school_houses": frappe.get_list("School House", fields=["name"], order_by="name asc", limit_page_length=200) if frappe.db.exists("DocType", "School House") and frappe.has_permission("School House", "read") else [],
		"permissions": {
			"can_create": frappe.has_permission("Program Enrollment", "create"),
			"can_write": frappe.has_permission("Program Enrollment", "write"),
			"can_submit": frappe.has_permission("Program Enrollment", "submit"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


@frappe.whitelist()
def get_student_enrollment_options(student: str, branch: str, offering: str | None = None) -> dict:
	_require_permission("read")
	resolved, selected_branch, allowed = _resolve_branch(branch)
	student_row = _student_row(student)
	if not cint(student_row.enabled):
		frappe.throw(_("Only enabled Students can be enrolled."), frappe.ValidationError)
	institution = selected_branch.get("institution")
	if _student_institution(student_row) != institution:
		frappe.throw(_("A Student may enroll across Campuses only within the same Institution."), frappe.ValidationError)
	if student_row.get(BRANCH_FIELD) not in _same_institution_allowed_branches(institution, allowed):
		frappe.throw(_("You do not have access to the Student's home Branch."), frappe.PermissionError)
	offerings = _offering_rows(resolved)
	selected = next((row for row in offerings if row.name == offering), None) if offering else None
	if offering and not selected:
		frappe.throw(_("Select an active enrollment-enabled Programme Offering for this Branch."), frappe.ValidationError)
	return {
		"student": student_row,
		"branch": selected_branch,
		"offerings": offerings,
		"context": selected or {},
		"courses": _programme_courses((selected or {}).get("program")),
	}


def _validate_enrollment_context(student: str, branch: str, offering: str) -> tuple[frappe._dict, frappe._dict, frappe._dict]:
	assert_branch_access(branch)
	student_row = _student_row(student)
	if not cint(student_row.enabled):
		frappe.throw(_("Only enabled Students can be enrolled."), frappe.ValidationError)
	branch_row = frappe.db.get_value(
		"EduEdge School Branch", branch, ["name", "institution", "enabled"], as_dict=True
	)
	if not branch_row or not cint(branch_row.enabled):
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
	offering_row = frappe.db.get_value(
		"EduEdge Program Offering",
		offering,
		[
			"name", "school_branch", "institution", "program", "academic_year", "academic_term",
			"student_batch", "is_active", "enrollment_enabled",
		],
		as_dict=True,
	)
	if not offering_row:
		frappe.throw(_("Programme Offering does not exist."), frappe.DoesNotExistError)
	offering_doc = frappe.get_doc("EduEdge Program Offering", offering)
	offering_doc.check_permission("read")
	if offering_row.school_branch != branch or not cint(offering_row.is_active) or not cint(offering_row.enrollment_enabled):
		frappe.throw(_("Select an active enrollment-enabled Programme Offering for this Branch."), frappe.ValidationError)
	student_institution = _student_institution(student_row)
	if not student_institution or student_institution != branch_row.institution or offering_row.institution != branch_row.institution:
		frappe.throw(_("Student, Branch and Programme Offering must belong to the same Institution."), frappe.ValidationError)
	return student_row, branch_row, offering_row


@frappe.whitelist(methods=["POST"])
def save_student_enrollment(payload: str | dict, submit: int = 0) -> dict:
	require_eduedge_access(feature_key="academics", action="save_student_enrollment")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Program Enrollment", name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Submitted or cancelled Enrollments cannot be edited."), frappe.ValidationError)
	else:
		_require_permission("create")
		doc = frappe.new_doc("Program Enrollment")
	student = str(data.get("student") or "").strip()
	branch = str(data.get(BRANCH_FIELD) or data.get("branch") or "").strip()
	offering = str(data.get(OFFERING_FIELD) or data.get("offering") or "").strip()
	if not student or not branch or not offering:
		frappe.throw(_("Student, Branch and Programme Offering are required."), frappe.ValidationError)
	_student_row_value, branch_row, offering_row = _validate_enrollment_context(student, branch, offering)
	duplicate = frappe.db.exists(
		"Program Enrollment",
		{
			"student": student,
			OFFERING_FIELD: offering,
			"docstatus": ["<", 2],
			"name": ["!=", doc.name or ""],
		},
	)
	if duplicate:
		frappe.throw(
			_("This Student already has an active Enrollment for the selected Programme Offering."),
			frappe.DuplicateEntryError,
		)
	old_program = doc.get("program")
	doc.student = student
	doc.enrollment_date = data.get("enrollment_date") or doc.get("enrollment_date") or nowdate()
	doc.program = offering_row.program
	doc.academic_year = offering_row.academic_year
	doc.academic_term = offering_row.academic_term
	if doc.meta.has_field(BRANCH_FIELD):
		doc.set(BRANCH_FIELD, branch)
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, branch_row.institution)
	if doc.meta.has_field(OFFERING_FIELD):
		doc.set(OFFERING_FIELD, offering)
	if doc.meta.has_field("student_batch_name"):
		doc.student_batch_name = offering_row.student_batch
	for fieldname in ("student_category", "school_house", "boarding_student"):
		if doc.meta.has_field(fieldname) and fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if not name or old_program != offering_row.program:
		doc.set("courses", [])
	doc.save()
	if cint(submit):
		doc.check_permission("submit")
		doc.submit()
	return _enrollment_detail(doc.name)
