from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeCBTLifecycleLog(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(
				_("CBT Lifecycle Logs are append-only and cannot be edited."),
				frappe.ValidationError,
			)
		if not getattr(self.flags, "eduedge_internal_lifecycle_log", False):
			frappe.throw(
				_("CBT Lifecycle Logs are created only by authorised Schedule and Candidate lifecycle actions."),
				frappe.PermissionError,
			)
		for fieldname, label in (
			("reference_doctype", _("Reference DocType")),
			("reference_name", _("Reference Record")),
			("exam_schedule", _("Examination Schedule")),
			("event_type", _("Event Type")),
			("to_status", _("To Status")),
			("reason", _("Reason")),
			("acted_by", _("Acted By")),
			("acted_on", _("Acted On")),
		):
			if not self.get(fieldname):
				frappe.throw(_("{0} is required.").format(label), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Lifecycle Logs are append-only and cannot be deleted."),
			frappe.ValidationError,
		)
