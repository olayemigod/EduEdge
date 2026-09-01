from __future__ import annotations

import hashlib
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.education.offerings import assert_branch_access


def _clean_name(value: str | None) -> str:
	return " ".join(str(value or "").split())


def _make_code(branch: str, program: str, label: str) -> str:
	prefix = re.sub(r"[^A-Z0-9]+", "-", label.upper()).strip("-")[:24] or "ARM"
	seed = f"{branch}::{program}::{label.casefold()}"
	digest = hashlib.sha1(seed.encode()).hexdigest()[:8].upper()
	return f"{prefix}-{digest}"


class EduEdgeClassArm(Document):
	def validate(self):
		self.class_arm_name = _clean_name(self.class_arm_name)
		if not self.class_arm_name:
			frappe.throw(_("Class Arm Name is required."), frappe.ValidationError)
		self.default_capacity = max(cint(self.default_capacity), 0)
		assert_branch_access(self.school_branch)

		institution = frappe.db.get_value("EduEdge School Branch", self.school_branch, "institution")
		if not institution:
			frappe.throw(_("The selected School Branch / Campus is not linked to an Institution."), frappe.ValidationError)
		if self.institution and self.institution != institution:
			frappe.throw(_("Class Arm Institution must match the selected Branch / Campus."), frappe.ValidationError)
		self.institution = institution

		program_meta = frappe.get_meta("Program")
		if program_meta.has_field(INSTITUTION_FIELD):
			program_institution = frappe.db.get_value("Program", self.program, INSTITUTION_FIELD)
			if program_institution and program_institution != institution:
				frappe.throw(_("Class / Programme must belong to the same Institution as the Class Arm."), frappe.ValidationError)

		if not self.class_arm_code:
			self.class_arm_code = _make_code(self.school_branch, self.program, self.class_arm_name)

		if not self.is_new():
			original = frappe.db.get_value(
				self.doctype,
				self.name,
				["school_branch", "institution", "program", "class_arm_code"],
				as_dict=True,
			) or {}
			for fieldname, label in (
				("school_branch", _("School Branch / Campus")),
				("institution", _("Institution")),
				("program", _("Class / Programme")),
			):
				old = original.get(fieldname)
				if old and old != self.get(fieldname):
					frappe.throw(
						_("{0} cannot be changed after a Class Arm identity is created. Create a new Class Arm instead.").format(label),
						frappe.ValidationError,
					)
			if original.get("class_arm_code"):
				self.class_arm_code = original.class_arm_code

		duplicate = frappe.db.sql(
			"""
			select name
			from `tabEduEdge Class Arm`
			where school_branch = %(branch)s
			  and program = %(program)s
			  and lower(trim(class_arm_name)) = lower(trim(%(label)s))
			  and name != %(name)s
			limit 1
			""",
			{
				"branch": self.school_branch,
				"program": self.program,
				"label": self.class_arm_name,
				"name": self.name or "",
			},
		)
		if duplicate:
			frappe.throw(
				_("Class Arm {0} already exists for this Branch and Class / Programme.").format(self.class_arm_name),
				frappe.DuplicateEntryError,
			)
