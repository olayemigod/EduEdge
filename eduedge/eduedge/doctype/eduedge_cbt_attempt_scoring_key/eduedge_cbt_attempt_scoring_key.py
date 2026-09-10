from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTAttemptScoringKey(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_attempt_service", False):
			frappe.throw(
				_("Attempt scoring keys are created only by the CBT attempt service."),
				frappe.PermissionError,
			)
		if not self.is_new():
			frappe.throw(_("Attempt scoring keys are immutable."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(
			_("Attempt scoring keys are immutable and cannot be deleted."),
			frappe.ValidationError,
		)
