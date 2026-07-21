from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from eduedge.education.offerings import assert_branch_access

SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
OBJECTIVE_TYPES = {"Single Choice", "Multiple Choice", "True/False"}
REVIEW_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}
PLATFORM_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}
PROTECTED_FIELDS = (
	"question_code",
	"ownership_scope",
	"school_branch",
	"version_number",
	"supersedes_question",
	"course",
	"topic",
	"curriculum",
	"exam_body",
	"difficulty",
	"question_type",
	"question_text",
	"answer_key",
	"marking_guide",
	"default_mark",
	"negative_mark",
)
ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Under Review", "Approved"},
	"Under Review": {"Draft", "Under Review", "Approved"},
	"Approved": {"Approved", "Retired"},
	"Retired": {"Retired"},
}


class EduEdgeCBTQuestion(Document):
	def validate(self) -> None:
		self.question_code = (self.question_code or "").strip().upper()
		self._validate_identity()
		self._validate_scope()
		self._validate_version()
		self._validate_marks()
		self._validate_answers()
		self._validate_status_transition()
		self._prevent_approved_content_mutation()

	def _validate_identity(self) -> None:
		if not self.question_code:
			frappe.throw(_("Question Code is required."), frappe.ValidationError)
		if not (self.question_text or "").strip():
			frappe.throw(_("Question is required."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.ownership_scope == SCHOOL_BANK:
			if not self.school_branch:
				frappe.throw(
					_("School Branch / Campus is required for a School Question Bank question."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			return

		if self.ownership_scope == PLATFORM_BANK:
			self._assert_platform_manager()
			self.school_branch = None
			return

		frappe.throw(_("Select a valid Question Bank."), frappe.ValidationError)

	def _validate_version(self) -> None:
		if cint(self.version_number) < 1:
			frappe.throw(_("Question Version must be at least 1."), frappe.ValidationError)
		if not self.supersedes_question:
			return
		if self.supersedes_question == self.name:
			frappe.throw(_("A question cannot supersede itself."), frappe.ValidationError)
		previous = frappe.db.get_value(
			"EduEdge CBT Question",
			self.supersedes_question,
			[
				"status",
				"ownership_scope",
				"school_branch",
				"course",
				"version_number",
			],
			as_dict=True,
		)
		if not previous:
			frappe.throw(_("The question selected to supersede does not exist."), frappe.ValidationError)
		if previous.status not in {"Approved", "Retired"}:
			frappe.throw(
				_("Only an Approved or Retired question can be superseded."),
				frappe.ValidationError,
			)
		if (
			previous.ownership_scope != self.ownership_scope
			or previous.school_branch != self.school_branch
			or previous.course != self.course
		):
			frappe.throw(
				_("A new question version must keep the same Question Bank, Branch, and Subject / Course."),
				frappe.ValidationError,
			)
		if cint(self.version_number) <= cint(previous.version_number):
			frappe.throw(
				_("The new Question Version must be greater than the superseded version."),
				frappe.ValidationError,
			)

	def _validate_marks(self) -> None:
		if flt(self.default_mark) <= 0:
			frappe.throw(_("Default Mark must be greater than zero."), frappe.ValidationError)
		if flt(self.negative_mark) < 0:
			frappe.throw(_("Negative Mark cannot be negative."), frappe.ValidationError)
		if flt(self.negative_mark) > flt(self.default_mark):
			frappe.throw(
				_("Negative Mark cannot exceed the Default Mark."),
				frappe.ValidationError,
			)

	def _validate_answers(self) -> None:
		rows = list(self.get("options") or [])
		if self.question_type not in OBJECTIVE_TYPES:
			if rows:
				frappe.throw(
					_("Answer Options are only allowed for objective question types."),
					frappe.ValidationError,
				)
			if self.question_type in {"Short Answer", "Numeric"} and not (self.answer_key or "").strip():
				frappe.throw(_("Answer Key is required for this question type."), frappe.ValidationError)
			if self.question_type == "Essay" and not (self.marking_guide or "").strip():
				frappe.throw(_("Marking Guide is required for an Essay question."), frappe.ValidationError)
			return

		if len(rows) < 2:
			frappe.throw(_("Objective questions require at least two Answer Options."), frappe.ValidationError)
		if self.question_type == "True/False" and len(rows) != 2:
			frappe.throw(_("True/False questions require exactly two Answer Options."), frappe.ValidationError)

		seen_keys: set[str] = set()
		correct_count = 0
		for index, row in enumerate(rows, start=1):
			row.option_key = (row.option_key or "").strip().upper()
			row.option_text = (row.option_text or "").strip()
			if not row.option_key or not row.option_text:
				frappe.throw(
					_("Every Answer Option requires an Option Key and Option Text."),
					frappe.ValidationError,
				)
			if row.option_key in seen_keys:
				frappe.throw(
					_("Answer Option Key {0} is used more than once.").format(row.option_key),
					frappe.ValidationError,
				)
			seen_keys.add(row.option_key)
			row.display_order = cint(row.display_order) or index
			correct_count += cint(row.is_correct)

		if self.question_type in {"Single Choice", "True/False"} and correct_count != 1:
			frappe.throw(
				_("This question type requires exactly one correct Answer Option."),
				frappe.ValidationError,
			)
		if self.question_type == "Multiple Choice" and correct_count < 1:
			frappe.throw(
				_("Multiple Choice questions require at least one correct Answer Option."),
				frappe.ValidationError,
			)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Question Status cannot change from {0} to {1}.").format(previous_status, self.status),
				frappe.ValidationError,
			)
		if self.status in {"Approved", "Retired"} and self.status != previous_status:
			self._assert_review_authority()
		if self.status == "Approved" and self.status != previous_status:
			self.reviewed_by = frappe.session.user
			self.reviewed_on = now_datetime()

	def _prevent_approved_content_mutation(self) -> None:
		before = self.get_doc_before_save()
		if not before or before.status not in {"Approved", "Retired"}:
			return
		for fieldname in PROTECTED_FIELDS:
			if before.get(fieldname) != self.get(fieldname):
				frappe.throw(
					_("Approved question content is immutable. Create a new version instead."),
					frappe.ValidationError,
				)
		if self._option_fingerprint(before) != self._option_fingerprint(self):
			frappe.throw(
				_("Approved Answer Options are immutable. Create a new question version instead."),
				frappe.ValidationError,
			)

	def _assert_review_authority(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(REVIEW_ROLES):
			frappe.throw(
				_("You are not permitted to approve or retire CBT questions."),
				frappe.PermissionError,
			)

	def _assert_platform_manager(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(PLATFORM_MANAGER_ROLES):
			frappe.throw(
				_("Only an EduEdge platform administrator can manage the EduEdge Examination Bank."),
				frappe.PermissionError,
			)

	@staticmethod
	def _option_fingerprint(doc) -> tuple:
		return tuple(
			(
				(row.option_key or "").strip().upper(),
				(row.option_text or "").strip(),
				cint(row.is_correct),
				cint(row.display_order),
			)
			for row in (doc.get("options") or [])
		)
