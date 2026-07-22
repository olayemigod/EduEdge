from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from eduedge.education.academic_validation import get_offering

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
		self.previous_status = self._current_status()
		self._validate_transition()
		self._derive_target_context()

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Enrollment Status Logs are append-only and cannot be edited."), frappe.PermissionError)
		if not frappe.db.exists("Program Enrollment", self.program_enrollment):
			frappe.throw(_("Select a valid Program Enrollment."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(_("Enrollment Status Logs are append-only and cannot be deleted."), frappe.PermissionError)

	def _current_status(self) -> str:
		latest = frappe.get_all(
			"EduEdge Enrollment Status Log",
			filters={"program_enrollment": self.program_enrollment},
			fields=["new_status"],
			order_by="effective_date desc, creation desc",
			limit=1,
		)
		return latest[0].new_status if latest else "Active"

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

	def _derive_target_context(self) -> None:
		if not self.target_program_offering:
			self.target_branch = None
			return
		offering = get_offering(self.target_program_offering, purpose="enrollment")
		self.target_branch = offering.school_branch
