from __future__ import annotations

import hashlib
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.offerings import assert_branch_access

IDENTITY_FIELDS = (
	"school_branch",
	"program",
	"academic_year",
	"academic_term",
	"student_batch",
	"study_mode",
	"delivery_mode",
	"academic_level",
)


class EduEdgeProgramOffering(Document):
	def before_validate(self) -> None:
		self._derive_context()
		self.offering_code = self._normalize_or_generate_code()
		if not self.offering_title:
			self.offering_title = " · ".join(
				value
				for value in (
					self.program,
					self.academic_year,
					self.academic_term,
					self.study_mode,
					self.school_branch,
				)
				if value
			)

	def validate(self) -> None:
		assert_branch_access(self.school_branch)
		if not self.is_new() and self.has_value_changed("offering_code"):
			frappe.throw(_("Offering Code cannot change after creation."), frappe.ValidationError)
		self._validate_identity_changes()
		self._validate_term()
		self._validate_institution_context()
		self._validate_capacity()
		self._validate_dates()
		self._validate_duplicate()

	def _derive_context(self) -> None:
		branch = (
			frappe.db.get_value(
				"EduEdge School Branch",
				self.school_branch,
				["institution", "enabled"],
				as_dict=True,
			)
			if self.school_branch
			else None
		)
		if not branch or not branch.enabled:
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		self.institution = branch.institution
		program_meta = frappe.get_meta("Program")
		if self.program and program_meta.has_field("eduedge_academic_section"):
			self.academic_section = frappe.db.get_value("Program", self.program, "eduedge_academic_section")

	def _normalize_or_generate_code(self) -> str:
		code = re.sub(r"[^A-Z0-9]+", "-", str(self.offering_code or "").strip().upper()).strip("-")
		if code:
			return code
		seed = "::".join(
			str(value or "")
			for value in (
				self.name,
				self.school_branch,
				self.program,
				self.academic_year,
				self.academic_term,
				self.student_batch,
				self.study_mode,
				self.delivery_mode,
			)
		)
		return f"OFR-{hashlib.sha1(seed.encode()).hexdigest()[:12].upper()}"

	def _validate_identity_changes(self) -> None:
		if self.is_new() or not any(self.has_value_changed(fieldname) for fieldname in IDENTITY_FIELDS):
			return
		if self._has_operational_references():
			frappe.throw(
				_("Programme Offering identity cannot change after applicants, groups, or submitted enrollments reference it. Create a new Offering instead."),
				frappe.ValidationError,
			)

	def _has_operational_references(self) -> bool:
		for doctype in ("Student Applicant", "Student Group"):
			if frappe.db.exists("DocType", doctype) and frappe.get_meta(doctype).has_field(OFFERING_FIELD):
				if frappe.db.exists(doctype, {OFFERING_FIELD: self.name}):
					return True
		if frappe.db.exists("DocType", "Program Enrollment") and frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD):
			return bool(
				frappe.db.exists(
					"Program Enrollment",
					{OFFERING_FIELD: self.name, "docstatus": 1},
				)
			)
		return False

	def _validate_term(self) -> None:
		if not self.academic_term:
			return
		actual_year = frappe.db.get_value("Academic Term", self.academic_term, "academic_year")
		if actual_year != self.academic_year:
			frappe.throw(
				_("Academic Term {0} does not belong to Academic Year {1}.").format(
					self.academic_term, self.academic_year
				),
				frappe.ValidationError,
			)

	def _validate_institution_context(self) -> None:
		if not self.institution:
			frappe.throw(_("The selected Branch must belong to an Institution."), frappe.ValidationError)
		program_meta = frappe.get_meta("Program")
		if self.program and program_meta.has_field("eduedge_institution"):
			program_institution = frappe.db.get_value("Program", self.program, "eduedge_institution")
			if program_institution and program_institution != self.institution:
				frappe.throw(_("Program must belong to the same Institution as the selected Branch."), frappe.ValidationError)
		if self.academic_section:
			section_institution = frappe.db.get_value("EduEdge Academic Section", self.academic_section, "institution")
			if section_institution != self.institution:
				frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)
		if self.academic_level:
			level = frappe.db.get_value(
				"EduEdge Academic Level",
				self.academic_level,
				["institution", "academic_section"],
				as_dict=True,
			)
			if not level or level.institution != self.institution:
				frappe.throw(_("Academic Level must belong to the selected Institution."), frappe.ValidationError)
			if level.academic_section and self.academic_section and level.academic_section != self.academic_section:
				frappe.throw(_("Academic Level must belong to the Program's Academic Section."), frappe.ValidationError)

	def _validate_capacity(self) -> None:
		if (self.capacity or 0) < 0:
			frappe.throw(_("Capacity cannot be negative."), frappe.ValidationError)
		if self.is_new() or not self.capacity:
			return
		enrolled = frappe.db.count(
			"Program Enrollment",
			{OFFERING_FIELD: self.name, "docstatus": 1},
		) if frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD) else 0
		if enrolled > int(self.capacity):
			frappe.throw(
				_("Capacity cannot be lower than the {0} submitted enrollments already linked to this Offering.").format(enrolled),
				frappe.ValidationError,
			)

	def _validate_dates(self) -> None:
		for start_field, end_field, label in (
			("start_date", "end_date", _("Offering")),
			("application_start_date", "application_end_date", _("Application")),
		):
			start_date = self.get(start_field)
			end_date = self.get(end_field)
			if start_date and end_date and getdate(end_date) < getdate(start_date):
				frappe.throw(_("{0} End Date cannot be earlier than Start Date.").format(label), frappe.ValidationError)
		if self.start_date and self.application_end_date and getdate(self.application_end_date) > getdate(self.start_date):
			frappe.throw(_("Application End Date cannot be later than the Offering Start Date."), frappe.ValidationError)

	def _validate_duplicate(self) -> None:
		duplicate = frappe.db.sql(
			"""
			select name
			from `tabEduEdge Program Offering`
			where school_branch = %s
				and program = %s
				and academic_year = %s
				and coalesce(academic_term, '') = %s
				and coalesce(student_batch, '') = %s
				and coalesce(study_mode, '') = %s
				and coalesce(delivery_mode, '') = %s
				and name != %s
			limit 1
			""",
			(
				self.school_branch,
				self.program,
				self.academic_year,
				self.academic_term or "",
				self.student_batch or "",
				self.study_mode or "",
				self.delivery_mode or "",
				self.name or "",
			),
		)
		if duplicate:
			frappe.throw(
				_("A matching Programme Offering already exists for this Branch, Program, period, cohort, and delivery mode."),
				frappe.DuplicateEntryError,
			)
