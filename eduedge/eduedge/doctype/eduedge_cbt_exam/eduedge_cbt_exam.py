from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime

from eduedge.cbt.domain import validate_exam_schedule
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Scheduled", "Cancelled"},
	"Scheduled": {"Active", "Cancelled"},
	"Active": {"Closed", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
}
LOCKED_FIELDS = (
	"school_branch",
	"student_group",
	"course",
	"academic_year",
	"academic_term",
	"assessment_group",
	"start_datetime",
	"end_datetime",
	"duration_minutes",
	"sync_grace_minutes",
	"max_attempts",
	"allow_resume",
	"auto_submit_on_timeout",
	"randomize_questions",
	"randomize_options",
	"questions",
)


class EduEdgeCBTExam(Document):
	def before_validate(self) -> None:
		if not self.title:
			parts = [self.course, self.student_group, self.academic_term or self.academic_year]
			self.title = " · ".join(part for part in parts if part) or _("Untitled CBT Exam")

	def validate(self) -> None:
		assert_branch_access(self.school_branch)
		self._validate_status_transition()
		self._validate_locked_fields()
		self._validate_scope()
		validate_exam_schedule(
			start_datetime=get_datetime(self.start_datetime),
			end_datetime=get_datetime(self.end_datetime),
			duration_minutes=cint(self.duration_minutes),
		)
		if cint(self.sync_grace_minutes) < 0 or cint(self.sync_grace_minutes) > 120:
			frappe.throw(_("Pending sync grace must be between 0 and 120 minutes."), frappe.ValidationError)
		if cint(self.max_attempts) < 1 or cint(self.max_attempts) > 5:
			frappe.throw(_("Maximum attempts must be between 1 and 5."), frappe.ValidationError)
		self._validate_questions()

	def on_trash(self) -> None:
		if self.status not in {"Draft", "Cancelled"}:
			frappe.throw(_("Only Draft or Cancelled CBT Exams can be deleted."), frappe.ValidationError)
		if frappe.db.exists("EduEdge CBT Attempt", {"exam": self.name}):
			frappe.throw(_("A CBT Exam with attempts cannot be deleted."), frappe.ValidationError)

	def _validate_status_transition(self) -> None:
		if self.is_new():
			if self.status != "Draft" and not self.flags.get("allow_cbt_transition"):
				frappe.throw(_("New CBT Exams must start in Draft."), frappe.ValidationError)
			return
		previous_status = frappe.db.get_value(self.doctype, self.name, "status") or "Draft"
		if previous_status == self.status:
			return
		if not self.flags.get("allow_cbt_transition"):
			frappe.throw(_("Use the CBT Operations actions to change exam status."), frappe.ValidationError)
		if self.status not in ALLOWED_STATUS_TRANSITIONS.get(previous_status, set()):
			frappe.throw(
				_("CBT Exam cannot move from {0} to {1}.").format(previous_status, self.status),
				frappe.ValidationError,
			)

	def _validate_locked_fields(self) -> None:
		if self.is_new():
			return
		previous_status = frappe.db.get_value(self.doctype, self.name, "status") or "Draft"
		if previous_status == "Draft":
			return
		for fieldname in LOCKED_FIELDS:
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("{0} cannot change after the CBT Exam is scheduled.").format(self.meta.get_label(fieldname)),
					frappe.ValidationError,
				)

	def _validate_scope(self) -> None:
		group = frappe.db.get_value(
			"Student Group",
			self.student_group,
			[BRANCH_FIELD, "academic_year", "academic_term", "course", "disabled"],
			as_dict=True,
		)
		if not group or group.disabled:
			frappe.throw(_("Select an active Student Group / Class."), frappe.ValidationError)
		if group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Student Group must belong to the selected branch."), frappe.ValidationError)
		if group.academic_year and group.academic_year != self.academic_year:
			frappe.throw(_("Student Group and CBT Exam must use the same Academic Year."), frappe.ValidationError)
		if group.academic_term and self.academic_term and group.academic_term != self.academic_term:
			frappe.throw(_("Student Group and CBT Exam must use the same Academic Term."), frappe.ValidationError)
		if group.course and group.course != self.course:
			frappe.throw(_("Student Group and CBT Exam must use the same Course / Subject."), frappe.ValidationError)

	def _validate_questions(self) -> None:
		if not self.questions:
			frappe.throw(_("Add at least one question before saving a CBT Exam."), frappe.ValidationError)
		question_names = [row.question for row in self.questions if row.question]
		if len(question_names) != len(set(question_names)):
			frappe.throw(_("A CBT question cannot be added to the same exam more than once."), frappe.ValidationError)
		question_rows = frappe.get_all(
			"EduEdge CBT Question",
			filters={"name": ["in", question_names]},
			fields=["name", "school_branch", "course", "default_marks", "is_active"],
		)
		questions = {row.name: row for row in question_rows}
		total_marks = 0.0
		for index, row in enumerate(self.questions, start=1):
			question = questions.get(row.question)
			if not question:
				frappe.throw(_("CBT Question {0} was not found.").format(row.question), frappe.DoesNotExistError)
			if not question.is_active:
				frappe.throw(_("CBT Question {0} is inactive.").format(row.question), frappe.ValidationError)
			if question.school_branch != self.school_branch:
				frappe.throw(_("Every CBT question must belong to the selected branch."), frappe.ValidationError)
			if question.course != self.course:
				frappe.throw(_("Every CBT question must belong to the selected Course / Subject."), frappe.ValidationError)
			row.sequence = index
			row.marks = flt(row.marks or question.default_marks)
			if row.marks <= 0:
				frappe.throw(_("Marks must be greater than zero for every CBT question."), frappe.ValidationError)
			total_marks += row.marks
		self.total_questions = len(self.questions)
		self.total_marks = total_marks
