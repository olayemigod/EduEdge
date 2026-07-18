from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.assessment_operations import validate_publication_scope


class EduEdgeResultPublication(Document):
	def before_naming(self) -> None:
		if not self.title:
			parts = [self.student_group, self.assessment_group, self.academic_term or self.academic_year]
			self.title = " · ".join(part for part in parts if part)

	def validate(self) -> None:
		validate_publication_scope(self)
		self._validate_scope_change()
		self._validate_duplicate_scope()

	def on_trash(self) -> None:
		if self.status != "Draft":
			frappe.throw(
				_("Only Draft Result Publications can be deleted."),
				frappe.ValidationError,
			)

	def _validate_scope_change(self) -> None:
		if self.is_new() or self.status in {"Draft", "Rejected"}:
			return
		for fieldname in (
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
		):
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("Result Publication scope cannot change after approval begins."),
					frappe.ValidationError,
				)

	def _validate_duplicate_scope(self) -> None:
		filters = {
			"name": ["!=", self.name],
			"school_branch": self.school_branch,
			"student_group": self.student_group,
			"academic_year": self.academic_year,
			"academic_term": self.academic_term or "",
			"assessment_group": self.assessment_group,
		}
		duplicate = frappe.db.exists("EduEdge Result Publication", filters)
		if duplicate:
			frappe.throw(
				_("Result Publication {0} already exists for this scope.").format(duplicate),
				frappe.DuplicateEntryError,
			)
