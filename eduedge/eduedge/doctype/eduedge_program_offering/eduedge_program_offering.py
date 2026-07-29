from __future__ import annotations

import hashlib
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.services.enrollment_lifecycle import count_capacity_consuming_enrollments

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
		self._validate_institution_calendar_period()
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

	def _validate_institution_calendar_period(self) -> None:
		"""Protect new or re-contextualised Offerings from global-term leakage.

		Legacy Offerings are not blocked when only non-identity fields are edited.
		When the Branch, year or period is selected or changed, the period must be
		configured on an enabled calendar owned by the resolved Institution.
		"""
		if not self.academic_term or not frappe.db.exists(
			"DocType", "EduEdge Institution Academic Calendar"
		):
			return
		context_changed = self.is_new() or any(
			self.has_value_changed(fieldname)
			for fieldname in ("school_branch", "academic_year", "academic_term")
		)
		if not context_changed:
			return
		calendars = frappe.get_all(
			"EduEdge Institution Academic Calendar",
			filters={
				"institution": self.institution,
				"academic_year": self.academic_year,
				"enabled": 1,
			},
			pluck="name",
		)
		if not calendars:
			frappe.throw(
				_("Configure an enabled Institution Academic Calendar for Academic Year {0} before selecting an Academic Period.").format(
					self.academic_year
				),
				frappe.ValidationError,
			)
		period_exists = frappe.db.exists(
			"EduEdge Academic Calendar Period",
			{
				"parent": ["in", calendars],
				"parenttype": "EduEdge Institution Academic Calendar",
				"academic_term": self.academic_term,
			},
		)
		if not period_exists:
			frappe.throw(
				_("Academic Period {0} is not configured on this Institution's Academic Calendar for {1}.").format(
					self.academic_term, self.academic_year
				),
				frappe.ValidationError,
			)

	def _validate_institution_context(self) -> None:
		if not self.institution:
			frappe.throw(_("The selected Branch must belong to an Institution."), frappe.ValidationError)

		program_meta = frappe.get_meta("Program")
		context_changed = self.is_new() or any(
			self.has_value_changed(fieldname)
			for fieldname in ("school_branch", "program", "academic_level", "student_batch")
		)
		if not self.program or not frappe.db.exists("Program", self.program):
			frappe.throw(_("Select a valid Programme."), frappe.ValidationError)
		if program_meta.has_field(INSTITUTION_FIELD):
			program_institution = frappe.db.get_value("Program", self.program, INSTITUTION_FIELD)
			if context_changed and not program_institution:
				frappe.throw(
					_("Assign the selected Programme to an Institution before creating or re-contextualising an Offering."),
					frappe.ValidationError,
				)
			if program_institution and program_institution != self.institution:
				frappe.throw(_("Program must belong to the same Institution as the selected Branch."), frappe.ValidationError)

		if self.academic_section:
			section = frappe.db.get_value(
				"EduEdge Academic Section",
				self.academic_section,
				["institution", "enabled"],
				as_dict=True,
			)
			if not section or section.institution != self.institution:
				frappe.throw(_("Academic Section must belong to the selected Institution."), frappe.ValidationError)
			if context_changed and not section.enabled:
				frappe.throw(_("Select an enabled Academic Section."), frappe.ValidationError)

		if self.academic_level:
			level = frappe.db.get_value(
				"EduEdge Academic Level",
				self.academic_level,
				["institution", "academic_section", "enabled"],
				as_dict=True,
			)
			if not level or level.institution != self.institution:
				frappe.throw(_("Academic Level must belong to the selected Institution."), frappe.ValidationError)
			if context_changed and not level.enabled:
				frappe.throw(_("Select an enabled Academic Level."), frappe.ValidationError)
			if level.academic_section and self.academic_section and level.academic_section != self.academic_section:
				frappe.throw(_("Academic Level must belong to the Program's Academic Section."), frappe.ValidationError)

		if self.student_batch:
			batch_meta = frappe.get_meta("Student Batch Name")
			if not frappe.db.exists("Student Batch Name", self.student_batch):
				frappe.throw(_("Select a valid Student Batch / Cohort."), frappe.ValidationError)
			if batch_meta.has_field(INSTITUTION_FIELD):
				batch_institution = frappe.db.get_value("Student Batch Name", self.student_batch, INSTITUTION_FIELD)
				if context_changed and not batch_institution:
					frappe.throw(
						_("Assign the selected Student Batch / Cohort to an Institution before using it on an Offering."),
						frappe.ValidationError,
					)
				if batch_institution and batch_institution != self.institution:
					frappe.throw(
						_("Student Batch / Cohort must belong to the same Institution as the selected Branch."),
						frappe.ValidationError,
					)

	def _validate_capacity(self) -> None:
		if (self.capacity or 0) < 0:
			frappe.throw(_("Capacity cannot be negative."), frappe.ValidationError)
		if self.is_new() or not self.capacity:
			return
		enrolled = count_capacity_consuming_enrollments(self.name)
		if enrolled > int(self.capacity):
			frappe.throw(
				_("Capacity cannot be lower than the {0} active or suspended enrollments already linked to this Offering.").format(enrolled),
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

	def _validate_duplicate(self) -> None:
		# Serialize identity checks for a Branch to prevent concurrent duplicate Offerings.
		frappe.db.sql(
			"select name from `tabEduEdge School Branch` where name = %s for update",
			(self.school_branch,),
		)
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
