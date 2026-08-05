from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

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
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Primary operational Branch. Additional eligibility remains governed by background Branch assignments.",
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


def _backfill_instructor_primary_branches() -> None:
	if not (
		frappe.db.exists("DocType", "Instructor")
		and frappe.db.exists("DocType", "EduEdge Instructor Branch Assignment")
		and frappe.get_meta("Instructor").has_field(INSTRUCTOR_PRIMARY_BRANCH_FIELD)
	):
		return
	instructor_meta = frappe.get_meta("Instructor")
	for instructor in frappe.get_all(
		"Instructor",
		filters={INSTRUCTOR_PRIMARY_BRANCH_FIELD: ["is", "not set"]},
		pluck="name",
		limit_page_length=0,
	):
		rows = frappe.get_all(
			"EduEdge Instructor Branch Assignment",
			filters={"instructor": instructor, "enabled": 1},
			fields=["school_branch", "is_primary"],
			order_by="is_primary desc, modified desc",
			limit_page_length=1,
		)
		if not rows or not rows[0].school_branch:
			continue
		values = {INSTRUCTOR_PRIMARY_BRANCH_FIELD: rows[0].school_branch}
		if instructor_meta.has_field(INSTITUTION_FIELD) and not frappe.db.get_value("Instructor", instructor, INSTITUTION_FIELD):
			values[INSTITUTION_FIELD] = frappe.db.get_value(
				"EduEdge School Branch", rows[0].school_branch, "institution"
			)
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
