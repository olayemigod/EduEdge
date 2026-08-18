from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTAttemptReview(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_attempt_review_service", False):
			frappe.throw(
				_("CBT Attempt Reviews are created only through the governed review service."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Attempt Reviews are append-only and cannot be deleted."),
			frappe.ValidationError,
		)
