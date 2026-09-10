from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTAttempt(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_attempt_service", False):
			frappe.throw(
				_("CBT Attempts are controlled by the attempt service and cannot be edited directly."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Attempts are audit records and cannot be deleted."),
			frappe.ValidationError,
		)
