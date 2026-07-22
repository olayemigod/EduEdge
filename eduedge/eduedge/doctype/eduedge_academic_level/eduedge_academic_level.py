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
		frappe.db.sql(
			"select name from `tabEduEdge Institution` where name = %s for update",
			(self.institution,),
		)
		if not self.is_new():
			if self.has_value_changed("level_code"):
				frappe.throw(_("Academic Level Code cannot change after creation."), frappe.ValidationError)
			if self.has_value_changed("institution"):
				frappe.throw(_("Academic Level cannot move to another Institution. Create a new Level instead."), frappe.ValidationError)
			if self.has_value_changed("academic_section") and frappe.db.exists(
				"EduEdge Program Offering", {"academic_level": self.name}
			):
				frappe.throw(_("Academic Section cannot change after Programme Offerings use this Level."), frappe.ValidationError)
		duplicate = frappe.db.exists(
			"EduEdge Academic Level",
			{"institution": self.institution, "level_code": self.level_code, "name": ["!=", self.name or ""]},
		)
		if duplicate:
			frappe.throw(_("Academic Level Code must be unique within the Institution."), frappe.DuplicateEntryError)
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
			self._validate_progression_cycle()

	def _validate_progression_cycle(self) -> None:
		visited = {self.name} if self.name else set()
		current = self.next_level
		while current:
			if current in visited:
				frappe.throw(_("Academic Level progression cannot contain a cycle."), frappe.ValidationError)
			visited.add(current)
			current = frappe.db.get_value("EduEdge Academic Level", current, "next_level")


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Academic Level Code is required."), frappe.ValidationError)
	return code
