from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


STEP_LABELS = {
	"session_terms": "Session & Terms",
	"class_structure": "Class Structure",
	"class_intakes": "Class Intakes",
	"class_arms": "Class Arms",
	"student_progression": "Student Progression",
	"admissions_enrollment": "Admissions & Enrollment",
	"academic_delivery": "Academic Delivery",
	"assessment_cbt": "Assessment & CBT",
	"operational_readiness": "Operational Readiness",
	"final_review": "Final Review & Activation",
}

ALLOWED_STATUSES = {"Draft", "Preparing", "Ready for Review", "Ready", "Active", "Closed"}


class EduEdgeAcademicSessionLaunch(Document):
	def before_insert(self):
		self.status = self.status or "Draft"
		self.current_step_key = self.current_step_key or "session_terms"
		self.started_by = self.started_by or frappe.session.user
		self.started_on = self.started_on or now_datetime()
		self.last_resumed_by = self.last_resumed_by or frappe.session.user
		self.last_resumed_on = self.last_resumed_on or now_datetime()

	def validate(self):
		self._validate_identity()
		self._validate_source_session()
		self._validate_state()
		self._validate_duplicate()
		self.current_step_label = STEP_LABELS[self.current_step_key]

	def _validate_identity(self):
		if not self.institution or not frappe.db.exists("EduEdge Institution", self.institution):
			frappe.throw(_("Select a valid Institution."), frappe.ValidationError)
		if not self.academic_year or not frappe.db.exists("Academic Year", self.academic_year):
			frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)

	def _validate_source_session(self):
		if not self.source_academic_year:
			return
		if not frappe.db.exists("Academic Year", self.source_academic_year):
			frappe.throw(_("Select a valid Source Academic Session."), frappe.ValidationError)
		if self.source_academic_year == self.academic_year:
			frappe.throw(_("Source and target Academic Sessions must be different."), frappe.ValidationError)
		source_start = frappe.db.get_value("Academic Year", self.source_academic_year, "year_start_date")
		target_start = frappe.db.get_value("Academic Year", self.academic_year, "year_start_date")
		if source_start and target_start and getdate(source_start) >= getdate(target_start):
			frappe.throw(_("Source Academic Session must be earlier than the target Session."), frappe.ValidationError)

	def _validate_state(self):
		if self.status not in ALLOWED_STATUSES:
			frappe.throw(_("Select a valid Session Launch status."), frappe.ValidationError)
		if self.current_step_key not in STEP_LABELS:
			frappe.throw(_("Select a valid Session Launch step."), frappe.ValidationError)

	def _validate_duplicate(self):
		existing = frappe.db.exists(
			"EduEdge Academic Session Launch",
			{"institution": self.institution, "academic_year": self.academic_year},
		)
		if existing and existing != self.name:
			frappe.throw(
				_("A Session Launch already exists for {0} and Academic Session {1}.").format(
					self.institution,
					self.academic_year,
				),
				frappe.DuplicateEntryError,
			)
