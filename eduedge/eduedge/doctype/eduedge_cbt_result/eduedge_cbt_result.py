from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTResult(Document):
	def validate(self) -> None:
		if not (
			getattr(frappe.flags, "in_cbt_result_service", False)
			or getattr(frappe.flags, "in_cbt_result_sync_service", False)
		):
			frappe.throw(
				_("CBT Results are maintained only through the governed scoring, marking and result-sync services."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Results are immutable audit records and cannot be deleted."),
			frappe.ValidationError,
		)
