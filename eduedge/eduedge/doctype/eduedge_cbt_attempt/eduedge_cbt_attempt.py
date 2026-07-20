from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime

ACTIVE_ATTEMPT_STATUSES = {"In Progress", "Pending Sync"}
FINAL_ATTEMPT_STATUSES = {"Submitted", "Timed Out", "Cancelled"}
ALLOWED_ATTEMPT_TRANSITIONS = {
	"Not Started": {"In Progress", "Cancelled"},
	"In Progress": {"Pending Sync", "Submitted", "Timed Out", "Cancelled"},
	"Pending Sync": {"Submitted", "Timed Out", "Cancelled"},
	"Submitted": set(),
	"Timed Out": set(),
	"Cancelled": set(),
}
IMMUTABLE_FIELDS = (
	"exam",
	"student",
	"user",
	"school_branch",
	"student_group",
	"course",
	"attempt_no",
	"started_on",
	"server_deadline",
	"sync_grace_ends_on",
	"random_seed",
	"question_snapshot",
)


class EduEdgeCBTAttempt(Document):
	def validate(self) -> None:
		self._require_service_mutation()
		self._validate_exam_scope()
		self._validate_candidate()
		self._validate_attempt_number()
		self._validate_active_attempt_uniqueness()
		self._validate_timing()
		self._validate_transition()
		self._validate_immutable_fields()
		self._validate_snapshot()

	def on_trash(self) -> None:
		if self.status not in {"Not Started", "Cancelled"}:
			frappe.throw(_("Started CBT Attempts cannot be deleted."), frappe.ValidationError)
		if frappe.db.exists("EduEdge CBT Attempt Answer", {"attempt": self.name}):
			frappe.throw(_("A CBT Attempt with answer history cannot be deleted."), frappe.ValidationError)

	def _require_service_mutation(self) -> None:
		if not self.flags.get("from_cbt_service"):
			frappe.throw(
				_("CBT Attempts are managed by the EduEdge CBT engine and cannot be edited directly."),
				frappe.PermissionError,
			)

	def _validate_exam_scope(self) -> None:
		exam = frappe.db.get_value(
			"EduEdge CBT Exam",
			self.exam,
			["school_branch", "student_group", "course", "total_questions", "status"],
			as_dict=True,
		)
		if not exam:
			frappe.throw(_("CBT Exam was not found."), frappe.DoesNotExistError)
		for fieldname in ("school_branch", "student_group", "course"):
			if self.get(fieldname) != exam.get(fieldname):
				frappe.throw(_("CBT Attempt does not match the exam {0}.").format(self.meta.get_label(fieldname)), frappe.ValidationError)
		if cint(self.total_questions) != cint(exam.total_questions):
			frappe.throw(_("CBT Attempt question count does not match the exam."), frappe.ValidationError)

	def _validate_candidate(self) -> None:
		if not frappe.db.exists(
			"Student Group Student",
			{
				"parent": self.student_group,
				"parenttype": "Student Group",
				"student": self.student,
				"active": 1,
			},
		):
			frappe.throw(_("Student is not an active member of the selected class."), frappe.PermissionError)
		student_email = frappe.db.get_value("Student", self.student, "student_email_id")
		if self.user != student_email:
			frappe.throw(_("CBT Attempt user does not match the Student portal account."), frappe.PermissionError)
		if frappe.session.user != "Administrator" and "Student" in frappe.get_roles(frappe.session.user):
			if self.user != frappe.session.user:
				frappe.throw(_("Students can only access their own CBT Attempt."), frappe.PermissionError)

	def _validate_attempt_number(self) -> None:
		if cint(self.attempt_no) < 1:
			frappe.throw(_("CBT Attempt Number must be at least 1."), frappe.ValidationError)
		duplicate = frappe.db.exists(
			self.doctype,
			{
				"name": ["!=", self.name],
				"exam": self.exam,
				"student": self.student,
				"attempt_no": cint(self.attempt_no),
			},
		)
		if duplicate:
			frappe.throw(_("CBT Attempt {0} already uses this attempt number.").format(duplicate), frappe.DuplicateEntryError)

	def _validate_active_attempt_uniqueness(self) -> None:
		if self.status not in ACTIVE_ATTEMPT_STATUSES:
			return
		active = frappe.db.exists(
			self.doctype,
			{
				"name": ["!=", self.name],
				"exam": self.exam,
				"student": self.student,
				"status": ["in", sorted(ACTIVE_ATTEMPT_STATUSES)],
			},
		)
		if active:
			frappe.throw(_("Student already has active CBT Attempt {0}.").format(active), frappe.ValidationError)

	def _validate_timing(self) -> None:
		if self.status == "Not Started":
			return
		if not self.started_on or not self.server_deadline:
			frappe.throw(_("Started CBT Attempts require server start and deadline values."), frappe.ValidationError)
		started_on = get_datetime(self.started_on)
		deadline = get_datetime(self.server_deadline)
		grace_end = get_datetime(self.sync_grace_ends_on) if self.sync_grace_ends_on else deadline
		if deadline <= started_on:
			frappe.throw(_("CBT server deadline must be after the start time."), frappe.ValidationError)
		if grace_end < deadline:
			frappe.throw(_("CBT sync grace cannot end before the server deadline."), frappe.ValidationError)

	def _validate_transition(self) -> None:
		if self.is_new():
			if self.status not in {"Not Started", "In Progress"}:
				frappe.throw(_("New CBT Attempts must start as Not Started or In Progress."), frappe.ValidationError)
			return
		previous_status = frappe.db.get_value(self.doctype, self.name, "status") or "Not Started"
		if previous_status == self.status:
			return
		if self.status not in ALLOWED_ATTEMPT_TRANSITIONS.get(previous_status, set()):
			frappe.throw(
				_("CBT Attempt cannot move from {0} to {1}.").format(previous_status, self.status),
				frappe.ValidationError,
			)

	def _validate_immutable_fields(self) -> None:
		if self.is_new():
			return
		for fieldname in IMMUTABLE_FIELDS:
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("{0} is immutable after a CBT Attempt starts.").format(self.meta.get_label(fieldname)),
					frappe.ValidationError,
				)

	def _validate_snapshot(self) -> None:
		if self.status == "Not Started":
			return
		if len(self.question_snapshot or []) != cint(self.total_questions):
			frappe.throw(_("CBT Attempt requires a complete immutable question snapshot."), frappe.ValidationError)
		keys = [row.snapshot_key for row in self.question_snapshot]
		if not all(keys) or len(keys) != len(set(keys)):
			frappe.throw(_("CBT Attempt question snapshot keys must be unique."), frappe.ValidationError)
