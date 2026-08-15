from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.academic_progression import LEVEL_PROGRESSION, PROGRAM_PROGRESSION_MODE_FIELD


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
			if self.has_value_changed("program") and _level_is_in_use(self.name):
				frappe.throw(_("Academic Level cannot move to another Programme after academic records use it."), frappe.ValidationError)
		duplicate_filters = {
			"institution": self.institution,
			"level_code": self.level_code,
			"name": ["!=", self.name or ""],
		}
		if self.program:
			duplicate_filters["program"] = self.program
		duplicate = frappe.db.exists("EduEdge Academic Level", duplicate_filters)
		if duplicate:
			frappe.throw(_("Academic Level Code must be unique within the Programme and Institution."), frappe.DuplicateEntryError)
		if cint(self.is_terminal) and self.next_level:
			frappe.throw(_("A terminal Academic Level cannot have a Next Academic Level."), frappe.ValidationError)
		if self.next_level:
			if self.next_level == self.name:
				frappe.throw(_("Next Academic Level cannot be the same record."), frappe.ValidationError)
			next_row = frappe.db.get_value(
				"EduEdge Academic Level",
				self.next_level,
				["institution", "program", "enabled"],
				as_dict=True,
			)
			if not next_row or not cint(next_row.enabled):
				frappe.throw(_("Next Academic Level must be enabled."), frappe.ValidationError)
			if next_row.institution != self.institution:
				frappe.throw(_("Next Academic Level must belong to the same Institution."), frappe.ValidationError)
			if self.program and next_row.program != self.program:
				frappe.throw(_("Next Academic Level must belong to the same Programme."), frappe.ValidationError)
			self._validate_progression_cycle()

	def _validate_program(self) -> None:
		if not self.program:
			# Historical legacy Levels are preserved. They are not eligible for the
			# governed tertiary/training progression workflow until explicitly mapped.
			return
		row = frappe.db.get_value(
			"Program",
			self.program,
			[INSTITUTION_FIELD, PROGRAM_PROGRESSION_MODE_FIELD],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Select a valid Programme."), frappe.ValidationError)
		if row.get(INSTITUTION_FIELD) != self.institution:
			frappe.throw(_("Academic Level Programme must belong to the same Institution."), frappe.ValidationError)
		if row.get(PROGRAM_PROGRESSION_MODE_FIELD) != LEVEL_PROGRESSION:
			frappe.throw(_("Academic Levels used for progression require a Level Progression Programme."), frappe.ValidationError)

	def _validate_progression_cycle(self) -> None:
		visited = {self.name} if self.name else set()
		current = self.next_level
		while current:
			if current in visited:
				frappe.throw(_("Academic Level progression cannot contain a cycle."), frappe.ValidationError)
			visited.add(current)
			current = frappe.db.get_value("EduEdge Academic Level", current, "next_level")


def _level_is_in_use(level: str) -> bool:
	for doctype in ("Program Enrollment", "Student Group"):
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		if meta.has_field("eduedge_progression_level") and frappe.db.exists(doctype, {"eduedge_progression_level": level}):
			return True
	return False


def _normalize_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Academic Level Code is required."), frappe.ValidationError)
	return code
