from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt.public_access import require_public_exam_assignment
from eduedge.cbt.schedule_governance import (
	assert_check_in_window,
	assert_manual_release_window,
	write_lifecycle_log,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
STUDENT_CANDIDATE = "EduEdge Student"
PUBLIC_CANDIDATE = "Public Candidate Reference"

ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Eligible", "Withdrawn"},
	"Eligible": {"Eligible", "Checked In", "Released", "Withdrawn", "Disqualified"},
	"Checked In": {"Checked In", "Released", "Withdrawn", "Disqualified"},
	"Released": {"Released", "Completed", "Disqualified"},
	"Completed": {"Completed"},
	"Withdrawn": {"Withdrawn"},
	"Disqualified": {"Disqualified"},
}

IDENTITY_FIELDS = (
	"exam_schedule",
	"exam_template",
	"exam_scope",
	"school_branch",
	"course",
	"candidate_type",
	"student",
	"student_name",
	"public_candidate_reference",
	"candidate_name",
	"student_group",
	"eligibility_source",
	"approved_extra_time_minutes",
	"access_start",
	"access_end",
)

REASONED_STATUSES = {"Withdrawn", "Disqualified"}


class EduEdgeCBTCandidateAssignment(Document):
	def validate(self) -> None:
		self._validate_schedule()
		self._apply_schedule_context()
		self._validate_candidate_identity()
		self._validate_school_eligibility()
		self._validate_extra_time()
		self._calculate_access_window()
		self._validate_duplicate_assignment()
		self._validate_status_transition()
		self._prevent_identity_mutation()

	def on_update(self) -> None:
		before = self.get_doc_before_save()
		if not before or before.assignment_status == self.assignment_status:
			return
		write_lifecycle_log(
			reference_doctype=self.doctype,
			reference_name=self.name,
			exam_schedule=self.exam_schedule,
			candidate_assignment=self.name,
			exam_scope=self.exam_scope,
			school_branch=self.school_branch,
			event_type="Candidate Status Change",
			from_status=before.assignment_status,
			to_status=self.assignment_status,
			reason=getattr(self, "_lifecycle_reason", None) or self.status_change_reason,
		)

	def on_trash(self) -> None:
		if self.assignment_status not in {"Draft", "Withdrawn"}:
			frappe.throw(
				_("Only Draft or Withdrawn candidate assignments can be deleted."),
				frappe.ValidationError,
			)
		schedule_status = frappe.db.get_value("EduEdge CBT Exam Schedule", self.exam_schedule, "status")
		if schedule_status in {"Active", "Suspended", "Completed"}:
			frappe.throw(
				_("Candidate assignments cannot be deleted after the Examination Schedule is activated."),
				frappe.ValidationError,
			)

	def _validate_schedule(self) -> None:
		if not self.exam_schedule:
			frappe.throw(_("Examination Schedule is required."), frappe.ValidationError)
		schedule = frappe.db.get_value(
			"EduEdge CBT Exam Schedule",
			self.exam_schedule,
			[
				"name",
				"status",
				"exam_template",
				"exam_scope",
				"school_branch",
				"course",
				"student_group",
				"scheduled_start",
				"scheduled_end",
				"check_in_opens_at",
				"require_candidate_check_in",
				"candidate_start_mode",
				"allow_late_entry",
				"late_entry_grace_minutes",
			],
			as_dict=True,
		)
		if not schedule:
			frappe.throw(_("The selected Examination Schedule does not exist."), frappe.ValidationError)
		before = self.get_doc_before_save()
		if not before and schedule.status not in {"Draft", "Ready"}:
			frappe.throw(
				_("New candidates can be assigned only while the Examination Schedule is Draft or Ready."),
				frappe.ValidationError,
			)
		self._schedule = schedule

	def _apply_schedule_context(self) -> None:
		schedule = self._schedule
		self.exam_template = schedule.exam_template
		self.exam_scope = schedule.exam_scope
		self.school_branch = schedule.school_branch
		self.course = schedule.course
		self.student_group = schedule.student_group

	def _validate_candidate_identity(self) -> None:
		if self.exam_scope == SCHOOL_EXAM:
			self.candidate_type = STUDENT_CANDIDATE
			if not self.student:
				frappe.throw(_("Student is required for a School Examination candidate."), frappe.ValidationError)
			student = frappe.db.get_value(
				"Student",
				self.student,
				["name", "student_name", BRANCH_FIELD],
				as_dict=True,
			)
			if not student:
				frappe.throw(_("Select a valid Student."), frappe.ValidationError)
			assert_branch_access(self.school_branch)
			if student.get(BRANCH_FIELD) != self.school_branch:
				frappe.throw(
					_("Student must belong to the Examination Schedule Branch / Campus."),
					frappe.ValidationError,
				)
			self.student_name = student.student_name
			self.candidate_name = student.student_name
			self.public_candidate_reference = None
			self.eligibility_source = "Schedule Student Group" if self.student_group else "Manual School Assignment"
			return

		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_assignment(
				reference_doctype="EduEdge CBT Exam Schedule",
				reference_name=self.exam_schedule,
			)
			self.candidate_type = PUBLIC_CANDIDATE
			self.student = None
			self.student_name = None
			self.school_branch = None
			self.student_group = None
			self.eligibility_source = "CoreEdge Public Assignment"
			self.public_candidate_reference = (self.public_candidate_reference or "").strip()
			self.candidate_name = (self.candidate_name or "").strip()
			if not self.public_candidate_reference or not self.candidate_name:
				frappe.throw(
					_("Public Candidate Reference and Candidate Name are required."),
					frappe.ValidationError,
				)
			return

		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	def _validate_school_eligibility(self) -> None:
		if self.exam_scope != SCHOOL_EXAM or not self.student_group:
			return
		if not frappe.db.exists(
			"Student Group Student",
			{"parent": self.student_group, "student": self.student, "active": 1},
		):
			frappe.throw(
				_("Student is not an active member of the Student Group / Class selected on the Schedule."),
				frappe.ValidationError,
			)

	def _validate_extra_time(self) -> None:
		if cint(self.approved_extra_time_minutes) < 0:
			frappe.throw(_("Approved Extra Time cannot be negative."), frappe.ValidationError)

	def _calculate_access_window(self) -> None:
		schedule = self._schedule
		self.access_start = schedule.scheduled_start
		self.access_end = get_datetime(schedule.scheduled_end) + timedelta(
			minutes=cint(self.approved_extra_time_minutes)
		)

	def _validate_duplicate_assignment(self) -> None:
		filters = {"exam_schedule": self.exam_schedule}
		if self.exam_scope == SCHOOL_EXAM:
			filters["student"] = self.student
		else:
			filters["public_candidate_reference"] = self.public_candidate_reference
		duplicate = frappe.db.get_value("EduEdge CBT Candidate Assignment", filters, "name")
		if duplicate and duplicate != self.name:
			frappe.throw(
				_("This candidate is already assigned to the selected Examination Schedule."),
				frappe.DuplicateEntryError,
			)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.assignment_status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.assignment_status not in allowed:
			frappe.throw(
				_("Candidate Assignment Status cannot change from {0} to {1}.").format(
					previous_status, self.assignment_status
				),
				frappe.ValidationError,
			)
		if self.assignment_status == previous_status:
			return

		schedule_status = self._schedule.status
		if self.assignment_status == "Eligible" and schedule_status not in {"Draft", "Ready"}:
			frappe.throw(_("Candidate eligibility must be confirmed before the Schedule is activated."), frappe.ValidationError)
		if self.assignment_status == "Checked In":
			if schedule_status not in {"Ready", "Active"}:
				frappe.throw(_("Candidate check-in requires a Ready or Active Schedule."), frappe.ValidationError)
			assert_check_in_window(self._schedule)
		if self.assignment_status == "Released":
			if not getattr(self.flags, "eduedge_attempt_engine_release", False):
				assert_manual_release_window(self._schedule, previous_status)
		if self.assignment_status == "Completed" and schedule_status not in {"Active", "Suspended", "Completed"}:
			frappe.throw(_("Candidate completion requires an activated Schedule."), frappe.ValidationError)

		if self.assignment_status in REASONED_STATUSES:
			reason = (self.status_change_reason or "").strip()
			if not reason or (before and reason == (before.status_change_reason or "").strip()):
				frappe.throw(_("Enter a new reason for this candidate lifecycle action."), frappe.ValidationError)
		else:
			reason = {
				"Eligible": "Candidate eligibility confirmed.",
				"Checked In": "Candidate check-in confirmed.",
				"Released": "Candidate released by the authorised start policy.",
				"Completed": "Candidate sitting marked complete.",
			}.get(self.assignment_status, "Candidate lifecycle updated.")
			self.status_change_reason = reason
		self._lifecycle_reason = reason

		if self.assignment_status == "Eligible" and previous_status == "Draft":
			self.assigned_by = frappe.session.user
			self.assigned_on = now_datetime()
		if self.assignment_status == "Checked In" and previous_status == "Eligible":
			self.checked_in_by = frappe.session.user
			self.checked_in_on = now_datetime()

	def _prevent_identity_mutation(self) -> None:
		before = self.get_doc_before_save()
		if not before or before.assignment_status == "Draft":
			return
		controlled_extension = bool(getattr(self.flags, "eduedge_time_extension", False))
		for fieldname in IDENTITY_FIELDS:
			if before.get(fieldname) == self.get(fieldname):
				continue
			if controlled_extension and fieldname in {"approved_extra_time_minutes", "access_end"}:
				continue
			frappe.throw(
				_("An eligible Candidate Assignment is immutable. Record permitted exceptions through an intervention."),
				frappe.ValidationError,
			)
