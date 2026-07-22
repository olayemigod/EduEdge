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
		duplicate = frappe.db.exists(
			"EduEdge Academic Section",
			{"institution": self.institution, "section_code": self.section_code, "name": ["!=", self.name or ""]},
		)
		if duplicate:
			frappe.throw(_("Academic Section Code must be unique within the Institution."), frappe.DuplicateEntryError)
		if not self.is_new() and self.has_value_changed("institution"):
			if frappe.db.exists("Program", {"eduedge_academic_section": self.name}):
				frappe.throw(_("Institution cannot change after Programs are linked to this Academic Section."), frappe.ValidationError)


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Academic Section Code is required."), frappe.ValidationError)
	return code
