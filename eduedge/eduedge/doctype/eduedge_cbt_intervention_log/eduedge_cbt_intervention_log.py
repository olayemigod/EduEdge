from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from eduedge.cbt.public_access import require_public_exam_capability
from eduedge.education.offerings import assert_branch_access

INTERVENTION_TYPES = {
	"Device Change",
	"Time Extension",
	"Force Submission",
	"Attempt Unlock",
	"Attempt Suspension",
	"Reconnection Approval",
	"Manual Sync Resolution",
	"Candidate Reassignment",
	"Other",
}


class EduEdgeCBTInterventionLog(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(
				_("CBT Intervention Logs are append-only and cannot be edited."),
				frappe.ValidationError,
			)
		self._validate_assignment()
		self._validate_intervention()
		self.acted_by = frappe.session.user
		self.acted_on = now_datetime()
		self.requires_attempt_review = 1

	def on_trash(self) -> None:
		frappe.throw(
			_("CBT Intervention Logs are append-only and cannot be deleted."),
			frappe.ValidationError,
		)

	def _validate_assignment(self) -> None:
		if not self.candidate_assignment:
			frappe.throw(_("Candidate Assignment is required."), frappe.ValidationError)
		assignment = frappe.db.get_value(
			"EduEdge CBT Candidate Assignment",
			self.candidate_assignment,
			[
				"exam_schedule",
				"exam_scope",
				"school_branch",
				"student",
				"public_candidate_reference",
				"assignment_status",
			],
			as_dict=True,
		)
		if not assignment:
			frappe.throw(_("Select a valid Candidate Assignment."), frappe.ValidationError)
		self.exam_schedule = assignment.exam_schedule
		self.exam_scope = assignment.exam_scope
		self.school_branch = assignment.school_branch
		self.student = assignment.student
		self.public_candidate_reference = assignment.public_candidate_reference
		self.candidate_status_snapshot = assignment.assignment_status
		if assignment.school_branch:
			assert_branch_access(assignment.school_branch)
		else:
			require_public_exam_capability(
				"assign",
				reference_doctype="EduEdge CBT Candidate Assignment",
				reference_name=self.candidate_assignment,
			)
		if assignment.assignment_status in {"Completed", "Withdrawn", "Disqualified"} and self.intervention_type not in {
			"Manual Sync Resolution",
			"Other",
		}:
			frappe.throw(
				_("The selected intervention is not allowed for a terminal candidate assignment."),
				frappe.ValidationError,
			)
		self._assignment = assignment

	def _validate_intervention(self) -> None:
		if self.intervention_type not in INTERVENTION_TYPES:
			frappe.throw(_("Select a valid Intervention Type."), frappe.ValidationError)
		self.reason = (self.reason or "").strip()
		if not self.reason:
			frappe.throw(_("A reason is required for every CBT intervention."), frappe.ValidationError)
		if self.intervention_type == "Time Extension":
			self._validate_time_extension()
		else:
			self.additional_minutes = 0
		if self.intervention_type == "Force Submission":
			allowed = frappe.db.get_value(
				"EduEdge CBT Exam Schedule",
				self.exam_schedule,
				"allow_invigilator_force_submit",
			)
			if not cint(allowed):
				frappe.throw(
					_("Force Submission is not permitted for this Examination Schedule."),
					frappe.PermissionError,
				)

	def _validate_time_extension(self) -> None:
		if cint(self.additional_minutes) <= 0:
			frappe.throw(_("Additional Minutes must be greater than zero."), frappe.ValidationError)
		policy = frappe.db.get_value(
			"EduEdge CBT Exam Schedule",
			self.exam_schedule,
			["allow_invigilator_time_extension", "maximum_time_extension_minutes"],
			as_dict=True,
		)
		if not policy or not cint(policy.allow_invigilator_time_extension):
			frappe.throw(
				_("Time Extension is not permitted for this Examination Schedule."),
				frappe.PermissionError,
			)
		if cint(self.additional_minutes) > cint(policy.maximum_time_extension_minutes):
			frappe.throw(
				_("Additional Minutes exceed the maximum permitted by the Examination Schedule."),
				frappe.ValidationError,
			)
