from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class EduEdgeInstitution(Document):
	def before_naming(self) -> None:
		self.institution_code = _normalize_code(self.institution_code)

	def before_validate(self) -> None:
		self.institution_code = _normalize_code(self.institution_code)
		self.official_name = self.official_name or self.institution_name

	def validate(self) -> None:
		if not self.is_new() and self.has_value_changed("institution_code"):
			frappe.throw(_("Institution Code cannot change after creation."), frappe.ValidationError)
		self._validate_company()
		self._validate_company_change()
		self._validate_institution_type()
		self._validate_contact_details()
		if self.is_default and not self.enabled:
			frappe.throw(_("A default Institution must be enabled."), frappe.ValidationError)

	def on_update(self) -> None:
		if self.is_default:
			frappe.db.set_value(
				"EduEdge Institution",
				{"company": self.company, "is_default": 1, "name": ["!=", self.name]},
				"is_default",
				0,
				update_modified=False,
			)
		frappe.clear_cache(doctype="EduEdge Institution")

	def _validate_company(self) -> None:
		if not frappe.db.exists("Company", self.company):
			frappe.throw(_("Select a valid Company."), frappe.ValidationError)
		if frappe.db.get_value("Company", self.company, "is_group") == 1:
			frappe.throw(_("A group Company cannot own an EduEdge Institution."), frappe.ValidationError)

	def _validate_company_change(self) -> None:
		if self.is_new() or not self.has_value_changed("company"):
			return
		if frappe.db.exists("EduEdge School Branch", {"institution": self.name}):
			frappe.throw(
				_("Company cannot change after School Branches are linked to this Institution."),
				frappe.ValidationError,
			)

	def _validate_institution_type(self) -> None:
		if not frappe.db.exists(
			"EduEdge Institution Type",
			{"name": self.institution_type, "enabled": 1},
		):
			frappe.throw(_("Select an enabled EduEdge Institution Type."), frappe.ValidationError)

	def _validate_contact_details(self) -> None:
		if self.email and not validate_email_address(self.email):
			frappe.throw(_("Enter a valid institution email address."), frappe.ValidationError)


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Institution Code is required."))
	return code
