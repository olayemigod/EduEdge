from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.offerings import assert_branch_access

SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"
PLATFORM_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


class EduEdgeExaminationCentre(Document):
	def autoname(self) -> None:
		self.centre_code = (self.centre_code or "").strip().upper()
		if self.centre_code:
			self.name = self.centre_code

	def validate(self) -> None:
		self.centre_code = (self.centre_code or "").strip().upper()
		self.centre_name = (self.centre_name or "").strip()
		self._validate_identity()
		self._validate_scope()
		self._validate_capacity()

	def _validate_identity(self) -> None:
		if not self.centre_code:
			frappe.throw(_("Centre Code is required."), frappe.ValidationError)
		if not self.centre_name:
			frappe.throw(_("Examination Centre Name is required."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.centre_type == SCHOOL_CENTRE:
			if not self.school_branch:
				frappe.throw(
					_("School Branch / Campus is required for a School Examination Centre."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			self.allow_public_registration = 0
			return

		if self.centre_type == PLATFORM_CENTRE:
			self._assert_platform_manager()
			self.school_branch = None
			return

		frappe.throw(_("Select a valid Examination Centre Type."), frappe.ValidationError)

	def _validate_capacity(self) -> None:
		if (self.capacity or 0) < 0:
			frappe.throw(_("Candidate Capacity cannot be negative."), frappe.ValidationError)

	def _assert_platform_manager(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(PLATFORM_MANAGER_ROLES):
			frappe.throw(
				_("Only an EduEdge platform administrator can manage an EduEdge Exam Centre."),
				frappe.PermissionError,
			)
