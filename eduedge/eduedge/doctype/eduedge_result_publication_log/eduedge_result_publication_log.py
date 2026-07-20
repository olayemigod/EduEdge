from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeResultPublicationLog(Document):
	def before_insert(self) -> None:
		if not self.acted_by:
			self.acted_by = frappe.session.user
		if not self.acted_on:
			self.acted_on = frappe.utils.now_datetime()

	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Result Publication logs are append-only."), frappe.ValidationError)
