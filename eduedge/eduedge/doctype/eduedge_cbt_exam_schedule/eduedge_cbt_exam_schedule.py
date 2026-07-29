from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.cbt.schedule_governance import (
	assert_fields_mutable_after_candidate_confirmation,
	assert_user_branch_access,
	validate_activation_readiness,
	validate_course_scope,
	write_lifecycle_log,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.eduedge.doctype.eduedge_cbt_exam_template.eduedge_cbt_exam_template import (
	MODE_FIXED,
	PUBLIC_EXAM,
	REUSE_BRANCH,
	REUSE_INSTITUTION,
	REUSE_UNIVERSAL,
	SCHOOL_EXAM,
	SUBJECT_ANY,
	SUBJECT_SPECIFIC,
)

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

REASONED_TRANSITIONS = {
	("Ready", "Draft"),
	("Active", "Suspended"),
	("Suspended", "Active"),
	("Active", "Completed"),
	("Suspended", "Completed"),
	("Draft", "Cancelled"),
	("Ready", "Cancelled"),
	("Active", "Cancelled"),
	("Suspended", "Cancelled"),
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

ACADEMIC_CONTEXT_FIELDS = (
	"student_group",
	"academic_year",
	"academic_term",
	"program",
	"assessment_group",
)

PROTECTED_AFTER_CANDIDATE_CONFIRMATION = (
	"schedule_code",
	"exam_template",
	"exam_scope",
	"school_branch",
	"course",
	*ACADEMIC_CONTEXT_FIELDS,
	"examination_centre",
	"scheduled_start",
	"scheduled_end",
	"check_in_opens_at",
	"require_candidate_check_in",
	"candidate_start_mode",
	"allow_late_entry",
	"late_entry_grace_minutes",
	"allow_invigilator_time_extension",
	"maximum_time_extension_minutes",
	"allow_invigilator_force_submit",
	*SNAPSHOT_FIELDS,
)

PROTECTED_AFTER_ACTIVATION = (
	"schedule_title",
	"schedule_code",
	"exam_template",
	"exam_scope",
	"school_branch",
	"course",
	*ACADEMIC_CONTEXT_FIELDS,
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

INVIGILATOR_ROLES = {
	"CBT Invigilator",
	"Teacher",
	"Instructor",
	"Education Manager",
	"Academic Administrator",
	"School Administrator",
	"EduEdge Administrator",
	"EduEdge Super Administrator",
}


class EduEdgeCBTExamSchedule(Document):
	def validate(self) -> None:
		self.schedule_code = (self.schedule_code or "").strip().upper()
		self.schedule_title = (self.schedule_title or "").strip()
		self._validate_identity()
		template = self._get_schedulable_template()
		self._apply_template_context_and_snapshot(template)
		self._validate_scope()
		self._validate_template_applicability(template)
		self._validate_academic_context()
		self._validate_centre()
		self._validate_timing()
		self._validate_operational_policy()
		self._validate_status_transition()
		assert_fields_mutable_after_candidate_confirmation(
			self,
			self.get_doc_before_save(),
			PROTECTED_AFTER_CANDIDATE_CONFIRMATION,
		)
		self._prevent_active_schedule_mutation()
		validate_activation_readiness(self)

	def on_update(self) -> None:
		before = self.get_doc_before_save()
		if not before or before.status == self.status:
			return
		write_lifecycle_log(
			reference_doctype=self.doctype,
			reference_name=self.name,
			exam_schedule=self.name,
			exam_scope=self.exam_scope,
			school_branch=self.school_branch,
			event_type="Schedule Status Change",
			from_status=before.status,
			to_status=self.status,
			reason=getattr(self, "_lifecycle_reason", None) or self.status_change_reason,
		)

	def on_trash(self) -> None:
		if self.status not in {"Draft", "Cancelled"}:
			frappe.throw(
				_("Only Draft or Cancelled examination schedules can be deleted."),
				frappe.ValidationError,
			)
		if frappe.db.exists("EduEdge CBT Candidate Assignment", {"exam_schedule": self.name}):
			frappe.throw(
				_("Delete or resolve Candidate Assignments before deleting this Schedule."),
				frappe.ValidationError,
			)

	def _validate_identity(self) -> None:
		if not self.schedule_code:
			frappe.throw(_("Schedule Code is required."), frappe.ValidationError)
		if not self.schedule_title:
			frappe.throw(_("Schedule Title is required."), frappe.ValidationError)
		if not self.exam_template:
			frappe.throw(_("Approved Fixed Question Set is required."), frappe.ValidationError)

	def _get_schedulable_template(self):
		template = frappe.get_doc("EduEdge CBT Exam Template", self.exam_template)
		template.check_permission("read")
		before = self.get_doc_before_save()
		if template.status == "Retired":
			if not before or before.exam_template != template.name or before.status not in {
				"Ready",
				"Active",
				"Suspended",
				"Completed",
				"Cancelled",
			}:
				frappe.throw(
					_("A Retired Template may be retained only by a Schedule that already referenced that exact version."),
					frappe.ValidationError,
				)
		elif template.status != "Approved":
			frappe.throw(_("Select an Approved CBT Exam Template."), frappe.ValidationError)
		if template.template_mode != MODE_FIXED:
			frappe.throw(
				_(
					"Policy Blueprint scheduling is disabled until rule-based question generation and an immutable generated-question snapshot are implemented. Select an Approved Fixed Question Set."
				),
				frappe.ValidationError,
			)
		return template

	def _apply_template_context_and_snapshot(self, template) -> None:
		before = self.get_doc_before_save()
		if before and before.status not in {"Draft", "Ready"}:
			return
		template_changed = not before or before.exam_template != template.name
		self.exam_scope = template.exam_scope
		if template.exam_scope == SCHOOL_EXAM and template.template_reuse_scope == REUSE_BRANCH:
			self.school_branch = template.school_branch
		elif template.exam_scope == PUBLIC_EXAM:
			self.school_branch = None
			for fieldname in ACADEMIC_CONTEXT_FIELDS:
				self.set(fieldname, None)

		if template.subject_applicability == SUBJECT_SPECIFIC:
			self.course = template.course
		elif template_changed:
			self.course = None

		if template_changed:
			for fieldname in ACADEMIC_CONTEXT_FIELDS:
				self.set(fieldname, None)
			self.examination_centre = template.default_examination_centre or None
		if template.exam_scope == SCHOOL_EXAM:
			self._apply_compatible_academic_defaults(template)
		for fieldname in SNAPSHOT_FIELDS:
			self.set(fieldname, template.get(fieldname))

	def _apply_compatible_academic_defaults(self, template) -> None:
		for fieldname in ("academic_year", "academic_term", "program", "assessment_group"):
			if not self.get(fieldname) and template.get(fieldname):
				self.set(fieldname, template.get(fieldname))
		if self.student_group or not template.student_group or not self.school_branch:
			return
		group_branch = frappe.db.get_value("Student Group", template.student_group, BRANCH_FIELD)
		if group_branch == self.school_branch:
			self.student_group = template.student_group

	def _validate_scope(self) -> None:
		if self.exam_scope == SCHOOL_EXAM:
			if not self.school_branch:
				frappe.throw(
					_("A School Examination Schedule requires a School Branch / Campus."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			if not self.course:
				frappe.throw(_("A School Examination Schedule requires a Subject / Course."), frappe.ValidationError)
			validate_course_scope(self.course, self.school_branch)
			return
		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()
			if self.school_branch:
				frappe.throw(
					_("Centrally authored public examination Schedules cannot carry a local School Branch."),
					frappe.ValidationError,
				)
			if not self.course:
				frappe.throw(_("A public examination Schedule requires a Subject / Course."), frappe.ValidationError)
			return
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	def _validate_template_applicability(self, template) -> None:
		if template.exam_scope != self.exam_scope:
			frappe.throw(_("The selected Template does not match the Schedule Examination Scope."), frappe.ValidationError)
		if template.subject_applicability == SUBJECT_SPECIFIC and self.course != template.course:
			frappe.throw(_("The Schedule Subject must match the Specific Subject Template."), frappe.ValidationError)
		if template.subject_applicability == SUBJECT_ANY and not self.course:
			frappe.throw(_("Select the actual Subject / Course for this Schedule."), frappe.ValidationError)
		if self.exam_scope != SCHOOL_EXAM:
			return

		branch = frappe.db.get_value(
			"EduEdge School Branch",
			self.school_branch,
			["company", "institution", "enabled"],
			as_dict=True,
		)
		if not branch or not cint(branch.enabled):
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		if template.template_reuse_scope == REUSE_BRANCH and self.school_branch != template.school_branch:
			frappe.throw(_("This Branch-wide Template cannot be used by another Branch."), frappe.PermissionError)
		if template.template_reuse_scope == REUSE_INSTITUTION and branch.institution != template.institution:
			frappe.throw(_("This Institution-wide Template cannot be used outside its Institution."), frappe.PermissionError)
		if template.template_reuse_scope == REUSE_UNIVERSAL and branch.company != template.company:
			frappe.throw(_("This Universal Template cannot be used outside its Company."), frappe.PermissionError)

	def _validate_academic_context(self) -> None:
		if self.exam_scope != SCHOOL_EXAM:
			return
		if self.academic_term:
			if not self.academic_year:
				frappe.throw(_("Select Academic Year before Academic Term."), frappe.ValidationError)
			actual_year = frappe.db.get_value("Academic Term", self.academic_term, "academic_year")
			if actual_year and actual_year != self.academic_year:
				frappe.throw(_("Academic Term does not belong to the selected Academic Year."), frappe.ValidationError)
		if not self.student_group:
			return
		group = frappe.db.get_value(
			"Student Group",
			self.student_group,
			["name", BRANCH_FIELD, "academic_year", "academic_term", "program", "course", "disabled"],
			as_dict=True,
		)
		if not group or cint(group.disabled):
			frappe.throw(_("Select an enabled Student Group / Class."), frappe.ValidationError)
		if group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Student Group / Class must belong to the Schedule Branch."), frappe.ValidationError)
		for fieldname, label in (
			("academic_year", _("Academic Year")),
			("academic_term", _("Academic Term")),
			("program", _("Programme")),
		):
			group_value = group.get(fieldname)
			if self.get(fieldname) and group_value and self.get(fieldname) != group_value:
				frappe.throw(_("Student Group / Class must match the Schedule {0}.").format(label), frappe.ValidationError)
			if not self.get(fieldname) and group_value:
				self.set(fieldname, group_value)
		if group.course and group.course != self.course:
			frappe.throw(_("Student Group / Class Subject must match the Schedule Subject / Course."), frappe.ValidationError)

	def _validate_centre(self) -> None:
		if not self.examination_centre:
			frappe.throw(_("Examination Centre is required."), frappe.ValidationError)
		centre = frappe.db.get_value(
			"EduEdge Examination Centre",
			self.examination_centre,
			["centre_type", "school_branch", "centre_status", "enabled"],
			as_dict=True,
		)
		if not centre or centre.centre_status != "Active" or not cint(centre.enabled):
			frappe.throw(_("Select an enabled Active Examination Centre."), frappe.ValidationError)
		if self.exam_scope == SCHOOL_EXAM:
			if centre.centre_type != SCHOOL_CENTRE or centre.school_branch != self.school_branch:
				frappe.throw(
					_("The Examination Centre must be an Active School Examination Centre in the selected Branch."),
					frappe.ValidationError,
				)
			return
		if centre.centre_type != PLATFORM_CENTRE or centre.school_branch:
			frappe.throw(
				_("A centrally authored public Schedule must use an EduEdge Exam Centre."),
				frappe.ValidationError,
			)

	def _validate_timing(self) -> None:
		if not self.scheduled_start:
			frappe.throw(_("Scheduled Start is required."), frappe.ValidationError)
		start = get_datetime(self.scheduled_start)
		duration = cint(self.duration_minutes)
		if duration <= 0:
			frappe.throw(_("The approved Template must provide a positive Duration."), frappe.ValidationError)
		self.scheduled_end = start + timedelta(minutes=duration)
		if self.check_in_opens_at and get_datetime(self.check_in_opens_at) > start:
			frappe.throw(_("Check-in Opens At cannot be later than Scheduled Start."), frappe.ValidationError)
		grace = cint(self.late_entry_grace_minutes)
		if grace < 0:
			frappe.throw(_("Late Entry Grace cannot be negative."), frappe.ValidationError)
		if not cint(self.allow_late_entry):
			self.late_entry_grace_minutes = 0
		elif grace >= duration:
			frappe.throw(_("Late Entry Grace must be shorter than the examination Duration."), frappe.ValidationError)

	def _validate_operational_policy(self) -> None:
		if self.candidate_start_mode not in {
			"Candidate Starts After Check-in",
			"Invigilator Releases Candidates",
			"Automatic Start at Scheduled Time",
		}:
			frappe.throw(_("Select a valid Candidate Start Mode."), frappe.ValidationError)
		if not cint(self.require_candidate_check_in) and self.candidate_start_mode == "Candidate Starts After Check-in":
			frappe.throw(
				_("Candidate Starts After Check-in requires Candidate Check-in to be enabled."),
				frappe.ValidationError,
			)
		self._validate_primary_invigilator()
		if self.status in {"Ready", "Active"} and not self.primary_invigilator:
			frappe.throw(_("Assign a Primary Invigilator before the Schedule becomes Ready."), frappe.ValidationError)
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
		if not set(frappe.get_roles(self.primary_invigilator)).intersection(INVIGILATOR_ROLES):
			frappe.throw(
				_("Primary Invigilator must hold an authorised examination or academic role."),
				frappe.PermissionError,
			)
		if self.exam_scope == SCHOOL_EXAM:
			assert_user_branch_access(self.primary_invigilator, self.school_branch, _("Primary Invigilator"))

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Examination Schedule Status cannot change from {0} to {1}.").format(previous_status, self.status),
				frappe.ValidationError,
			)
		if self.status == previous_status:
			return
		transition = (previous_status, self.status)
		if transition in REASONED_TRANSITIONS:
			reason = (self.status_change_reason or "").strip()
			if not reason or (before and reason == (before.status_change_reason or "").strip()):
				frappe.throw(_("Enter a new reason for this lifecycle action."), frappe.ValidationError)
		else:
			reason = (
				"Schedule readiness confirmed."
				if transition == ("Draft", "Ready")
				else "Schedule activated after readiness checks."
			)
			self.status_change_reason = reason
		self._lifecycle_reason = reason
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
					_("An activated Examination Schedule is immutable. Use an audited candidate intervention for permitted exceptions."),
					frappe.ValidationError,
				)


def exam_schedule_query(user: str | None = None) -> str:
	from eduedge.cbt.permissions import _school_branch_condition

	return _school_branch_condition("EduEdge CBT Exam Schedule", user)


def has_exam_schedule_permission(doc, user=None, permission_type=None) -> bool:
	from eduedge.cbt.permissions import has_school_branch_permission

	return has_school_branch_permission(doc, user=user, permission_type=permission_type)
