from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTAttemptAnswer(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_answer_sync", False):
			frappe.throw(
				_("CBT answers can be changed only through the idempotent answer-sync service."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(_("CBT answer history cannot be deleted."), frappe.ValidationError)
