from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access

SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"
PLATFORM_MANAGER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}
REVIEW_ROLES = PLATFORM_MANAGER_ROLES | {
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}
ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Under Review", "Approved"},
	"Under Review": {"Draft", "Under Review", "Approved"},
	"Approved": {"Approved", "Retired"},
	"Retired": {"Retired"},
}
PROTECTED_FIELDS = (
	"template_title",
	"template_code",
	"exam_scope",
	"school_branch",
	"version_number",
	"supersedes_template",
	"academic_year",
	"academic_term",
	"program",
	"student_group",
	"course",
	"assessment_group",
	"exam_body",
	"default_examination_centre",
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
	"candidate_instructions",
)


class EduEdgeCBTExamTemplate(Document):
	def validate(self) -> None:
		self.template_code = (self.template_code or "").strip().upper()
		self.template_title = (self.template_title or "").strip()
		self._validate_identity()
		self._validate_scope()
		self._validate_academic_context()
		self._validate_examination_centre()
		self._validate_timing_and_policy()
		self._validate_version()
		self._validate_question_rows()
		self._validate_status_transition()
		self._prevent_approved_content_mutation()

	def on_trash(self) -> None:
		if self.status in {"Approved", "Retired"}:
			frappe.throw(
				_("Approved or Retired exam templates cannot be deleted."),
				frappe.ValidationError,
			)

	def _validate_identity(self) -> None:
		if not self.template_code:
			frappe.throw(_("Template Code is required."), frappe.ValidationError)
		if not self.template_title:
			frappe.throw(_("Template Title is required."), frappe.ValidationError)
		if not self.course:
			frappe.throw(_("Subject / Course is required."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.exam_scope == SCHOOL_EXAM:
			if not self.school_branch:
				frappe.throw(
					_("School Branch / Campus is required for a School Examination template."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			if not self.academic_year:
				frappe.throw(
					_("Academic Year is required for a School Examination template."),
					frappe.ValidationError,
				)
			return

		if self.exam_scope == PUBLIC_EXAM:
			self._assert_platform_manager()
			self.school_branch = None
			self.academic_year = None
			self.academic_term = None
			self.program = None
			self.student_group = None
			self.assessment_group = None
			return

		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	def _validate_academic_context(self) -> None:
		if self.exam_scope != SCHOOL_EXAM:
			return
		if self.academic_term:
			actual_year = frappe.db.get_value("Academic Term", self.academic_term, "academic_year")
			if actual_year != self.academic_year:
				frappe.throw(
					_("Academic Term {0} does not belong to Academic Year {1}.").format(
						self.academic_term, self.academic_year
					),
					frappe.ValidationError,
				)
		if not self.student_group:
			return

		group = frappe.db.get_value(
			"Student Group",
			self.student_group,
			[
				"name",
				BRANCH_FIELD,
				"academic_year",
				"academic_term",
				"program",
				"course",
				"disabled",
			],
			as_dict=True,
		)
		if not group or cint(group.disabled):
			frappe.throw(_("Select an enabled Student Group / Class."), frappe.ValidationError)
		if group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(
				_("Student Group / Class must belong to the selected School Branch / Campus."),
				frappe.ValidationError,
			)
		if group.academic_year and group.academic_year != self.academic_year:
			frappe.throw(
				_("Student Group / Class must belong to the selected Academic Year."),
				frappe.ValidationError,
			)
		if self.academic_term and group.academic_term and group.academic_term != self.academic_term:
			frappe.throw(
				_("Student Group / Class must belong to the selected Academic Term."),
				frappe.ValidationError,
			)
		if self.program and group.program and group.program != self.program:
			frappe.throw(
				_("Student Group / Class must belong to the selected Program."),
				frappe.ValidationError,
			)
		if group.course and group.course != self.course:
			frappe.throw(
				_("Student Group / Class course must match the template Subject / Course."),
				frappe.ValidationError,
			)

	def _validate_examination_centre(self) -> None:
		if not self.default_examination_centre:
			return
		centre = frappe.db.get_value(
			"EduEdge Examination Centre",
			self.default_examination_centre,
			["name", "centre_type", "school_branch", "enabled"],
			as_dict=True,
		)
		if not centre or not cint(centre.enabled):
			frappe.throw(_("Select an enabled Examination Centre."), frappe.ValidationError)
		if self.exam_scope == SCHOOL_EXAM:
			if centre.centre_type != SCHOOL_CENTRE or centre.school_branch != self.school_branch:
				frappe.throw(
					_("The default centre must be a School Examination Centre in the selected Branch."),
					frappe.ValidationError,
				)
			return
		if centre.centre_type != PLATFORM_CENTRE or centre.school_branch:
			frappe.throw(
				_("The default centre must be an EduEdge Exam Centre for a public examination."),
				frappe.ValidationError,
			)

	def _validate_timing_and_policy(self) -> None:
		if cint(self.duration_minutes) <= 0:
			frappe.throw(_("Duration must be greater than zero minutes."), frappe.ValidationError)
		if cint(self.maximum_attempts) <= 0:
			frappe.throw(_("Maximum Attempts must be at least one."), frappe.ValidationError)
		if flt(self.pass_percentage) < 0 or flt(self.pass_percentage) > 100:
			frappe.throw(_("Pass Percentage must be between 0 and 100."), frappe.ValidationError)
		if self.navigation_policy not in {"Free Navigation", "Forward Only"}:
			frappe.throw(_("Select a valid Question Navigation policy."), frappe.ValidationError)
		if self.marking_policy not in {"Use Question Marks", "Disable Negative Marking"}:
			frappe.throw(_("Select a valid Marking Policy."), frappe.ValidationError)
		if self.result_release_policy not in {"Manual Approval", "After Submission"}:
			frappe.throw(_("Select a valid Result Release Policy."), frappe.ValidationError)

	def _validate_version(self) -> None:
		if cint(self.version_number) < 1:
			frappe.throw(_("Template Version must be at least 1."), frappe.ValidationError)
		if not self.supersedes_template:
			return
		if self.supersedes_template == self.name:
			frappe.throw(_("An exam template cannot supersede itself."), frappe.ValidationError)
		previous = frappe.db.get_value(
			"EduEdge CBT Exam Template",
			self.supersedes_template,
			[
				"status",
				"exam_scope",
				"school_branch",
				"course",
				"exam_body",
				"version_number",
			],
			as_dict=True,
		)
		if not previous:
			frappe.throw(_("The template selected to supersede does not exist."), frappe.ValidationError)
		if previous.status not in {"Approved", "Retired"}:
			frappe.throw(
				_("Only an Approved or Retired exam template can be superseded."),
				frappe.ValidationError,
			)
		if (
			previous.exam_scope != self.exam_scope
			or previous.school_branch != self.school_branch
			or previous.course != self.course
			or (previous.exam_body or "") != (self.exam_body or "")
		):
			frappe.throw(
				_("A new template version must keep the same Scope, Branch, Course, and Exam Body."),
				frappe.ValidationError,
			)
		if cint(self.version_number) <= cint(previous.version_number):
			frappe.throw(
				_("The new Template Version must be greater than the superseded version."),
				frappe.ValidationError,
			)

	def _validate_question_rows(self) -> None:
		rows = list(self.get("questions") or [])
		if self.status in {"Under Review", "Approved"} and not rows:
			frappe.throw(
				_("Add at least one Approved CBT Question before review or approval."),
				frappe.ValidationError,
			)

		before = self.get_doc_before_save()
		uses_frozen_snapshot = bool(before and before.status in {"Approved", "Retired"})
		expected_bank = SCHOOL_BANK if self.exam_scope == SCHOOL_EXAM else PLATFORM_BANK
		seen_questions: set[str] = set()
		seen_orders: set[int] = set()
		total_marks = 0.0
		total_negative_marks = 0.0
		for index, row in enumerate(rows, start=1):
			if not row.question:
				frappe.throw(_("Every template row requires an Approved CBT Question."), frappe.ValidationError)
			if row.question in seen_questions:
				frappe.throw(
					_("CBT Question {0} is included more than once.").format(row.question),
					frappe.ValidationError,
				)
			seen_questions.add(row.question)

			row.display_order = cint(row.display_order) or index
			if row.display_order < 1 or row.display_order in seen_orders:
				frappe.throw(_("Template Question Order values must be unique positive numbers."), frappe.ValidationError)
			seen_orders.add(row.display_order)

			if uses_frozen_snapshot:
				if flt(row.mark) <= 0:
					frappe.throw(
						_("Approved template question snapshots must retain a positive Mark."),
						frappe.ValidationError,
					)
			else:
				question = frappe.db.get_value(
					"EduEdge CBT Question",
					row.question,
					[
						"question_code",
						"status",
						"ownership_scope",
						"school_branch",
						"course",
						"question_type",
						"topic",
						"default_mark",
						"negative_mark",
					],
					as_dict=True,
				)
				if not question or question.status != "Approved":
					frappe.throw(
						_("Question {0} must be Approved before it can be used in an exam template.").format(
							row.question
						),
						frappe.ValidationError,
					)
				if question.ownership_scope != expected_bank:
					frappe.throw(
						_("Question {0} belongs to a different Question Bank.").format(row.question),
						frappe.ValidationError,
					)
				if self.exam_scope == SCHOOL_EXAM and question.school_branch != self.school_branch:
					frappe.throw(
						_("Question {0} does not belong to the selected School Branch / Campus.").format(
							row.question
						),
						frappe.ValidationError,
					)
				if question.course != self.course:
					frappe.throw(
						_("Question {0} does not match the template Subject / Course.").format(row.question),
						frappe.ValidationError,
					)
				row.question_type = question.question_type
				row.topic = question.topic
				row.mark = flt(question.default_mark)
				row.negative_mark = flt(question.negative_mark)

			total_marks += flt(row.mark)
			if self.marking_policy != "Disable Negative Marking":
				total_negative_marks += flt(row.negative_mark)

		self.question_count = len(rows)
		self.total_marks = total_marks
		self.total_negative_marks = total_negative_marks
		if self.status == "Approved" and total_marks <= 0:
			frappe.throw(_("An Approved exam template must have a positive Total Mark."), frappe.ValidationError)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Exam Template Status cannot change from {0} to {1}.").format(
					previous_status, self.status
				),
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
					_("Approved exam template content is immutable. Create a new version instead."),
					frappe.ValidationError,
				)
		if self._question_fingerprint(before) != self._question_fingerprint(self):
			frappe.throw(
				_("Approved template questions are immutable. Create a new template version instead."),
				frappe.ValidationError,
			)

	def _assert_review_authority(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(REVIEW_ROLES):
			frappe.throw(
				_("You are not permitted to approve or retire CBT exam templates."),
				frappe.PermissionError,
			)

	def _assert_platform_manager(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(PLATFORM_MANAGER_ROLES):
			frappe.throw(
				_("Only an EduEdge platform administrator can manage public examination templates."),
				frappe.PermissionError,
			)

	@staticmethod
	def _question_fingerprint(doc) -> tuple:
		return tuple(
			(
				row.question,
				cint(row.display_order),
				(row.section_label or "").strip(),
				flt(row.mark),
				flt(row.negative_mark),
			)
			for row in (doc.get("questions") or [])
		)
