from __future__ import annotations

from typing import Any

import filetype
import frappe
from frappe import _
from frappe.utils import cint, now_datetime, nowdate

from eduedge.api.fuzzy_search import CANDIDATE_LIMIT, rank_link_rows
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


def _rank_student_rows(rows: list[dict], search: str, start: int, length: int) -> tuple[list[dict], bool]:
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("student_name") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("student_email_id"),
				row.get("student_mobile_number"),
				row.get("first_name"),
				row.get("last_name"),
			)
			if value
		)
		candidates.append(row)
	ranked = rank_link_rows(
		candidates,
		search,
		exact_fields=("value", "student_mobile_number", "student_email_id"),
		search_fields=("label", "description"),
		start=0,
		page_length=CANDIDATE_LIMIT,
	)
	has_more = start + length < len(ranked)
	return ranked[start : start + length], has_more


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
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	search = str(search or "").strip()
	fields = _row_fields(
		"Student",
		[
			"name", "student_name", "first_name", "last_name", "image", BRANCH_FIELD,
			"student_email_id", "student_mobile_number", "joining_date", "enabled",
			PHOTO_STATUS_FIELD, PHOTO_LOCKED_FIELD,
		],
	)
	if search:
		candidate_rows = frappe.get_list(
			"Student",
			filters=filters,
			fields=fields,
			order_by="student_name asc",
			page_length=CANDIDATE_LIMIT,
		)
		rows, has_more = _rank_student_rows(candidate_rows, search, start, length)
	else:
		rows = frappe.get_list(
			"Student",
			filters=filters,
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
	_append_photo_log(doc, "Upload", old_image, file_url)
	return _student_detail(doc.name) if reference_doctype == "Student" else doc.as_dict(no_nulls=False)


@frappe.whitelist(methods=["POST"])
def review_student_photo(reference_doctype: str, reference_name: str, decision: str, note: str | None = None) -> dict:
	require_eduedge_access(feature_key="academics", action="review_student_photo")
	_require_people_manager()
	if reference_doctype not in {"Student Applicant", "Student"}:
		frappe.throw(_("Invalid student photo target."), frappe.ValidationError)
	doc = frappe.get_doc(reference_doctype, reference_name)
	doc.check_permission("write")
	decision = str(decision or "").strip().title()
	if decision not in {"Approve", "Reject", "Unlock"}:
		frappe.throw(_("Select Approve, Reject, or Unlock."), frappe.ValidationError)
	old_image = doc.get("image")
	if decision == "Approve":
		if not old_image:
			frappe.throw(_("Upload a profile photo before approval."), frappe.ValidationError)
		_validate_private_image(old_image, reference_doctype, reference_name)
		doc.set(PHOTO_STATUS_FIELD, "Approved")
		doc.set(PHOTO_LOCKED_FIELD, 1)
		doc.set(PHOTO_APPROVED_BY_FIELD, frappe.session.user)
		doc.set(PHOTO_APPROVED_ON_FIELD, now_datetime())
		doc.set(PHOTO_REVIEW_NOTE_FIELD, note)
	elif decision == "Reject":
		doc.set("image", None)
		doc.set(PHOTO_STATUS_FIELD, "Rejected")
		doc.set(PHOTO_LOCKED_FIELD, 0)
		doc.set(PHOTO_APPROVED_BY_FIELD, frappe.session.user)
		doc.set(PHOTO_APPROVED_ON_FIELD, now_datetime())
		doc.set(PHOTO_REVIEW_NOTE_FIELD, note)
	else:
		doc.set(PHOTO_LOCKED_FIELD, 0)
		doc.set(PHOTO_STATUS_FIELD, "Pending Review" if old_image else "Not Uploaded")
		doc.set(PHOTO_REVIEW_NOTE_FIELD, note)
	doc.save()
	_append_photo_log(doc, decision, old_image, doc.get("image"), note)
	return _student_detail(doc.name) if reference_doctype == "Student" else doc.as_dict(no_nulls=False)


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
	filters: dict[str, Any] = {INSTRUCTOR_PRIMARY_BRANCH_FIELD: resolved}
	or_filters = None
	if str(search or "").strip():
		needle = f"%{str(search).strip()}%"
		or_filters = {
			"name": ["like", needle],
			"instructor_name": ["like", needle],
			"eduedge_email": ["like", needle],
			"eduedge_mobile": ["like", needle],
			"department": ["like", needle],
		}
	length = min(max(cint(page_length), 1), MAX_PAGE_LENGTH)
	start = max(cint(start), 0)
	fields = _row_fields(
		"Instructor",
		[
			"name", "instructor_name", "image", "status", "department", "employee", INSTITUTION_FIELD,
			INSTRUCTOR_PRIMARY_BRANCH_FIELD, "eduedge_email", "eduedge_mobile", "eduedge_qualification",
			"eduedge_specialisation", "eduedge_employment_type",
			PHOTO_STATUS_FIELD, PHOTO_LOCKED_FIELD,
		],
	)
	rows = frappe.get_list(
		"Instructor",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="instructor_name asc",
		start=start,
		page_length=length + 1,
	)
	has_more = len(rows) > length
	rows = rows[:length]
	return {
		"allowed_branches": allowed,
		"selected_branch": selected,
		"instructors": rows,
		"instructor": _instructor_detail(instructor) if instructor else None,
		"options": _standard_options(),
		"permissions": {
			"can_create": frappe.has_permission("Instructor", "create"),
			"can_write": frappe.has_permission("Instructor", "write"),
			"can_manage_photo": bool(PEOPLE_MANAGER_ROLES.intersection(frappe.get_roles())),
		},
		"paging": {"start": start, "page_length": length, "has_more": has_more},
	}


def _instructor_detail(name: str) -> dict:
	doc = frappe.get_doc("Instructor", name)
	doc.check_permission("read")
	result = doc.as_dict(no_nulls=False)
	result["assignment_count"] = frappe.db.count("EduEdge Instructor Assignment", {"instructor": name, "enabled": 1}) if frappe.db.exists("DocType", "EduEdge Instructor Assignment") else 0
	return result


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
	for fieldname in INSTRUCTOR_FIELDS:
		if doc.meta.has_field(fieldname) and fieldname in data:
			doc.set(fieldname, data.get(fieldname))
	branch = str(data.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD) or "").strip()
	if not branch:
		frappe.throw(_("Primary School Branch / Campus is required."), frappe.ValidationError)
	assert_branch_access(branch)
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if doc.meta.has_field(INSTITUTION_FIELD):
		doc.set(INSTITUTION_FIELD, institution)
	if not doc.instructor_name:
		frappe.throw(_("Instructor Name is required."), frappe.ValidationError)
	doc.save()
	return _instructor_detail(doc.name)
