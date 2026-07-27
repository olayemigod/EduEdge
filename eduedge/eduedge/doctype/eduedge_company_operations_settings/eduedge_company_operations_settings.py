from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


APPROVAL_MODES = {"Recommended", "Simple", "Standard"}
MAX_BULK_QUESTIONS = 100


class EduEdgeCompanyOperationsSettings(Document):
	def before_naming(self) -> None:
		self.name = self.company

	def validate(self) -> None:
		self._validate_company()
		self._validate_company_change()
		self._validate_question_governance()

	def _validate_company(self) -> None:
		if not frappe.db.exists("Company", self.company):
			frappe.throw(_("Select a valid Company."), frappe.ValidationError)
		if frappe.db.get_value("Company", self.company, "is_group") == 1:
			frappe.throw(_("A group Company cannot own EduEdge operations settings."), frappe.ValidationError)

	def _validate_company_change(self) -> None:
		if not self.is_new() and self.has_value_changed("company"):
			frappe.throw(_("Company cannot change after operations settings are created."), frappe.ValidationError)

	def _validate_question_governance(self) -> None:
		self.question_approval_mode = self.question_approval_mode or "Recommended"
		if self.question_approval_mode not in APPROVAL_MODES:
			frappe.throw(_("Question Approval Mode must be Recommended, Simple, or Standard."), frappe.ValidationError)
		self.max_bulk_question_approval = cint(self.max_bulk_question_approval or MAX_BULK_QUESTIONS)
		if not 1 <= self.max_bulk_question_approval <= MAX_BULK_QUESTIONS:
			frappe.throw(
				_("Maximum Questions per Bulk Action must be between 1 and {0}.").format(MAX_BULK_QUESTIONS),
				frappe.ValidationError,
			)
