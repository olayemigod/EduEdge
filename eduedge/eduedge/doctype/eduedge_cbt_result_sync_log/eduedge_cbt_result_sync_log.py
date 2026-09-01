from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTResultSyncLog(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, "in_cbt_result_sync_service", False):
			frappe.throw(
				_("CBT Result Sync Logs are maintained only by the governed result-sync service."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Result Sync Logs are append-only audit records and cannot be deleted."),
			frappe.ValidationError,
		)
