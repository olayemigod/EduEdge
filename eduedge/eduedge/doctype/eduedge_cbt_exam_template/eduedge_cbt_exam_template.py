from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.services.branch_context import get_allowed_school_branches

SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"

REUSE_UNIVERSAL = "Universal"
REUSE_INSTITUTION = "Institution-wide"
REUSE_BRANCH = "Branch-wide"
REUSE_SCOPES = {REUSE_UNIVERSAL, REUSE_INSTITUTION, REUSE_BRANCH}

SUBJECT_ANY = "Any Subject"
SUBJECT_SPECIFIC = "Specific Subject"
SUBJECT_APPLICABILITY = {SUBJECT_ANY, SUBJECT_SPECIFIC}

MODE_BLUEPRINT = "Policy Blueprint"
MODE_FIXED = "Fixed Question Set"
TEMPLATE_MODES = {MODE_BLUEPRINT, MODE_FIXED}

EXAM_PURPOSES = {
	"Continuous Assessment",
	"Midterm Examination",
	"End-of-Term Examination",
	"Mock Examination",
	"Entrance Examination",
	"Practice / Revision",
	"Other",
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
	"template_reuse_scope",
	"company",
	"institution",
	"school_branch",
	"exam_purpose",
	"template_mode",
	"subject_applicability",
	"course",
	"version_number",
	"supersedes_template",
	"academic_year",
	"academic_term",
	"program",
	"student_group",
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
	"device_change_policy",
	"attempt_review_policy",
	"candidate_instructions",
)

PRIVILEGED_TEMPLATE_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
}


def can_review_templates(user: str | None = None) -> bool:
	"""Use a configurable DocType right as the template-review capability."""
	return user_has_role_permission("EduEdge CBT Exam Template", "delete", user)


def _branch_context(branch: str | None) -> dict:
	if not branch:
		return {}
	row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["name", "company", "institution", "enabled"],
		as_dict=True,
	)
	return dict(row or {})


def _institution_context(institution: str | None) -> dict:
	if not institution:
		return {}
	row = frappe.db.get_value(
		"EduEdge Institution",
		institution,
		["name", "company", "enabled"],
		as_dict=True,
	)
	return dict(row or {})


def _allowed_branch_rows() -> list[dict]:
	return [dict(row) for row in get_allowed_school_branches()]


def _has_privileged_template_role() -> bool:
	return bool(PRIVILEGED_TEMPLATE_ROLES.intersection(frappe.get_roles(frappe.session.user)))


def _assert_company_access(company: str) -> None:
	allowed = _allowed_branch_rows()
	if any(row.get("company") == company for row in allowed):
		return
	branch_count = frappe.db.count("EduEdge School Branch", {"company": company, "enabled": 1})
	if not branch_count and _has_privileged_template_role():
		return
	frappe.throw(_("You are not permitted to configure templates for this Company."), frappe.PermissionError)


def _assert_institution_access(institution: str) -> None:
	allowed = _allowed_branch_rows()
	if any(row.get("institution") == institution for row in allowed):
		return
	branch_count = frappe.db.count("EduEdge School Branch", {"institution": institution, "enabled": 1})
	if not branch_count and _has_privileged_template_role():
		return
	frappe.throw(_("You are not permitted to configure templates for this Institution."), frappe.PermissionError)


class EduEdgeCBTExamTemplate(Document):
	def validate(self) -> None:
		self.template_code = (self.template_code or "").strip().upper()
		self.template_title = (self.template_title or "").strip()
		self.template_reuse_scope = self.template_reuse_scope or REUSE_BRANCH
		self.subject_applicability = self.subject_applicability or SUBJECT_SPECIFIC
		self.template_mode = self.template_mode or MODE_FIXED
		self.exam_purpose = self.exam_purpose or "Other"
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
		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()

	def _validate_identity(self) -> None:
		if not self.template_code:
			frappe.throw(_("Template Code is required."), frappe.ValidationError)
		if not self.template_title:
			frappe.throw(_("Template Title is required."), frappe.ValidationError)
		if self.template_reuse_scope not in REUSE_SCOPES:
			frappe.throw(_("Select a valid Template Reuse Scope."), frappe.ValidationError)
		if self.subject_applicability not in SUBJECT_APPLICABILITY:
			frappe.throw(_("Select a valid Subject Applicability."), frappe.ValidationError)
		if self.template_mode not in TEMPLATE_MODES:
			frappe.throw(_("Select a valid Template Content Mode."), frappe.ValidationError)
		if self.exam_purpose not in EXAM_PURPOSES:
			frappe.throw(_("Select a valid Exam Purpose."), frappe.ValidationError)

		if self.subject_applicability == SUBJECT_ANY:
			self.course = None
		elif not self.course:
			frappe.throw(_("Subject / Course is required for a Specific Subject template."), frappe.ValidationError)

		if self.template_mode == MODE_FIXED:
			if self.subject_applicability != SUBJECT_SPECIFIC or not self.course:
				frappe.throw(
					_("A Fixed Question Set must be limited to a Specific Subject."),
					frappe.ValidationError,
				)
			if self.exam_scope == SCHOOL_EXAM and self.template_reuse_scope != REUSE_BRANCH:
				frappe.throw(
					_("School Fixed Question Sets must be Branch-wide. Use a Policy Blueprint for Universal or Institution-wide reuse."),
					frappe.ValidationError,
				)

	def _validate_scope(self) -> None:
		if self.exam_scope == SCHOOL_EXAM:
			if self.template_reuse_scope == REUSE_UNIVERSAL:
				if not self.company:
					frappe.throw(
						_("Company is required for a Universal school template."),
						frappe.ValidationError,
					)
				_assert_company_access(self.company)
				self.institution = None
				self.school_branch = None
				return

			if self.template_reuse_scope == REUSE_INSTITUTION:
				institution = _institution_context(self.institution)
				if not institution or not cint(institution.get("enabled")):
					frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
				if self.company and institution.get("company") != self.company:
					frappe.throw(_("The selected Institution does not belong to the selected Company."), frappe.ValidationError)
				self.company = institution.get("company")
				_assert_company_access(self.company)
				_assert_institution_access(self.institution)
				self.school_branch = None
				return

			if self.template_reuse_scope == REUSE_BRANCH:
				if not self.school_branch:
					frappe.throw(
						_("School Branch / Campus is required for a Branch-wide template."),
						frappe.ValidationError,
					)
				assert_branch_access(self.school_branch)
				branch = _branch_context(self.school_branch)
				if not branch or not cint(branch.get("enabled")):
					frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
				self.company = branch.get("company")
				self.institution = branch.get("institution")
				return

		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()
			self.template_reuse_scope = REUSE_UNIVERSAL
			self.company = None
			self.institution = None
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
			if not self.academic_year:
				frappe.throw(_("Select Academic Year before Academic Term."), frappe.ValidationError)
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

		group_branch = _branch_context(group.get(BRANCH_FIELD))
		if self.template_reuse_scope == REUSE_BRANCH and group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Student Group / Class must belong to the selected Branch."), frappe.ValidationError)
		if self.template_reuse_scope == REUSE_INSTITUTION and group_branch.get("institution") != self.institution:
			frappe.throw(_("Student Group / Class must belong to the selected Institution."), frappe.ValidationError)
		if self.template_reuse_scope == REUSE_UNIVERSAL and group_branch.get("company") != self.company:
			frappe.throw(_("Student Group / Class must belong to the selected Company."), frappe.ValidationError)
		if self.academic_year and group.academic_year and group.academic_year != self.academic_year:
			frappe.throw(_("Student Group / Class must belong to the selected Academic Year."), frappe.ValidationError)
		if self.academic_term and group.academic_term and group.academic_term != self.academic_term:
			frappe.throw(_("Student Group / Class must belong to the selected Academic Term."), frappe.ValidationError)
		if self.program and group.program and group.program != self.program:
			frappe.throw(_("Student Group / Class must belong to the selected Programme."), frappe.ValidationError)
		if self.subject_applicability == SUBJECT_SPECIFIC and group.course and group.course != self.course:
			frappe.throw(_("Student Group / Class course must match the template Subject / Course."), frappe.ValidationError)

	def _validate_examination_centre(self) -> None:
		if not self.default_examination_centre:
			return
		centre = frappe.db.get_value(
			"EduEdge Examination Centre",
			self.default_examination_centre,
			["name", "centre_type", "school_branch", "centre_status", "enabled"],
			as_dict=True,
		)
		if not centre or (centre.centre_status != "Active" and not cint(centre.enabled)):
			frappe.throw(_("Select an Active Examination Centre."), frappe.ValidationError)
		if self.exam_scope == SCHOOL_EXAM:
			if centre.centre_type != SCHOOL_CENTRE or not centre.school_branch:
				frappe.throw(_("Select an Active School Examination Centre."), frappe.ValidationError)
			centre_branch = _branch_context(centre.school_branch)
			if self.template_reuse_scope == REUSE_BRANCH and centre.school_branch != self.school_branch:
				frappe.throw(_("The default centre must belong to the selected Branch."), frappe.ValidationError)
			if self.template_reuse_scope == REUSE_INSTITUTION and centre_branch.get("institution") != self.institution:
				frappe.throw(_("The default centre must belong to the selected Institution."), frappe.ValidationError)
			if self.template_reuse_scope == REUSE_UNIVERSAL and centre_branch.get("company") != self.company:
				frappe.throw(_("The default centre must belong to the selected Company."), frappe.ValidationError)
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
				"template_reuse_scope",
				"company",
				"institution",
				"school_branch",
				"exam_purpose",
				"template_mode",
				"subject_applicability",
				"course",
				"exam_body",
				"version_number",
			],
			as_dict=True,
		)
		if not previous:
			frappe.throw(_("The template selected to supersede does not exist."), frappe.ValidationError)
		if previous.status not in {"Approved", "Retired"}:
			frappe.throw(_("Only an Approved or Retired exam template can be superseded."), frappe.ValidationError)
		identity_fields = (
			"exam_scope",
			"template_reuse_scope",
			"company",
			"institution",
			"school_branch",
			"exam_purpose",
			"template_mode",
			"subject_applicability",
			"course",
			"exam_body",
		)
		if any((previous.get(fieldname) or "") != (self.get(fieldname) or "") for fieldname in identity_fields):
			frappe.throw(
				_("A new template version must keep the same ownership, purpose, content mode, Subject applicability, and Exam Body."),
				frappe.ValidationError,
			)
		if cint(self.version_number) <= cint(previous.version_number):
			frappe.throw(_("The new Template Version must be greater than the superseded version."), frappe.ValidationError)

	def _validate_question_rows(self) -> None:
		rows = list(self.get("questions") or [])
		if self.template_mode == MODE_BLUEPRINT:
			if rows:
				frappe.throw(
					_("A Policy Blueprint cannot carry fixed questions. Questions are selected when the exam is prepared from the blueprint."),
					frappe.ValidationError,
				)
			self.question_count = 0
			self.total_marks = 0
			self.total_negative_marks = 0
			return

		if self.status in {"Under Review", "Approved"} and not rows:
			frappe.throw(_("Add at least one Approved CBT Question before review or approval."), frappe.ValidationError)

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
				frappe.throw(_("CBT Question {0} is included more than once.").format(row.question), frappe.ValidationError)
			seen_questions.add(row.question)

			row.display_order = cint(row.display_order) or index
			if row.display_order < 1 or row.display_order in seen_orders:
				frappe.throw(_("Template Question Order values must be unique positive numbers."), frappe.ValidationError)
			seen_orders.add(row.display_order)

			if uses_frozen_snapshot:
				if flt(row.mark) <= 0:
					frappe.throw(_("Approved template question snapshots must retain a positive Mark."), frappe.ValidationError)
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
						_("Question {0} must be Approved before it can be used in an exam template.").format(row.question),
						frappe.ValidationError,
					)
				if question.ownership_scope != expected_bank:
					frappe.throw(_("Question {0} belongs to a different Question Bank.").format(row.question), frappe.ValidationError)
				if self.exam_scope == SCHOOL_EXAM and question.school_branch != self.school_branch:
					frappe.throw(
						_("Question {0} does not belong to the selected School Branch / Campus.").format(row.question),
						frappe.ValidationError,
					)
				if question.course != self.course:
					frappe.throw(_("Question {0} does not match the template Subject / Course.").format(row.question), frappe.ValidationError)
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
			frappe.throw(_("An Approved Fixed Question Set must have a positive Total Mark."), frappe.ValidationError)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(
				_("Exam Template Status cannot change from {0} to {1}.").format(previous_status, self.status),
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
		if self.exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()
			return
		if not can_review_templates(frappe.session.user):
			frappe.throw(
				_("You are not permitted to approve or retire CBT exam templates."),
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
