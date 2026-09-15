from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeReportCardIssue(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(_("Issued Report Cards are immutable."), frappe.ValidationError)
		expected_hash = hashlib.sha256((self.payload_json or "").encode("utf-8")).hexdigest()
		if self.payload_hash != expected_hash:
			frappe.throw(_("Issued Report Card payload hash is invalid."), frappe.ValidationError)

		review = frappe.db.get_value(
			"EduEdge Report Card Review",
			self.report_card_review,
			["result_publication", "student", "school_branch", "progression_status"],
			as_dict=True,
		)
		if not review or review.progression_status != "Approved":
			frappe.throw(_("Report Card Issue requires an Approved review."), frappe.ValidationError)
		if review.result_publication != self.result_publication or review.student != self.student:
			frappe.throw(_("Report Card Issue must match its Approved review scope."), frappe.ValidationError)
		if review.school_branch != self.school_branch:
			frappe.throw(_("Report Card Issue Branch must match its Approved review."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(_("Issued Report Cards are immutable and cannot be deleted."), frappe.ValidationError)
