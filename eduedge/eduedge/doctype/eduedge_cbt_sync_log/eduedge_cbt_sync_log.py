from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class EduEdgeCBTSyncLog(Document):
	def before_insert(self) -> None:
		self.received_on = self.received_on or now_datetime()
		self.user = self.user or frappe.session.user

	def validate(self) -> None:
		if not self.flags.get("from_cbt_service"):
			frappe.throw(_("CBT sync logs are created only by the sync service."), frappe.PermissionError)
		attempt = frappe.db.get_value(
			"EduEdge CBT Attempt",
			self.attempt,
			["exam", "student", "user", "school_branch"],
			as_dict=True,
		)
		if not attempt:
			frappe.throw(_("CBT Attempt was not found."), frappe.DoesNotExistError)
		for fieldname in ("exam", "student", "user", "school_branch"):
			if self.get(fieldname) != attempt.get(fieldname):
				frappe.throw(_("CBT sync log does not match the attempt {0}.").format(fieldname), frappe.ValidationError)
		if frappe.session.user != "Administrator" and "Student" in frappe.get_roles(frappe.session.user):
			if attempt.user != frappe.session.user:
				frappe.throw(_("Students can only create sync logs for their own CBT Attempt."), frappe.PermissionError)
		counts = [
			cint(self.accepted_count),
			cint(self.duplicate_count),
			cint(self.stale_count),
			cint(self.conflict_count),
			cint(self.rejected_count),
		]
		if any(value < 0 for value in counts) or cint(self.received_count) < 0:
			frappe.throw(_("CBT sync counts cannot be negative."), frappe.ValidationError)
		if sum(counts) != cint(self.received_count):
			frappe.throw(_("CBT sync outcome counts must equal the received answer count."), frappe.ValidationError)

	def on_update(self) -> None:
		if not self.is_new():
			frappe.throw(_("CBT sync audit logs are append-only."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(_("CBT sync audit logs cannot be deleted."), frappe.ValidationError)
