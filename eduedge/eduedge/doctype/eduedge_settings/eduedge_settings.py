from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class EduEdgeSettings(Document):
	def validate(self) -> None:
		self._validate_capability_enforcement_change()
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

	def _validate_capability_enforcement_change(self) -> None:
		"""Keep the global capability switch behind the readiness workflow."""
		before = self.get_doc_before_save()
		if not before or not self.meta.has_field("enforce_instructor_assignment_capabilities"):
			return
		if cint(before.enforce_instructor_assignment_capabilities) == cint(
			self.enforce_instructor_assignment_capabilities
		):
			return
		if getattr(frappe.flags, "in_eduedge_capability_enforcement_change", False):
			return
		frappe.throw(
			_(
				"Instructor Assignment Capability Enforcement must be changed from EduEdge Settings Center after readiness review."
			),
			frappe.PermissionError,
		)
