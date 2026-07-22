from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_validation import get_offering
from eduedge.services.enrollment_lifecycle import get_current_enrollment_status

ALLOWED_TRANSITIONS = {
	"Active": {"Completed", "Promoted", "Withdrawn", "Suspended", "Transferred", "Graduated", "Cancelled"},
	"Suspended": {"Active", "Withdrawn", "Transferred", "Cancelled"},
	"Completed": {"Promoted", "Graduated"},
	"Promoted": set(),
	"Withdrawn": set(),
	"Transferred": set(),
	"Graduated": set(),
	"Cancelled": set(),
}


class EduEdgeEnrollmentStatusLog(Document):
	def before_insert(self) -> None:
		self.effective_date = self.effective_date or nowdate()
		self.approved_by = frappe.session.user
		self._load_enrollment()
		self.previous_status = get_current_enrollment_status(self.program_enrollment)
		self._validate_chronology()
		self._validate_transition()
		self._derive_target_context()

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Enrollment Status Logs are append-only and cannot be edited."), frappe.PermissionError)
		if not frappe.db.exists("Program Enrollment", self.program_enrollment):
			frappe.throw(_("Select a valid Program Enrollment."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(_("Enrollment Status Logs are append-only and cannot be deleted."), frappe.PermissionError)

	def _load_enrollment(self) -> None:
		# Serialize lifecycle changes for the same enrollment. Without this lock,
		# two simultaneous status logs could both validate against the same prior state.
		frappe.db.sql(
			"select name from `tabProgram Enrollment` where name = %s for update",
			(self.program_enrollment,),
		)
		self._enrollment = frappe.get_doc("Program Enrollment", self.program_enrollment)
		self._enrollment.check_permission("read")
		if self._enrollment.docstatus != 1:
			frappe.throw(_("Enrollment lifecycle changes require a submitted Program Enrollment."), frappe.ValidationError)

	def _latest_log(self) -> frappe._dict | None:
		rows = frappe.get_all(
			"EduEdge Enrollment Status Log",
			filters={"program_enrollment": self.program_enrollment},
			fields=["name", "new_status", "effective_date", "creation"],
			order_by="effective_date desc, creation desc",
			limit=1,
		)
		return rows[0] if rows else None

	def _validate_chronology(self) -> None:
		if getdate(self.effective_date) > getdate(nowdate()):
			frappe.throw(_("Enrollment status changes cannot be future-dated."), frappe.ValidationError)
		latest = self._latest_log()
		if latest and getdate(self.effective_date) < getdate(latest.effective_date):
			frappe.throw(
				_("Effective Date cannot be earlier than the latest status change on {0}.").format(latest.effective_date),
				frappe.ValidationError,
			)

	def _validate_transition(self) -> None:
		if self.new_status == self.previous_status:
			frappe.throw(_("New Status must differ from Previous Status."), frappe.ValidationError)
		allowed = ALLOWED_TRANSITIONS.get(self.previous_status, set())
		if self.new_status not in allowed:
			frappe.throw(
				_("Enrollment cannot move from {0} to {1}.").format(self.previous_status, self.new_status),
				frappe.ValidationError,
			)
		if self.new_status in {"Promoted", "Transferred"} and not self.target_program_offering:
			frappe.throw(_("Target Programme Offering is required for promotion or transfer."), frappe.ValidationError)
		if self.target_program_offering and self._enrollment.meta.has_field(OFFERING_FIELD):
			if self.target_program_offering == self._enrollment.get(OFFERING_FIELD):
				frappe.throw(_("Target Programme Offering must differ from the current Offering."), frappe.ValidationError)

	def _derive_target_context(self) -> None:
		if not self.target_program_offering:
			self.target_branch = None
			return
		offering = get_offering(self.target_program_offering, purpose="enrollment")
		if self.new_status == "Promoted":
			if self._enrollment.meta.has_field(INSTITUTION_FIELD):
				source_institution = self._enrollment.get(INSTITUTION_FIELD)
				if source_institution and offering.institution != source_institution:
					frappe.throw(_("Promotion must remain within the same Institution. Use Transfer for another Institution."), frappe.ValidationError)
			if self._enrollment.meta.has_field(ACADEMIC_LEVEL_FIELD):
				source_level = self._enrollment.get(ACADEMIC_LEVEL_FIELD)
				next_level = frappe.db.get_value("EduEdge Academic Level", source_level, "next_level") if source_level else None
				if next_level and offering.academic_level != next_level:
					frappe.throw(
						_("Promotion target must use the configured next Academic Level {0}.").format(next_level),
						frappe.ValidationError,
					)
		self.target_branch = offering.school_branch
