from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.education.offerings import assert_branch_access

SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"

ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Ready", "Cancelled"},
	"Ready": {"Draft", "Ready", "Active", "Cancelled"},
	"Active": {"Active", "Suspended", "Completed", "Cancelled"},
	"Suspended": {"Suspended", "Active", "Completed", "Cancelled"},
	"Completed": {"Completed"},
	"Cancelled": {"Cancelled"},
}

SNAPSHOT_FIELDS = (
	"duration_minutes",
	"maximum_attempts",
	"pass_percentage",
	"navigation_policy",
	"auto_submit_on_timeout",
	"allow_resume",
	"randomise_questions",
	"randomise_options",
	"marking_policy",
	"result_release_policy",
	"device_change_policy",
	"attempt_review_policy",
)

PROTECTED_AFTER_ACTIVATION = (
	"schedule_title",
	"schedule_code",
	"exam_template",
	"exam_scope",
	"school_branch",
	"course",
	"examination_centre",
	"scheduled_start",
	"scheduled_end",
	"check_in_opens_at",
	"require_candidate_check_in",
	"candidate_start_mode",
	"allow_late_entry",
	"late_entry_grace_minutes",
	"primary_invigilator",
	"allow_invigilator_time_extension",
	"maximum_time_extension_minutes",
	"allow_invigilator_force_submit",
	*SNAPSHOT_FIELDS,
)


class EduEdgeCBTExamSchedule(Document):
	def validate(self) -> None:
		self.schedule_code = (self.schedule_code or "").strip().upper()
		self.schedule_title = (self.schedule_title or "").strip()
		self._validate_identity()
		template = self._get_approved_template()
		self._apply_template_context_and_snapshot(template)
		self._validate_scope()
		self._validate_centre()
		self._validate_timing()
		self._validate_operational_policy()
		self._validate_status_transition()
		self._prevent_active_schedule_mutation()

	def on_trash(self) -> None:
		if self.status not in {"Draft", "Cancelled"}:
			frappe.throw(
				_("Only Draft or Cancelled examination schedules can be deleted."),
				frappe.ValidationError,
			)

	def _validate_identity(self) -> None:
		if not self.schedule_code:
			frappe.throw(_("Schedule Code is required."), frappe.ValidationError)
		if not self.schedule_title:
			frappe.throw(_("Schedule Title is required."), frappe.ValidationError)
		if not self.exam_template:
			frappe.throw(_("Approved CBT Exam Template is required."), frappe.ValidationError)

	def _get_approved_template(self):
		template = frappe.db.get_value(
			"EduEdge CBT Exam Template",
			self.exam_template,
			[
				"name",
				"status",
				"exam_scope",
				"school_branch",
				"course",
				"default_examination_centre",
				*SNAPSHOT_FIELDS,
			],
			as_dict=True,
		)
		before = self.get_doc_before_save()
		allowed_statuses = {"Approved"}
		if before and before.status in {"Ready", "Active", "Suspended", "Completed", "Cancelled"}:
			allowed_statuses.add("Retired")
		if not template or template.status not in allowed_statuses:
			frappe.throw(
				_("Select an Approved CBT Exam Template."),
				frappe.ValidationError,
			)
		return template

	def _apply_template_context_and_snapshot(self, template) -> None:
		before = self.get_doc_before_save()
		should_refresh = not before or before.status in {"Draft", "Ready"}
		if not should_refresh:
			return
		self.exam_scope = template.exam_scope
		self.school_branch = template.school_branch
		self.course = template.course
		if not self.examination_centre and template.default_examination_centre:
			self.examination_centre = template.default_examination_centre
		for fieldname in SNAPSHOT_FIELDS:
			self.set(fieldname, template.get(fieldname))

	def _validate_scope(self) -> None:
		if self.exam_scope == SCHOOL_EXAM:
			if not self.school_branch:
				frappe.throw(
					_("A School Examination schedule requires a School Branch / Campus."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			return
		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()
			if self.school_branch:
				frappe.throw(
					_("Centrally authored public examination schedules cannot carry a local School Branch."),
					frappe.ValidationError,
				)
			return
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	def _validate_centre(self) -> None:
		if not self.examination_centre:
			frappe.throw(_("Examination Centre is required."), frappe.ValidationError)
		centre = frappe.db.get_value(
			"EduEdge Examination Centre",
			self.examination_centre,
			["centre_type", "school_branch", "centre_status", "enabled"],
			as_dict=True,
		)
		if not centre or (centre.centre_status != "Active" and not cint(centre.enabled)):
			frappe.throw(_("Select an Active Examination Centre."), frappe.ValidationError)
		if self.exam_scope == SCHOOL_EXAM:
			if centre.centre_type != SCHOOL_CENTRE or centre.school_branch != self.school_branch:
				frappe.throw(
					_("The examination centre must be an Active School Examination Centre in the selected Branch."),
					frappe.ValidationError,
				)
			return
		if centre.centre_type != PLATFORM_CENTRE or centre.school_branch:
			frappe.throw(
				_("A centrally authored public schedule must use an EduEdge Exam Centre."),
				frappe.ValidationError,
			)

	def _validate_timing(self) -> None:
		if not self.scheduled_start:
			frappe.throw(_("Scheduled Start is required."), frappe.ValidationError)
		start = get_datetime(self.scheduled_start)
		duration = cint(self.duration_minutes)
		if duration <= 0:
			frappe.throw(_("The approved exam template must provide a positive Duration."), frappe.ValidationError)
		self.scheduled_end = start + timedelta(minutes=duration)
		if self.check_in_opens_at and get_datetime(self.check_in_opens_at) > start:
			frappe.throw(_("Check-in Opens At cannot be later than Scheduled Start."), frappe.ValidationError)
		if cint(self.late_entry_grace_minutes) < 0:
			frappe.throw(_("Late Entry Grace cannot be negative."), frappe.ValidationError)
		if not cint(self.allow_late_entry):
			self.late_entry_grace_minutes = 0

	def _validate_operational_policy(self) -> None:
		if self.candidate_start_mode not in {
			"Candidate Starts After Check-in",
			"Invigilator Releases Candidates",
			"Automatic Start at Scheduled Time",
		}:
			frappe.throw(_("Select a valid Candidate Start Mode."), frappe.ValidationError)
		self._validate_primary_invigilator()
		if cint(self.require_candidate_check_in) and not self.primary_invigilator and self.status in {"Ready", "Active"}:
			frappe.throw(
				_("Primary Invigilator is required before a check-in controlled schedule can become Ready or Active."),
				frappe.ValidationError,
			)
		if cint(self.allow_invigilator_time_extension):
			if cint(self.maximum_time_extension_minutes) <= 0:
				frappe.throw(
					_("Maximum Time Extension must be greater than zero when extensions are allowed."),
					frappe.ValidationError,
				)
		else:
			self.maximum_time_extension_minutes = 0

	def _validate_primary_invigilator(self) -> None:
		if not self.primary_invigilator:
			return
		user = frappe.db.get_value("User", self.primary_invigilator, ["enabled", "user_type"], as_dict=True)
		if not user or not cint(user.enabled) or user.user_type != "System User":
			frappe.throw(_("Select an enabled System User as Primary Invigilator."), frappe.ValidationError)
		allowed_roles = {
			"CBT Invigilator",
			"Teacher",
			"Instructor",
			"Education Manager",
			"Academic Administrator",
			"School Administrator",
			"EduEdge Administrator",
			"EduEdge Super Administrator",
		}
		if not set(frappe.get_roles(self.primary_invigilator)).intersection(allowed_roles):
			frappe.throw(
				_("Primary Invigilator must hold an authorised examination or academic role."),
				frappe.PermissionError,
			)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Examination Schedule Status cannot change from {0} to {1}.").format(
					previous_status, self.status
				),
				frappe.ValidationError,
			)
		if self.status in {"Ready", "Active"} and not self.primary_invigilator and cint(self.require_candidate_check_in):
			frappe.throw(_("Assign a Primary Invigilator before the schedule becomes Ready."), frappe.ValidationError)
		if self.status == "Active" and previous_status == "Ready":
			self.activated_by = frappe.session.user
			self.activated_on = now_datetime()

	def _prevent_active_schedule_mutation(self) -> None:
		before = self.get_doc_before_save()
		if not before or before.status not in {"Active", "Suspended", "Completed", "Cancelled"}:
			return
		for fieldname in PROTECTED_AFTER_ACTIVATION:
			if before.get(fieldname) != self.get(fieldname):
				frappe.throw(
					_("An activated examination schedule is immutable. Use an audited intervention for candidate-specific exceptions."),
					frappe.ValidationError,
				)


def exam_schedule_query(user: str | None = None) -> str:
	from eduedge.cbt.permissions import _school_branch_condition

	return _school_branch_condition("EduEdge CBT Exam Schedule", user)


def has_exam_schedule_permission(doc, user=None, permission_type=None) -> bool:
	from eduedge.cbt.permissions import has_school_branch_permission

	return has_school_branch_permission(doc, user=user, permission_type=permission_type)
