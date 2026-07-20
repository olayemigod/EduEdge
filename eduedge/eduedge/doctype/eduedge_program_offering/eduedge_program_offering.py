from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from eduedge.education.offerings import assert_branch_access


class EduEdgeProgramOffering(Document):
	def validate(self) -> None:
		assert_branch_access(self.school_branch)
		self._validate_term()
		self._validate_capacity()
		self._validate_dates()
		self._validate_duplicate()

	def _validate_term(self) -> None:
		if not self.academic_term:
			return
		actual_year = frappe.db.get_value("Academic Term", self.academic_term, "academic_year")
		if actual_year != self.academic_year:
			frappe.throw(
				_("Academic Term {0} does not belong to Academic Year {1}.").format(
					self.academic_term, self.academic_year
				),
				frappe.ValidationError,
			)

	def _validate_capacity(self) -> None:
		if (self.capacity or 0) < 0:
			frappe.throw(_("Capacity cannot be negative."), frappe.ValidationError)

	def _validate_dates(self) -> None:
		if self.application_start_date and self.application_end_date:
			if getdate(self.application_end_date) < getdate(self.application_start_date):
				frappe.throw(
					_("Application End Date cannot be earlier than Application Start Date."),
					frappe.ValidationError,
				)

	def _validate_duplicate(self) -> None:
		term = self.academic_term or ""
		duplicate = frappe.db.sql(
			"""
			select name
			from `tabEduEdge Program Offering`
			where school_branch = %s
				and program = %s
				and academic_year = %s
				and coalesce(academic_term, '') = %s
				and name != %s
			limit 1
			""",
			(
				self.school_branch,
				self.program,
				self.academic_year,
				term,
				self.name or "",
			),
		)
		if duplicate:
			frappe.throw(
				_("An EduEdge Program Offering already exists for this Branch, Program, Academic Year, and Academic Term."),
				frappe.DuplicateEntryError,
			)
