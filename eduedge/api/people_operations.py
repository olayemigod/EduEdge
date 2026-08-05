from __future__ import annotations

from typing import Any

import filetype
import frappe
from frappe import _
from frappe.utils import cint, now_datetime, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.people_fields import (
	INSTRUCTOR_PRIMARY_BRANCH_FIELD,
	PHOTO_APPROVED_BY_FIELD,
	PHOTO_APPROVED_ON_FIELD,
	PHOTO_LOCKED_FIELD,
	PHOTO_REVIEW_NOTE_FIELD,
	PHOTO_STATUS_FIELD,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_PAGE_LENGTH = 50
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}
PEOPLE_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Registrar",
	"Admission Officer",
	"School HR Officer",
	"Education Manager",
}
STUDENT_FIELDS = (
	"enabled",
	"first_name",
	"middle_name",
	"last_name",
	BRANCH_FIELD,
	"joining_date",
	"student_email_id",
	"student_mobile_number",
	"date_of_birth",
	"blood_group",
	"gender",
	"nationality",
	"address_line_1",
	"address_line_2",
	"city",
	"state",
	"pincode",
	"country",
)
INSTRUCTOR_FIELDS = (
	"instructor_name",
	"employee",
	"gender",
	"status",
	"department",
	INSTITUTION_FIELD,
	INSTRUCTOR_PRIMARY_BRANCH_FIELD,
	"eduedge_email",
	"eduedge_mobile",
	"eduedge_qualification",
	"eduedge_specialisation",
	"eduedge_employment_type",
)


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(doctype: str, permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission(doctype, permission_type):
		frappe.throw(
			_("You are not permitted to {0} {1} records.").format(permission_type, doctype),
			frappe.PermissionError,
		)


def _require_people_manager() -> None:
	_require_login()
	if not PEOPLE_MANAGER_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only authorised school staff can manage official profile photos."), frappe.PermissionError)


def _parse_payload(payload: str | dict | None) -> dict:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("A valid request payload is required."), frappe.ValidationError)
	return payload


def _allowed_branches() -> list[dict]:
	rows = get_allowed_school_branches() or []
	result: list[dict] = []
	for source in rows:
		row = dict(source)
		if not row.get("name"):
			continue
		if not row.get("branch_name") or not row.get("institution"):
			details = frappe.db.get_value(
				"EduEdge School Branch",
				row["name"],
				["branch_name", "institution", "enabled"],
				as_dict=True,
			) or {}
			row.update(details)
		if not cint(row.get("enabled", 1)):
			continue
		if row.get("institution") and not row.get("institution_name"):
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


def _standard_options() -> dict:
	return {
		"genders": frappe.get_list("Gender", fields=["name"], order_by="name asc", limit_page_length=100),
		"countries": frappe.get_list("Country", fields=["name"], order_by="name asc", limit_page_length=300),
		"blood_groups": ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
	}


def _student_detail(name: str) -> dict:
	doc = frappe.get_doc("Student", name)
	doc.check_permission("read")
	result = doc.as_dict(no_nulls=False)
	result["guardians"] = [
		{"guardian": row.guardian, "guardian_name": row.guardian_name, "relation": row.relation}
		for row in doc.get("guardians") or []
	]
	result["enrollments"] = frappe.get_list(
		"Program Enrollment",
		filters={"student": doc.name, "docstatus": 1},
		fields=_row_fields(
			"Program Enrollment",
			["name", "program", "academic_year", "academic_term", OFFERING_FIELD, BRANCH_FIELD],
		),
		order_by="creation desc",
		limit_page_length=20,
	)
	group_rows = frappe.get_all(
		"Student Group Student",
		filters={"student": doc.name, "active": 1, "parenttype": "Student Group"},
		fields=["parent", "group_roll_number"],
		limit_page_length=50,
	)
	group_names = [row.parent for row in group_rows]
	group_map = {
		row.name: row
		for row in frappe.get_list(
			"Student Group",
			filters={"name": ["in", group_names]},
			fields=_row_fields(
				"Student Group",
				["name", "student_group_name", "eduedge_display_name", "program", "academic_year", "academic_term", BRANCH_FIELD],
			),
			limit_page_length=max(len(group_names), 1),
		)
	} if group_names else {}
	result["class_arms"] = [
		{
			**dict(group_map.get(row.parent) or {"name": row.parent}),
			"group_roll_number": row.group_roll_number,
		}
		for row in group_rows
	]
	return result


@frappe.whitelist()
def get_students_page(
	branch: str | None = None,
	search: str | None = None,
	student: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	_require_permission("Student", "read")
	resolved, selected, allowed = _resolve_branch(branch)
	filters: dict[str, Any] = {BRANCH_FIELD: resolved}
	or_filters = None
	if str(search or "").strip():
		needle = f"%{str(search).strip()}%"
		or_filters = {
			"name": ["like", needle],
			"student_name": ["like", needle],
			"student_email_id": ["like", needle],
			"student_mobile_number": ["like", needle],
		}
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	fields = _row_fields(
		"Student",
		[
			"name", "student_name", "first_name", "last_name", "image", BRANCH_FIELD,
			"student_email_id", "student_mobile_number", "joining_date", "enabled",
			PHOTO_STATUS_FIELD, PHOTO_LOCKED_FIELD,
		],
	)
	rows = frappe.get_list(
		"Student",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="student_name asc",
		start=start,
		page_length=length + 1,
	)
	has_more = len(rows) > length
	rows = rows[:length]
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"students": rows,
		"student": _student_detail(student) if student else None,
		"guardians": frappe.get_list(
			"Guardian",
			fields=["name", "guardian_name", "mobile_number", "email_address"],
			order_by="guardian_name asc",
			limit_page_length=300,
		) if frappe.has_permission("Guardian", "read") else [],
		"options": _standard_options(),
		"permissions": {
			"can_create": frappe.has_permission("Student", "create"),
			"can_write": frappe.has_permission("Student", "write"),
			"can_manage_photo": bool(PEOPLE_MANAGER_ROLES.intersection(frappe.get_roles())),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


@frappe.whitelist(methods=["POST"])
def save_student(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_student")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Student", name)
		doc.check_permission("write")
	else:
		_require_permission("Student", "create")
		doc = frappe.new_doc("Student")
		doc.naming_series = data.get("naming_series") or "EDU-STU-.YYYY.-"
	branch = str(data.get(BRANCH_FIELD) or "").strip()
	if not branch:
		frappe.throw(_("School Branch / Campus is required."), frappe.ValidationError)
	assert_branch_access(branch)
	for fieldname in STUDENT_FIELDS:
		if doc.meta.has_field(fieldname) and fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if not doc.first_name:
		frappe.throw(_("First Name is required."), frappe.ValidationError)
	guardians = data.get("guardians") or []
	if not isinstance(guardians, list):
		frappe.throw(_("Guardians must be supplied as a list."), frappe.ValidationError)
	doc.set("guardians", [])
	seen: set[str] = set()
	for row in guardians:
		guardian = str((row or {}).get("guardian") or "").strip()
		if not guardian or guardian in seen:
			continue
		seen.add(guardian)
		doc.append("guardians", {"guardian": guardian, "relation": (row or {}).get("relation")})
	doc.save()
	return _student_detail(doc.name)


def _validate_private_image(file_url: str, doctype: str, name: str) -> frappe._dict:
	file_row = frappe.db.get_value(
		"File",
		{"file_url": file_url},
		["name", "file_name", "file_size", "is_private", "attached_to_doctype", "attached_to_name"],
		as_dict=True,
	)
	if not file_row:
		frappe.throw(_("Uploaded image could not be found."), frappe.ValidationError)
	if not file_row.is_private:
		frappe.throw(_("Student and Instructor photos must be private files."), frappe.ValidationError)
	if file_row.attached_to_doctype != doctype or file_row.attached_to_name != name:
		frappe.throw(_("Uploaded image is not attached to the selected record."), frappe.PermissionError)
	if cint(file_row.file_size) > MAX_IMAGE_BYTES:
		frappe.throw(_("Profile photos must not exceed 2 MB."), frappe.ValidationError)
	file_doc = frappe.get_doc("File", file_row.name)
	content = file_doc.get_content()
	if isinstance(content, str):
		content = content.encode()
	kind = filetype.guess(bytes(content or b""))
	if not kind or kind.mime not in ALLOWED_IMAGE_MIMETYPES:
		frappe.throw(_("Only genuine JPG, PNG, and WebP images are allowed."), frappe.ValidationError)
	return file_row


def _photo_context(doc) -> tuple[str | None, str | None, str | None]:
	if doc.doctype == "Student":
		return doc.name, doc.get("student_applicant"), doc.get(BRANCH_FIELD)
	student = frappe.db.get_value("Student", {"student_applicant": doc.name}, "name")
	return student, doc.name, doc.get(BRANCH_FIELD)


def _append_photo_log(doc, decision: str, old_image: str | None, new_image: str | None, note: str | None = None) -> None:
	student, applicant, branch = _photo_context(doc)
	frappe.get_doc(
		{
			"doctype": "EduEdge Student Photo Review Log",
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"student": student,
			"student_applicant": applicant,
			"school_branch": branch,
			"decision": decision,
			"old_image": old_image,
			"new_image": new_image,
			"review_note": note,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now_datetime(),
		}
	).insert()


@frappe.whitelist(methods=["POST"])
def set_student_photo(reference_doctype: str, reference_name: str, file_url: str) -> dict:
	require_eduedge_access(feature_key="academics", action="set_student_photo")
	_require_people_manager()
	if reference_doctype not in {"Student Applicant", "Student"}:
		frappe.throw(_("Invalid student photo target."), frappe.ValidationError)
	doc = frappe.get_doc(reference_doctype, reference_name)
	doc.check_permission("write")
	if doc.meta.has_field(BRANCH_FIELD) and doc.get(BRANCH_FIELD):
		assert_branch_access(doc.get(BRANCH_FIELD))
	_validate_private_image(file_url, reference_doctype, reference_name)
	old_image = doc.get("image")
	doc.image = file_url
	if doc.meta.has_field(PHOTO_STATUS_FIELD):
		doc.set(PHOTO_STATUS_FIELD, "Pending Review")
		doc.set(PHOTO_LOCKED_FIELD, 0)
		doc.set(PHOTO_APPROVED_BY_FIELD, None)
		doc.set(PHOTO_APPROVED_ON_FIELD, None)
		doc.set(PHOTO_REVIEW_NOTE_FIELD, None)
	doc.save()
	_append_photo_log(doc, "Replaced" if old_image else "Uploaded", old_image, file_url)
	return doc.as_dict(no_nulls=False)


@frappe.whitelist(methods=["POST"])
def review_student_photo(reference_doctype: str, reference_name: str, decision: str, note: str | None = None) -> dict:
	require_eduedge_access(feature_key="academics", action="review_student_photo")
	_require_people_manager()
	if reference_doctype not in {"Student Applicant", "Student"} or decision not in {"Approved", "Rejected"}:
		frappe.throw(_("Invalid photo review request."), frappe.ValidationError)
	doc = frappe.get_doc(reference_doctype, reference_name)
	doc.check_permission("write")
	if not doc.get("image"):
		frappe.throw(_("Upload a photo before completing review."), frappe.ValidationError)
	if doc.meta.has_field(BRANCH_FIELD) and doc.get(BRANCH_FIELD):
		assert_branch_access(doc.get(BRANCH_FIELD))
	doc.set(PHOTO_STATUS_FIELD, decision)
	doc.set(PHOTO_LOCKED_FIELD, 1 if decision == "Approved" else 0)
	doc.set(PHOTO_APPROVED_BY_FIELD, frappe.session.user if decision == "Approved" else None)
	doc.set(PHOTO_APPROVED_ON_FIELD, now_datetime() if decision == "Approved" else None)
	doc.set(PHOTO_REVIEW_NOTE_FIELD, note)
	doc.save()
	_append_photo_log(doc, decision, doc.image, doc.image, note)

	if reference_doctype == "Student Applicant" and decision == "Approved":
		student_name = frappe.db.get_value("Student", {"student_applicant": doc.name}, "name")
		if student_name:
			student = frappe.get_doc("Student", student_name)
			student.check_permission("write")
			old_image = student.image
			student.image = doc.image
			student.set(PHOTO_STATUS_FIELD, "Approved")
			student.set(PHOTO_LOCKED_FIELD, 1)
			student.set(PHOTO_APPROVED_BY_FIELD, frappe.session.user)
			student.set(PHOTO_APPROVED_ON_FIELD, now_datetime())
			student.set(PHOTO_REVIEW_NOTE_FIELD, note)
			student.save()
			_append_photo_log(student, "Approved", old_image, student.image, _("Copied from approved admission application."))
	return doc.as_dict(no_nulls=False)


def _instructor_detail(name: str) -> dict:
	doc = frappe.get_doc("Instructor", name)
	doc.check_permission("read")
	result = doc.as_dict(no_nulls=False)
	result["assignments"] = frappe.get_list(
		"EduEdge Instructor Assignment",
		filters={"instructor": doc.name},
		fields=["name", "assignment_title", "school_branch", "program_offering", "student_group", "course", "assignment_type", "enabled"],
		order_by="modified desc",
		limit_page_length=50,
	) if frappe.db.exists("DocType", "EduEdge Instructor Assignment") else []
	return result


@frappe.whitelist()
def get_instructors_page(
	branch: str | None = None,
	search: str | None = None,
	instructor: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	_require_permission("Instructor", "read")
	resolved, selected, allowed = _resolve_branch(branch)
	institution = selected.get("institution")
	filters: dict[str, Any] = {}
	meta = frappe.get_meta("Instructor")
	if meta.has_field(INSTITUTION_FIELD):
		filters[INSTITUTION_FIELD] = institution
	if meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
		filters[INSTRUCTOR_PRIMARY_BRANCH_FIELD] = resolved
	or_filters = None
	if str(search or "").strip():
		needle = f"%{str(search).strip()}%"
		or_filters = {"name": ["like", needle], "instructor_name": ["like", needle]}
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	rows = frappe.get_list(
		"Instructor",
		filters=filters,
		or_filters=or_filters,
		fields=_row_fields(
			"Instructor",
			["name", "instructor_name", "employee", "department", "status", "image", INSTITUTION_FIELD, INSTRUCTOR_PRIMARY_BRANCH_FIELD, "eduedge_email", "eduedge_mobile"],
		),
		order_by="instructor_name asc",
		start=start,
		page_length=length + 1,
	)
	has_more = len(rows) > length
	rows = rows[:length]
	departments = frappe.get_list(
		"Department",
		filters={INSTITUTION_FIELD: institution} if frappe.get_meta("Department").has_field(INSTITUTION_FIELD) else {},
		fields=["name", "department_name"],
		order_by="department_name asc",
		limit_page_length=300,
	)
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"instructors": rows,
		"instructor": _instructor_detail(instructor) if instructor else None,
		"departments": departments,
		"employees": frappe.get_list("Employee", filters={"status": "Active"}, fields=["name", "employee_name", "department", "gender"], order_by="employee_name asc", limit_page_length=500) if frappe.db.exists("DocType", "Employee") and frappe.has_permission("Employee", "read") else [],
		"genders": _standard_options()["genders"],
		"permissions": {
			"can_create": frappe.has_permission("Instructor", "create"),
			"can_write": frappe.has_permission("Instructor", "write"),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


def _ensure_branch_eligibility(instructor: str, branch: str) -> None:
	assignment_name = frappe.db.get_value(
		"EduEdge Instructor Branch Assignment",
		{"instructor": instructor, "school_branch": branch},
		"name",
	)
	for other in frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"instructor": instructor, "is_primary": 1, "name": ["!=", assignment_name or ""]},
		pluck="name",
	):
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", other)
		doc.check_permission("write")
		doc.is_primary = 0
		doc.save()
	if assignment_name:
		doc = frappe.get_doc("EduEdge Instructor Branch Assignment", assignment_name)
		doc.check_permission("write")
	else:
		_require_permission("EduEdge Instructor Branch Assignment", "create")
		doc = frappe.new_doc("EduEdge Instructor Branch Assignment")
		doc.instructor = instructor
		doc.school_branch = branch
	doc.enabled = 1
	doc.is_primary = 1
	doc.valid_from = doc.valid_from or nowdate()
	doc.save()


@frappe.whitelist(methods=["POST"])
def save_instructor(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_instructor")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("Instructor", name)
		doc.check_permission("write")
	else:
		_require_permission("Instructor", "create")
		doc = frappe.new_doc("Instructor")
		doc.naming_series = data.get("naming_series") or "EDU-INS-.YYYY.-"
	branch = str(data.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD) or "").strip()
	if not branch:
		frappe.throw(_("Primary School Branch / Campus is required."), frappe.ValidationError)
	assert_branch_access(branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	for fieldname in INSTRUCTOR_FIELDS:
		if doc.meta.has_field(fieldname) and fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, institution)
	if doc.meta.has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD):
		doc.set(INSTRUCTOR_PRIMARY_BRANCH_FIELD, branch)
	if not doc.instructor_name:
		frappe.throw(_("Instructor Name is required."), frappe.ValidationError)
	doc.save()
	_ensure_branch_eligibility(doc.name, branch)
	return _instructor_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def set_instructor_photo(instructor: str, file_url: str) -> dict:
	require_eduedge_access(feature_key="academics", action="set_instructor_photo")
	_require_people_manager()
	doc = frappe.get_doc("Instructor", instructor)
	doc.check_permission("write")	
	_validate_private_image(file_url, "Instructor", instructor)
	doc.image = file_url
	doc.save()
	return _instructor_detail(doc.name)


def _assignment_options(branch: str, offering: str | None = None, student_group: str | None = None) -> dict:
	resolved, selected, allowed = _resolve_branch(branch)
	institution = selected.get("institution")
	offering_filters = {"school_branch": resolved, "is_active": 1}
	offerings = frappe.get_list(
		"EduEdge Program Offering",
		filters=offering_filters,
		fields=["name", "offering_title", "program", "academic_year", "academic_term", "institution"],
		order_by="academic_year desc, offering_title asc",
		limit_page_length=300,
	)
	selected_offering = next((row for row in offerings if row.name == offering), None)
	group_filters: dict[str, Any] = {BRANCH_FIELD: resolved, "disabled": 0}
	if offering and frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
		group_filters[OFFERING_FIELD] = offering
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=_row_fields("Student Group", ["name", "student_group_name", "eduedge_display_name", "program", "academic_year", "academic_term", OFFERING_FIELD]),
		order_by="student_group_name asc",
		limit_page_length=300,
	)
	selected_group = next((row for row in groups if row.name == student_group), None)
	program = (selected_offering or {}).get("program") or (selected_group or {}).get("program")
	courses = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		fields=["course"],
		order_by="idx asc",
		limit_page_length=300,
	) if program else []
	eligible_names = frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"school_branch": resolved, "enabled": 1},
		pluck="instructor",
		limit_page_length=500,
	)
	instructor_filters: dict[str, Any] = {"name": ["in", eligible_names], "status": "Active"}
	if frappe.get_meta("Instructor").has_field(INSTITUTION_FIELD):
		instructor_filters[INSTITUTION_FIELD] = institution
	instructors = frappe.get_list(
		"Instructor",
		filters=instructor_filters,
		fields=["name", "instructor_name", "department"],
		order_by="instructor_name asc",
		limit_page_length=500,
	) if eligible_names else []
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"offerings": offerings,
		"groups": groups,
		"courses": courses,
		"instructors": instructors,
		"selected_offering": selected_offering,
		"selected_group": selected_group,
	}


@frappe.whitelist()
def get_instructor_assignment_options(branch: str, offering: str | None = None, student_group: str | None = None) -> dict:
	_require_permission("EduEdge Instructor Assignment", "read")
	return _assignment_options(branch, offering, student_group)


@frappe.whitelist()
def get_instructor_assignments_page(
	branch: str | None = None,
	offering: str | None = None,
	student_group: str | None = None,
	assignment: str | None = None,
) -> dict:
	_require_permission("EduEdge Instructor Assignment", "read")
	resolved, _, _ = _resolve_branch(branch)
	options = _assignment_options(resolved, offering, student_group)
	filters: dict[str, Any] = {"school_branch": resolved}
	if offering:
		filters["program_offering"] = offering
	if student_group:
		filters["student_group"] = student_group
	rows = frappe.get_list(
		"EduEdge Instructor Assignment",
		filters=filters,
		fields=["name", "assignment_title", "instructor", "instructor_name", "assignment_type", "program_offering", "student_group", "course", "academic_year", "academic_term", "enabled", "valid_from", "valid_to"],
		order_by="modified desc",
		limit_page_length=300,
	)
	selected = None
	if assignment:
		doc = frappe.get_doc("EduEdge Instructor Assignment", assignment)
		doc.check_permission("read")
		selected = doc.as_dict(no_nulls=False)
	return {
		**options,
		"assignments": rows,
		"assignment": selected,
		"permissions": {
			"can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
			"can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
		},
	}


@frappe.whitelist(methods=["POST"])
def save_instructor_assignment(payload: str | dict) -> dict:
	require_eduedge_access(feature_key="academics", action="save_instructor_assignment")
	data = _parse_payload(payload)
	name = str(data.get("name") or "").strip()
	if name:
		doc = frappe.get_doc("EduEdge Instructor Assignment", name)
		doc.check_permission("write")
	else:
		_require_permission("EduEdge Instructor Assignment", "create")
		doc = frappe.new_doc("EduEdge Instructor Assignment")
	for fieldname in (
		"instructor", "assignment_type", "enabled", "school_branch", "program_offering",
		"student_group", "course", "valid_from", "valid_to", "notes",
	):
		if fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	doc.save()
	return doc.as_dict(no_nulls=False)
