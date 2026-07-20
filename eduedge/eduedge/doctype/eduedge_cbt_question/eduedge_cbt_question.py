from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, strip_html

from eduedge.cbt.domain import stable_hash, validate_question_contract
from eduedge.education.offerings import assert_branch_access


class EduEdgeCBTQuestion(Document):
	def before_validate(self) -> None:
		if not self.title:
			plain_text = " ".join(strip_html(self.question_text or "").split())
			self.title = plain_text[:120] or _("Untitled CBT Question")

	def validate(self) -> None:
		assert_branch_access(self.school_branch)
		if flt(self.default_marks) <= 0:
			frappe.throw(_("Default marks must be greater than zero."), frappe.ValidationError)

		normalized_options = validate_question_contract(
			self.question_type,
			[
				{
					"option_key": row.option_key,
					"option_text": row.option_text,
					"is_correct": row.is_correct,
					"display_order": row.display_order,
				}
				for row in self.options
			],
		)
		for row, normalized in zip(self.options, normalized_options, strict=True):
			row.option_key = normalized["option_key"]
			row.option_text = normalized["option_text"]
			row.is_correct = normalized["is_correct"]
			row.display_order = normalized["display_order"]

		new_hash = stable_hash(
			{
				"school_branch": self.school_branch,
				"course": self.course,
				"question_type": self.question_type,
				"difficulty": self.difficulty,
				"default_marks": flt(self.default_marks),
				"is_active": bool(self.is_active),
				"question_text": self.question_text or "",
				"options": normalized_options,
				"explanation": self.explanation or "",
			}
		)
		previous_hash = None if self.is_new() else frappe.db.get_value(self.doctype, self.name, "content_hash")
		if previous_hash and previous_hash != new_hash:
			self._assert_not_used_by_locked_exam()
			previous_version = frappe.db.get_value(self.doctype, self.name, "version_no") or 1
			self.version_no = int(previous_version) + 1
		elif self.is_new():
			self.version_no = 1
		self.content_hash = new_hash

	def on_trash(self) -> None:
		self._assert_not_used_by_locked_exam()

	def _assert_not_used_by_locked_exam(self) -> None:
		if self.is_new() or not self.name:
			return
		locked = frappe.db.sql(
			"""
			select exam_question.parent
			from `tabEduEdge CBT Exam Question` exam_question
			inner join `tabEduEdge CBT Exam` exam
				on exam.name = exam_question.parent
				and exam_question.parenttype = 'EduEdge CBT Exam'
			where exam_question.question = %s
				and exam.status not in ('Draft', 'Cancelled')
			limit 1
			""",
			self.name,
		)
		if locked:
			frappe.throw(
				_("This question is used by scheduled or active CBT Exam {0}. Create a new question version instead.").format(
					locked[0][0]
				),
				frappe.ValidationError,
			)
