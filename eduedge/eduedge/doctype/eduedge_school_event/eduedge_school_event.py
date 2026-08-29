from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate

from eduedge.services.branch_context import get_allowed_school_branches


AUDIENCE_SCOPES = {
	"Everyone",
	"Students",
	"Parents / Guardians",
	"Staff",
	"Teachers / Instructors",
	"Specific Class",
	"Specific Class Arm",
	"Specific Programme",
	"Boarding Students",
}
STATUSES = {"Draft", "Scheduled", "Published", "Cancelled", "Completed", "Archived"}


class EduEdgeSchoolEvent(Document):
	def before_insert(self):
		self.status = self.status or "Draft"
		self.organiser = self.organiser or frappe.session.user

	def validate(self):
		self._validate_branch()
		self._validate_academic_context()
		self._validate_dates()
		self._validate_audience()
		self._validate_status()

	def _validate_branch(self):
		if not self.school_branch:
			frappe.throw(_("Select a School Branch / Campus."), frappe.ValidationError)
		allowed = {row.get("name") for row in get_allowed_school_branches()}
		if self.school_branch not in allowed:
			frappe.throw(_("You are not permitted to manage events for the selected School Branch / Campus."), frappe.PermissionError)
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			self.school_branch,
			["institution", "enabled"],
			as_dict=True,
		)
		if not branch or not branch.enabled:
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		self.institution = branch.institution

	def _validate_academic_context(self):
		if not self.academic_year or not frappe.db.exists("Academic Year", self.academic_year):
			frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
		if self.academic_term:
			term_year = frappe.db.get_value("Academic Term", self.academic_term, "academic_year")
			if term_year != self.academic_year:
				frappe.throw(_("The selected Term must belong to the Event Academic Session."), frappe.ValidationError)

	def _validate_dates(self):
		if not self.starts_on or not self.ends_on:
			frappe.throw(_("Set the Event start and end."), frappe.ValidationError)
		start = get_datetime(self.starts_on)
		end = get_datetime(self.ends_on)
		if end < start:
			frappe.throw(_("Event end cannot be earlier than Event start."), frappe.ValidationError)
		year = frappe.db.get_value(
			"Academic Year",
			self.academic_year,
			["year_start_date", "year_end_date"],
			as_dict=True,
		)
		if year and (getdate(start) < getdate(year.year_start_date) or getdate(end) > getdate(year.year_end_date)):
			frappe.throw(_("School Event dates must stay inside the selected Academic Session."), frappe.ValidationError)
		if self.academic_term:
			term = frappe.db.get_value(
				"Academic Term",
				self.academic_term,
				["term_start_date", "term_end_date"],
				as_dict=True,
			)
			if term and (getdate(start) < getdate(term.term_start_date) or getdate(end) > getdate(term.term_end_date)):
				frappe.throw(_("A Term-scoped School Event must stay inside the selected Term dates."), frappe.ValidationError)

	def _validate_audience(self):
		if self.audience_scope not in AUDIENCE_SCOPES:
			frappe.throw(_("Select a valid Event audience."), frappe.ValidationError)
		if self.audience_scope == "Specific Programme" and not self.program:
			frappe.throw(_("Select the Programme for this audience."), frappe.ValidationError)
		if self.audience_scope == "Specific Class" and not self.program:
			frappe.throw(_("Select the Class / Programme for this audience."), frappe.ValidationError)
		if self.audience_scope == "Specific Class Arm" and not self.student_group:
			frappe.throw(_("Select the Class Arm for this audience."), frappe.ValidationError)
		if self.student_group:
			group = frappe.db.get_value(
				"Student Group",
				self.student_group,
				["program", "academic_year", "eduedge_school_branch"],
				as_dict=True,
			)
			if not group or group.academic_year != self.academic_year or group.eduedge_school_branch != self.school_branch:
				frappe.throw(_("The selected Class Arm is outside this Branch or Academic Session."), frappe.ValidationError)
			if self.program and group.program and group.program != self.program:
				frappe.throw(_("The selected Class Arm does not belong to the selected Class / Programme."), frappe.ValidationError)

	def _validate_status(self):
		if self.status not in STATUSES:
			frappe.throw(_("Select a valid School Event status."), frappe.ValidationError)
		if self.status == "Cancelled" and not str(self.cancellation_reason or "").strip():
			frappe.throw(_("Record a cancellation reason before cancelling a School Event."), frappe.ValidationError)
