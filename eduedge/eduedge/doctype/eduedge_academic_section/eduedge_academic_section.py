from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeAcademicSection(Document):
	def before_naming(self) -> None:
		self.section_code = _normalize_code(self.section_code)

	def before_validate(self) -> None:
		self.section_code = _normalize_code(self.section_code)

	def validate(self) -> None:
		if not frappe.db.exists("EduEdge Institution", {"name": self.institution, "enabled": 1}):
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
		frappe.db.sql(
			"select name from `tabEduEdge Institution` where name = %s for update",
			(self.institution,),
		)
		if not self.is_new():
			if self.has_value_changed("section_code"):
				frappe.throw(_("Academic Section Code cannot change after creation."), frappe.ValidationError)
			if self.has_value_changed("institution"):
				frappe.throw(_("Academic Section cannot move to another Institution. Create a new Section instead."), frappe.ValidationError)
		duplicate = frappe.db.exists(
			"EduEdge Academic Section",
			{"institution": self.institution, "section_code": self.section_code, "name": ["!=", self.name or ""]},
		)
		if duplicate:
			frappe.throw(_("Academic Section Code must be unique within the Institution."), frappe.DuplicateEntryError)


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Academic Section Code is required."), frappe.ValidationError)
	return code
