from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime

from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.education.custom_fields import BRANCH_FIELD
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

ACADEMIC_CONTEXT_FIELDS = (
	"student_group",
	"academic_year",
	"academic_term",
	"assessment_group",
	"assessment_plan",
	"maximum_assessment_score",
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


class EduEdgeCBTExamSchedule(Document):
	def validate(self) -> None:
		self.schedule_code = (self.schedule_code or "").strip().upper()
		self.schedule_title = (self.schedule_title or "").strip()
		self._validate_identity()
		template = self._get_approved_template()
		self._apply_template_context_and_snapshot(template)
		self._validate_scope()
		self._validate_assessment_plan(template)
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
				"academic_year",
				"academic_term",
				"program",
				"student_group",
				"assessment_group",
				"total_marks",
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
		self.student_group = template.student_group
		self.academic_year = template.academic_year
		self.academic_term = template.academic_term
		self.assessment_group = template.assessment_group
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
			for fieldname in ACADEMIC_CONTEXT_FIELDS:
				self.set(fieldname, None)
			return
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	def _validate_assessment_plan(self, template) -> None:
		if self.exam_scope != SCHOOL_EXAM:
			return
		if self.status in {"Ready", "Active"} and not self.assessment_plan:
			frappe.throw(
				_("Select a submitted Assessment Plan before the School Examination schedule becomes Ready."),
				frappe.ValidationError,
			)
		if not self.assessment_plan:
			self.maximum_assessment_score = 0
			return

		plan = frappe.get_doc("Assessment Plan", self.assessment_plan)
		if not frappe.has_permission("Assessment Plan", "read", doc=plan):
			frappe.throw(_("You are not permitted to use this Assessment Plan."), frappe.PermissionError)
		if plan.docstatus != 1:
			frappe.throw(_("The Assessment Plan selected for CBT Result Sync must be submitted."), frappe.ValidationError)
		if plan.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Assessment Plan Branch must match the CBT Examination Schedule Branch."), frappe.ValidationError)
		if plan.course != self.course:
			frappe.throw(_("Assessment Plan Subject / Course must match the CBT Exam Template."), frappe.ValidationError)
		if not self.student_group or plan.student_group != self.student_group:
			frappe.throw(_("Assessment Plan Student Group must match the CBT Exam Template class."), frappe.ValidationError)

		for fieldname, label in (
			("academic_year", _("Academic Year")),
			("academic_term", _("Academic Term")),
			("assessment_group", _("Assessment Group")),
		):
			template_value = template.get(fieldname)
			plan_value = plan.get(fieldname)
			if template_value and plan_value != template_value:
				frappe.throw(
					_("Assessment Plan {0} must match the approved CBT Exam Template.").format(label),
					frappe.ValidationError,
				)

		criteria = list(plan.get("assessment_criteria") or [])
		if len(criteria) != 1:
			frappe.throw(
				_("CBT Result Sync V1.1 requires an Assessment Plan with exactly one Assessment Criterion."),
				frappe.ValidationError,
			)
		template_total = flt(template.total_marks)
		plan_total = flt(plan.maximum_assessment_score)
		criterion_total = flt(criteria[0].maximum_score)
		if not template_total or abs(plan_total - template_total) > 0.0001 or abs(criterion_total - plan_total) > 0.0001:
			frappe.throw(
				_("Assessment Plan maximum score and its single criterion must equal the approved CBT Template total marks."),
				frappe.ValidationError,
			)

		self.student_group = plan.student_group
		self.academic_year = plan.academic_year
		self.academic_term = plan.academic_term
		self.assessment_group = plan.assessment_group
		self.maximum_assessment_score = plan_total

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
