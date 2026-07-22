from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeAcademicLevel(Document):
	def before_naming(self) -> None:
		self.level_code = _normalize_code(self.level_code)

	def before_validate(self) -> None:
		self.level_code = _normalize_code(self.level_code)

	def validate(self) -> None:
		if not frappe.db.exists("EduEdge Institution", {"name": self.institution, "enabled": 1}):
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
		if self.academic_section:
			section_institution = frappe.db.get_value("EduEdge Academic Section", self.academic_section, "institution")
			if section_institution != self.institution:
				frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)
		if self.next_level:
			if self.next_level == self.name:
				frappe.throw(_("Next Academic Level cannot be the same record."), frappe.ValidationError)
			next_institution = frappe.db.get_value("EduEdge Academic Level", self.next_level, "institution")
			if next_institution != self.institution:
				frappe.throw(_("Next Academic Level must belong to the same Institution."), frappe.ValidationError)


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Academic Level Code is required."), frappe.ValidationError)
	return code
