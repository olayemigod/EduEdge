from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EduEdgeInstructorBranchAssignment(Document):
	def validate(self) -> None:
		self._validate_branch()
		self._validate_dates()
		self._validate_duplicate()
		self._validate_primary()

	def _validate_branch(self) -> None:
		if not frappe.db.get_value("EduEdge School Branch", self.school_branch, "enabled"):
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)

	def _validate_dates(self) -> None:
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

	def _validate_duplicate(self) -> None:
		duplicate = frappe.db.exists(
			self.doctype,
			{
				"instructor": self.instructor,
				"school_branch": self.school_branch,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Instructor {0} is already assigned to School Branch / Campus {1}.").format(
					self.instructor, self.school_branch
				),
				frappe.DuplicateEntryError,
			)

	def _validate_primary(self) -> None:
		if not self.is_primary or not self.enabled:
			return
		existing = frappe.db.exists(
			self.doctype,
			{
				"instructor": self.instructor,
				"is_primary": 1,
				"enabled": 1,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				_("Instructor {0} already has a primary School Branch assignment.").format(
					self.instructor
				),
				frappe.ValidationError,
			)
