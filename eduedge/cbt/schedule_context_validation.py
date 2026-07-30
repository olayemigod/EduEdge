from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.cbt.schedule_governance import (
	OPEN_SCHEDULE_STATUSES,
	TERMINAL_CANDIDATE_STATUSES,
	_assert_no_candidate_overlap,
)

SCHOOL_EXAM = "School Examination"
SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
RESERVED_SCHEDULE_STATUSES = {"Ready", "Active"}
RESERVED_CANDIDATE_STATUSES = {"Eligible", "Checked In", "Released"}


def validate_schedule_academic_scope(doc, method=None) -> None:
	"""Validate Institution context and reject conflicting reserved sittings."""
	if doc.get("exam_scope") == SCHOOL_EXAM and doc.get("school_branch"):
		_validate_academic_master_ownership(doc)
	_validate_schedule_reservation(doc)


def validate_candidate_reservation(doc, method=None) -> None:
	"""Prevent one confirmed candidate from occupying overlapping open sittings."""
	if doc.get("assignment_status") not in RESERVED_CANDIDATE_STATUSES:
		return
	identity_field = "student" if doc.get("student") else "public_candidate_reference"
	identity = doc.get(identity_field)
	if not identity or not doc.get("exam_schedule"):
		return
	schedule = frappe.db.get_value(
		SCHEDULE_DOCTYPE,
		doc.exam_schedule,
		["status", "scheduled_start", "scheduled_end"],
		as_dict=True,
	)
	if not schedule or schedule.status not in OPEN_SCHEDULE_STATUSES:
		return
	other_assignments = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			identity_field: identity,
			"name": ["!=", doc.name or ""],
			"exam_schedule": ["!=", doc.exam_schedule],
			"assignment_status": ["not in", list(TERMINAL_CANDIDATE_STATUSES)],
		},
		fields=["name", "exam_schedule"],
		limit_page_length=1000,
	)
	if not other_assignments:
		return
	conflict = frappe.get_all(
		SCHEDULE_DOCTYPE,
		filters=[
			["name", "in", sorted({row.exam_schedule for row in other_assignments})],
			["status", "in", list(OPEN_SCHEDULE_STATUSES)],
			["scheduled_start", "<", schedule.scheduled_end],
			["scheduled_end", ">", schedule.scheduled_start],
		],
		fields=["name", "schedule_title"],
		limit_page_length=1,
	)
	if conflict:
		row = conflict[0]
		frappe.throw(
			_("This candidate already has an overlapping reserved Examination Schedule: {0} ({1}).").format(
				row.schedule_title or row.name,
				row.name,
			),
			frappe.ValidationError,
		)


def _validate_academic_master_ownership(doc) -> None:
	branch = frappe.db.get_value(
		"EduEdge School Branch",
		doc.school_branch,
		["institution", "company", "enabled"],
		as_dict=True,
	)
	if not branch or not cint(branch.enabled):
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

	for doctype, fieldname, label in (
		("Program", "program", _("Programme")),
		("Assessment Group", "assessment_group", _("Assessment Group")),
	):
		value = doc.get(fieldname)
		if not value:
			continue
		_validate_owned_master(
			doctype=doctype,
			name=value,
			institution=branch.institution,
			company=branch.company,
			label=label,
		)


def _validate_owned_master(
	*,
	doctype: str,
	name: str,
	institution: str | None,
	company: str | None,
	label: str,
) -> None:
	meta = frappe.get_meta(doctype)
	ownership_field = None
	expected = None
	for fieldname, value in (
		("eduedge_institution", institution),
		("institution", institution),
		("company", company),
	):
		if value and meta.has_field(fieldname):
			ownership_field = fieldname
			expected = value
			break
	if not ownership_field:
		frappe.throw(
			_("{0} ownership is not configured for Institution-safe CBT scheduling.").format(label),
			frappe.ValidationError,
		)
	actual = frappe.db.get_value(doctype, name, ownership_field)
	if actual != expected:
		frappe.throw(
			_("The selected {0} does not belong to the Schedule Institution context.").format(label),
			frappe.ValidationError,
		)


def _validate_schedule_reservation(doc) -> None:
	if doc.get("status") not in RESERVED_SCHEDULE_STATUSES:
		return
	if not doc.get("scheduled_start") or not doc.get("scheduled_end"):
		return
	for fieldname, value, label in (
		("examination_centre", doc.get("examination_centre"), _("Examination Centre")),
		("primary_invigilator", doc.get("primary_invigilator"), _("Primary Invigilator")),
	):
		if not value:
			continue
		conflict = frappe.get_all(
			SCHEDULE_DOCTYPE,
			filters=[
				["name", "!=", doc.name or ""],
				["status", "in", list(OPEN_SCHEDULE_STATUSES)],
				[fieldname, "=", value],
				["scheduled_start", "<", doc.scheduled_end],
				["scheduled_end", ">", doc.scheduled_start],
			],
			fields=["name", "schedule_title"],
			limit_page_length=1,
		)
		if conflict:
			row = conflict[0]
			frappe.throw(
				_("{0} is already reserved by {1} ({2}) for an overlapping sitting.").format(
					label,
					row.schedule_title or row.name,
					row.name,
				),
				frappe.ValidationError,
			)
	_validate_schedule_candidate_reservations(doc)


def _validate_schedule_candidate_reservations(doc) -> None:
	assignments = frappe.get_all(
		ASSIGNMENT_DOCTYPE,
		filters={
			"exam_schedule": doc.name,
			"assignment_status": ["in", list(RESERVED_CANDIDATE_STATUSES)],
		},
		fields=["student", "public_candidate_reference"],
		limit_page_length=5000,
	)
	_assert_no_candidate_overlap(
		doc,
		[row.student for row in assignments if row.student],
		[
			row.public_candidate_reference
			for row in assignments
			if row.public_candidate_reference
		],
	)
