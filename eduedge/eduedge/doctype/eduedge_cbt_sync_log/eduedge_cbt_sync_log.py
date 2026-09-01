from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTSyncLog(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_answer_sync", False):
			frappe.throw(
				_("CBT Sync Logs are created only by the answer-sync service."),
				frappe.PermissionError,
			)
		if not self.is_new():
			frappe.throw(_("CBT Sync Logs are append-only and cannot be edited."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Sync Logs are append-only and cannot be deleted."),
			frappe.ValidationError,
		)
