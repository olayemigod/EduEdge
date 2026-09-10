from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeStudentPhotoReviewLog(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Student photo review logs are append-only."), frappe.ValidationError)
		if self.reference_doctype not in {"Student Applicant", "Student"}:
			frappe.throw(_("Invalid student photo reference type."), frappe.ValidationError)
