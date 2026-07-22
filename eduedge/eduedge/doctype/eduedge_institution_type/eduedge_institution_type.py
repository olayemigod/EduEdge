from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.institution_types import SEED_UPDATE_FLAG, normalize_institution_type_code


class EduEdgeInstitutionType(Document):
	def before_naming(self) -> None:
		self.institution_type_code = normalize_institution_type_code(self.institution_type_code)

	def validate(self) -> None:
		self.institution_type_code = normalize_institution_type_code(self.institution_type_code)
		if not self.institution_type_code:
			frappe.throw(_("Institution Type Code is required."), frappe.ValidationError)
		if not getattr(frappe.flags, SEED_UPDATE_FLAG, False):
			frappe.throw(
				_("EduEdge Institution Types are system-managed and can only be changed through an EduEdge update."),
				frappe.PermissionError,
			)

	def on_trash(self) -> None:
		if not getattr(frappe.flags, SEED_UPDATE_FLAG, False):
			frappe.throw(
				_("EduEdge Institution Types are system-managed and cannot be deleted."),
				frappe.PermissionError,
			)
