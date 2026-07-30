from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_progression import LEVEL_PROGRESSION, get_program_progression


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
		self._validate_program()
		if not self.is_new():
			if self.has_value_changed("level_code"):
				frappe.throw(_("Academic Level Code cannot change after creation."), frappe.ValidationError)
			if self.has_value_changed("institution"):
				frappe.throw(_("Academic Level cannot move to another Institution. Create a new Level instead."), frappe.ValidationError)
			if self.has_value_changed("program") and frappe.db.exists(
				"EduEdge Program Offering", {"academic_level": self.name}
			):
				frappe.throw(_("Programme cannot change after Programme Offerings use this Level."), frappe.ValidationError)
		self._validate_duplicates()
		self._validate_next_level()

	def _validate_program(self) -> None:
		if not self.program:
			if self.is_new():
				frappe.throw(_("Programme is required for a new Academic Level."), frappe.ValidationError)
			return
		program = get_program_progression(self.program)
		if not program:
			frappe.throw(_("Select a valid Programme."), frappe.ValidationError)
		if program.get(INSTITUTION_FIELD) != self.institution:
			frappe.throw(_("Academic Level Programme must belong to the selected Institution."), frappe.ValidationError)
		if program.get("eduedge_progression_mode") != LEVEL_PROGRESSION:
			frappe.throw(_("Academic Levels are only valid for a Programme configured for Level Progression."), frappe.ValidationError)

	def _validate_duplicates(self) -> None:
		filters = {
			"institution": self.institution,
			"program": self.program or "",
			"name": ["!=", self.name or ""],
		}
		if frappe.db.exists("EduEdge Academic Level", {**filters, "level_code": self.level_code}):
			frappe.throw(_("Academic Level Code must be unique within the Programme."), frappe.DuplicateEntryError)
		if frappe.db.exists("EduEdge Academic Level", {**filters, "level_name": self.level_name}):
			frappe.throw(_("Academic Level Name must be unique within the Programme."), frappe.DuplicateEntryError)

	def _validate_next_level(self) -> None:
		if cint(self.is_terminal) and self.next_level:
			frappe.throw(_("A terminal Academic Level cannot have a Next Academic Level."), frappe.ValidationError)
		if not self.next_level:
			return
		if self.next_level == self.name:
			frappe.throw(_("Next Academic Level cannot be the same record."), frappe.ValidationError)
		next_row = frappe.db.get_value(
			"EduEdge Academic Level",
			self.next_level,
			["institution", "program", "enabled"],
			as_dict=True,
		)
		if not next_row or not cint(next_row.enabled):
			frappe.throw(_("Select an enabled Next Academic Level."), frappe.ValidationError)
		if next_row.institution != self.institution:
			frappe.throw(_("Next Academic Level must belong to the same Institution."), frappe.ValidationError)
		if next_row.program != self.program:
			frappe.throw(_("Next Academic Level must belong to the same Programme."), frappe.ValidationError)
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
