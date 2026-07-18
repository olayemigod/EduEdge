from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeSettings(Document):
	def validate(self) -> None:
		if not self.default_school_branch:
			return
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			self.default_school_branch,
			["company", "enabled"],
			as_dict=True,
		)
		if not branch or not branch.enabled:
			frappe.throw(_("Default School Branch must be enabled."))
		if self.default_company and branch.company != self.default_company:
			frappe.throw(_("Default School Branch must belong to the Default Company."))
