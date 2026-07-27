from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTMarkingLog(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_result_service", False):
			frappe.throw(
				_("CBT Marking Logs are created only by the governed marking service."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Marking Logs are append-only and cannot be deleted."),
			frappe.ValidationError,
		)
