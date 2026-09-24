from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD

PHOTO_STATUS_FIELD = "eduedge_photo_status"
PHOTO_LOCKED_FIELD = "eduedge_photo_locked"
PHOTO_APPROVED_BY_FIELD = "eduedge_photo_approved_by"
PHOTO_APPROVED_ON_FIELD = "eduedge_photo_approved_on"
PHOTO_REVIEW_NOTE_FIELD = "eduedge_photo_review_note"
INSTRUCTOR_PRIMARY_BRANCH_FIELD = "eduedge_primary_branch"


def _photo_fields(insert_after: str) -> list[dict]:
	return [
		{
			"fieldname": PHOTO_STATUS_FIELD,
			"fieldtype": "Select",
			"label": "Photo Review Status",
			"options": "Pending Review\nApproved\nRejected",
			"default": "Pending Review",
			"read_only": 1,
			"in_standard_filter": 1,
			"insert_after": insert_after,
		},
		{
			"fieldname": PHOTO_LOCKED_FIELD,
			"fieldtype": "Check",
			"label": "Approved Photo Locked",
			"default": 0,
			"read_only": 1,
			"insert_after": PHOTO_STATUS_FIELD,
		},
		{
			"fieldname": PHOTO_APPROVED_BY_FIELD,
			"fieldtype": "Link",
			"label": "Photo Approved By",
			"options": "User",
			"read_only": 1,
			"insert_after": PHOTO_LOCKED_FIELD,
		},
		{
			"fieldname": PHOTO_APPROVED_ON_FIELD,
			"fieldtype": "Datetime",
			"label": "Photo Approved On",
			"read_only": 1,
			"insert_after": PHOTO_APPROVED_BY_FIELD,
		},
		{
			"fieldname": PHOTO_REVIEW_NOTE_FIELD,
			"fieldtype": "Small Text",
			"label": "Photo Review Note",
			"read_only": 1,
			"insert_after": PHOTO_APPROVED_ON_FIELD,
		},
	]


PEOPLE_CUSTOM_FIELDS = {
	"Student Applicant": _photo_fields("image"),
	"Student": _photo_fields("image"),
	"Instructor": [
		{
			"fieldname": INSTRUCTOR_PRIMARY_BRANCH_FIELD,
			"fieldtype": "Link",
			"label": "Primary School Branch / Campus",
			"options": "EduEdge School Branch",
			"insert_after": INSTITUTION_FIELD,
			"read_only": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Compatibility mirror of the current Primary Instructor Branch Eligibility. Manage this in Branch Governance.",
		},
		{
			"fieldname": "eduedge_email",
			"fieldtype": "Data",
			"label": "Instructor Email",
			"options": "Email",
			"insert_after": INSTRUCTOR_PRIMARY_BRANCH_FIELD,
		},
		{
			"fieldname": "eduedge_mobile",
			"fieldtype": "Data",
			"label": "Mobile Number",
			"options": "Phone",
			"insert_after": "eduedge_email",
		},
		{
			"fieldname": "eduedge_qualification",
			"fieldtype": "Small Text",
			"label": "Qualification",
			"insert_after": "eduedge_mobile",
		},
		{
			"fieldname": "eduedge_specialisation",
			"fieldtype": "Small Text",
			"label": "Specialisation",
			"insert_after": "eduedge_qualification",
		},
		{
			"fieldname": "eduedge_employment_type",
			"fieldtype": "Select",
			"label": "Employment Type",
			"options": "\nFull-Time\nPart-Time\nContract\nVisiting\nVolunteer",
			"insert_after": "eduedge_specialisation",
		},
	],
}



def reconcile_instructor_primary_branches() -> dict:
	"""Refresh the current Primary Branch compatibility mirror from dated governance.

	This scheduled reconciliation does not change Home Institution or Branch
	Eligibility. It only keeps the read-only Instructor mirror aligned when a
	future primary period becomes active or a dated primary period expires.
	"""
	if not (
		frappe.db.exists("DocType", "Instructor")
		and frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment")
		and frappe.get_meta("Instructor").has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
	):
		return {"checked": 0, "updated": 0}

	day = getdate(nowdate())
	primary_rows = frappe.get_all(
		"EduEdge Instructor Branch Assignment",
		filters={"enabled": 1, "is_primary": 1},
		fields=["instructor", "school_branch", "valid_from", "valid_to"],
		limit_page_length=0,
	)
	current_by_instructor: dict[str, list[str]] = {}
	for row in primary_rows:
		start = getdate(row.valid_from) if row.valid_from else getdate("1900-01-01")
		end = getdate(row.valid_to) if row.valid_to else getdate("2999-12-31")
		if not (start <= day <= end):
			continue
		instructor = str(row.instructor or "").strip()
		branch = str(row.school_branch or "").strip()
		if instructor and branch:
			current_by_instructor.setdefault(instructor, []).append(branch)

	instructors = frappe.get_all(
		"Instructor",
		fields=["name", INSTRUCTOR_PRIMARY_BRANCH_FIELD],
		limit_page_length=0,
	)
	updated = 0
	for row in instructors:
		candidates = current_by_instructor.get(row.name, [])
		governed_primary = candidates[0] if len(candidates) == 1 else None
		current = row.get(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
		if (current or None) == (governed_primary or None):
			continue
		frappe.db.set_value(
			"Instructor",
			row.name,
			INSTRUCTOR_PRIMARY_BRANCH_FIELD,
			governed_primary,
			update_modified=False,
		)
		updated += 1
	return {"checked": len(instructors), "updated": updated}


def _backfill_instructor_primary_branches() -> None:
	if not (
		frappe.db.exists("DocType", "Instructor")
		and frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment")
		and frappe.get_meta("Instructor").has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
	):
		return

	from eduedge.services.instructor_branch_governance import primary_branch

	instructor_meta = frappe.get_meta("Instructor")
	for instructor in frappe.get_all("Instructor", pluck="name", limit_page_length=0):
		governed_primary = primary_branch(instructor)
		current = frappe.db.get_value("Instructor", instructor, INSTRUCTOR_PRIMARY_BRANCH_FIELD)
		values = {}
		if (current or None) != (governed_primary or None):
			values[INSTRUCTOR_PRIMARY_BRANCH_FIELD] = governed_primary
		if (
			governed_primary
			and instructor_meta.has_field(INSTITUTION_FIELD)
			and not frappe.db.get_value("Instructor", instructor, INSTITUTION_FIELD)
		):
			values[INSTITUTION_FIELD] = frappe.db.get_value(
				"EduEdge School Branch",
				governed_primary,
				"institution",
			)
		if values:
			frappe.db.set_value("Instructor", instructor, values, update_modified=False)


def ensure_people_operations_foundation() -> None:
	available = {
		doctype: fields
		for doctype, fields in PEOPLE_CUSTOM_FIELDS.items()
		if frappe.db.exists("DocType", doctype)
	}
	if available:
		create_custom_fields(available, update=True)
	_backfill_instructor_primary_branches()
