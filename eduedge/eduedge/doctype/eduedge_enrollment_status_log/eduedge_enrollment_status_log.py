from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD, INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.academic_progression import progression_target
from eduedge.education.academic_validation import get_offering
from eduedge.services.enrollment_lifecycle import get_current_enrollment_status

TARGET_STATUSES = {"Promoted", "Repeated", "Transferred"}

ALLOWED_TRANSITIONS = {
	"Active": {"Completed", "Promoted", "Repeated", "Withdrawn", "Suspended", "Held for Review", "Transferred", "Graduated", "Cancelled"},
	"Suspended": {"Active", "Withdrawn", "Held for Review", "Transferred", "Cancelled"},
	"Held for Review": {"Active", "Promoted", "Repeated", "Withdrawn", "Transferred", "Cancelled"},
	"Completed": {"Promoted", "Repeated", "Graduated"},
	"Promoted": set(),
	"Repeated": set(),
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
		if self.new_status in TARGET_STATUSES and not self.target_program_enrollment:
			frappe.throw(_("Target Program Enrollment is required for promotion, repetition or transfer."), frappe.ValidationError)
		if self.new_status not in TARGET_STATUSES and (self.target_program_enrollment or self.target_program_offering):
			frappe.throw(_("A target enrollment is only valid for promotion, repetition or transfer."), frappe.ValidationError)

	def _derive_target_context(self) -> None:
		if not self.target_program_enrollment:
			self.target_branch = None
			self.target_program_offering = None
			return
		target = frappe.get_doc("Program Enrollment", self.target_program_enrollment)
		target.check_permission("read")
		if target.docstatus != 1:
			frappe.throw(_("Target Program Enrollment must be submitted before finalising progression."), frappe.ValidationError)
		if target.student != self._enrollment.student:
			frappe.throw(_("Source and target Program Enrollments must belong to the same Student."), frappe.ValidationError)
		if not target.meta.has_field(OFFERING_FIELD) or not target.get(OFFERING_FIELD):
			frappe.throw(_("Target Program Enrollment must use an exact Programme Offering."), frappe.ValidationError)
		self.target_program_offering = target.get(OFFERING_FIELD)
		offering = get_offering(self.target_program_offering, purpose="enrollment")
		self.target_branch = offering.school_branch
		self._validate_target_transition(target, offering)

	def _validate_target_transition(self, target, offering) -> None:
		source_institution = self._enrollment.get(INSTITUTION_FIELD) if self._enrollment.meta.has_field(INSTITUTION_FIELD) else None
		target_institution = target.get(INSTITUTION_FIELD) if target.meta.has_field(INSTITUTION_FIELD) else offering.institution
		if self.new_status in {"Promoted", "Repeated"} and source_institution and target_institution != source_institution:
			frappe.throw(_("Promotion and repetition must remain within the same Institution."), frappe.ValidationError)

		source_level = self._enrollment.get(ACADEMIC_LEVEL_FIELD) if self._enrollment.meta.has_field(ACADEMIC_LEVEL_FIELD) else None
		target_level = target.get(ACADEMIC_LEVEL_FIELD) if target.meta.has_field(ACADEMIC_LEVEL_FIELD) else offering.get("academic_level")
		if self.new_status == "Promoted":
			expected = progression_target(self._enrollment.program, source_level)
			if not expected.get("program"):
				frappe.throw(_("The source Programme has no configured promotion target."), frappe.ValidationError)
			if target.program != expected.get("program") or target_level != expected.get("academic_level"):
				frappe.throw(_("Target enrollment does not match the configured next Class or Academic Level."), frappe.ValidationError)
			if target.academic_year == self._enrollment.academic_year:
				frappe.throw(_("Promotion target must use a later Academic Session."), frappe.ValidationError)
		elif self.new_status == "Repeated":
			if target.program != self._enrollment.program or target_level != source_level:
				frappe.throw(_("A repeated enrollment must retain the same Programme / Class and Academic Level."), frappe.ValidationError)
			if target.academic_year == self._enrollment.academic_year:
				frappe.throw(_("Repetition target must use a different Academic Session."), frappe.ValidationError)
		elif self.new_status == "Transferred":
			if source_institution and target_institution and target_institution != source_institution:
				frappe.throw(_("Automatic transfer is limited to Branches within the same Institution. Use a new admission for another Institution."), frappe.ValidationError)
