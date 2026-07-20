from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.report_cards import refresh_review_metrics, validate_report_card_review


class EduEdgeReportCardReview(Document):
	def before_naming(self) -> None:
		if not self.title and self.student:
			student_name = frappe.db.get_value("Student", self.student, "student_name") or self.student
			self.title = f"{student_name} · {self.academic_term or self.academic_year or ''}".strip(" ·")

	def validate(self) -> None:
		validate_report_card_review(self)
		refresh_review_metrics(self)
		student_name = frappe.db.get_value("Student", self.student, "student_name") or self.student
		self.title = f"{student_name} · {self.academic_term or self.academic_year or ''}".strip(" ·")
		self._validate_duplicate()

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
