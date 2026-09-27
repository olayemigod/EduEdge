from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.report_cards import refresh_review_metrics, validate_report_card_review


REVIEW_WORKFLOW_AUDIT_FIELDS = (
	"recommended_by",
	"recommended_on",
	"approved_by",
	"approved_on",
)

REVIEW_CONTENT_FIELDS = (
	"class_teacher_comment",
	"principal_comment",
	"progression_recommendation",
	"last_review_note",
)


class EduEdgeReportCardReview(Document):
	def before_naming(self) -> None:
		if not self.title and self.student:
			student_name = frappe.db.get_value("Student", self.student, "student_name") or self.student
			self.title = f"{student_name} · {self.academic_term or self.academic_year or ''}".strip(" ·")

	def validate(self) -> None:
		validate_report_card_review(self)
		self._validate_workflow_state()
		refresh_review_metrics(self)
		student_name = frappe.db.get_value("Student", self.student, "student_name") or self.student
		self.title = f"{student_name} · {self.academic_term or self.academic_year or ''}".strip(" ·")
		self._validate_duplicate()

	def _validate_workflow_state(self) -> None:
		in_transition = bool(
			getattr(frappe.flags, "in_eduedge_report_card_transition", False)
		)
		if in_transition:
			return

		if self.is_new():
			if (self.progression_status or "Draft") != "Draft":
				frappe.throw(
					_("New Report Card Reviews must start in Draft status."),
					frappe.ValidationError,
				)
			if any(self.get(fieldname) for fieldname in REVIEW_WORKFLOW_AUDIT_FIELDS):
				frappe.throw(
					_("New Report Card Reviews cannot pre-populate recommendation or approval audit state."),
					frappe.ValidationError,
				)
			return

		if any(self.has_value_changed(fieldname) for fieldname in REVIEW_WORKFLOW_AUDIT_FIELDS):
			frappe.throw(
				_("Report Card Review workflow metadata can change only through EduEdge report-card actions."),
				frappe.ValidationError,
			)

		previous_status = frappe.db.get_value(
			"EduEdge Report Card Review",
			self.name,
			"progression_status",
		)
		if previous_status in {"Recommended", "Approved"} and any(
			self.has_value_changed(fieldname) for fieldname in REVIEW_CONTENT_FIELDS
		):
			frappe.throw(
				_("Recommended or Approved Report Card Reviews must be reopened before editing."),
				frappe.ValidationError,
			)

	def on_trash(self) -> None:
		if self.progression_status != "Draft":
			frappe.throw(
				_("Only Draft Report Card Reviews can be deleted."),
				frappe.ValidationError,
			)

	def _validate_duplicate(self) -> None:
		duplicate = frappe.db.exists(
			"EduEdge Report Card Review",
			{
				"name": ["!=", self.name],
				"result_publication": self.result_publication,
				"student": self.student,
			},
		)
		if duplicate:
			frappe.throw(
				_("Report Card Review {0} already exists for this student.").format(duplicate),
				frappe.DuplicateEntryError,
			)
