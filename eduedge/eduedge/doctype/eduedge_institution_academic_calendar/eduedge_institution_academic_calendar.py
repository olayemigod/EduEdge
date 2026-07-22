from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EduEdgeInstitutionAcademicCalendar(Document):
	def validate(self) -> None:
		if not frappe.db.exists("EduEdge Institution", {"name": self.institution, "enabled": 1}):
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
		if getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("Calendar End Date cannot be earlier than Start Date."), frappe.ValidationError)
		duplicate = frappe.db.exists(
			"EduEdge Institution Academic Calendar",
			{"institution": self.institution, "academic_year": self.academic_year, "name": ["!=", self.name or ""]},
		)
		if duplicate:
			frappe.throw(_("An academic calendar already exists for this Institution and Academic Year."), frappe.DuplicateEntryError)
		if self.is_current and not self.enabled:
			frappe.throw(_("The current academic calendar must be enabled."), frappe.ValidationError)
		self._validate_periods()

	def on_update(self) -> None:
		if self.is_current:
			frappe.db.sql(
				"""
				update `tabEduEdge Institution Academic Calendar`
				set is_current = 0
				where institution = %s
					and name != %s
					and is_current = 1
				""",
				(self.institution, self.name),
			)
		frappe.clear_cache(doctype="EduEdge Institution Academic Calendar")

	def _validate_periods(self) -> None:
		seen_terms = set()
		periods = sorted(self.periods or [], key=lambda row: (getdate(row.start_date), getdate(row.end_date)))
		previous = None
		for row in periods:
			if row.academic_term in seen_terms:
				frappe.throw(_("Academic Term {0} is listed more than once.").format(row.academic_term), frappe.ValidationError)
			seen_terms.add(row.academic_term)
			term_year = frappe.db.get_value("Academic Term", row.academic_term, "academic_year")
			if term_year != self.academic_year:
				frappe.throw(_("Academic Term {0} does not belong to Academic Year {1}.").format(row.academic_term, self.academic_year), frappe.ValidationError)
			if getdate(row.end_date) < getdate(row.start_date):
				frappe.throw(_("Academic Period End Date cannot be earlier than Start Date."), frappe.ValidationError)
			if getdate(row.start_date) < getdate(self.start_date) or getdate(row.end_date) > getdate(self.end_date):
				frappe.throw(_("Academic Period dates must fall inside the Institution calendar dates."), frappe.ValidationError)
			if previous and getdate(row.start_date) <= getdate(previous.end_date):
				frappe.throw(
					_("Academic Period {0} overlaps with {1}.").format(row.academic_term, previous.academic_term),
					frappe.ValidationError,
				)
			if row.result_publication_date and getdate(row.result_publication_date) < getdate(row.end_date):
				frappe.throw(_("Result Publication Date cannot be earlier than the period End Date."), frappe.ValidationError)
			previous = row
