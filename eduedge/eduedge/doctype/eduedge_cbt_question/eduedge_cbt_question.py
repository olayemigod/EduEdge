from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime, sanitize_html

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.curriculum_fields import (
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
)
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import require_course_assignment

SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
BINARY_ANSWER_PRESETS = {
	"True/False": ("True", "False"),
	"Yes/No": ("Yes", "No"),
}
CHOICE_TYPES = {"Single Choice", "Multiple Choice"}
OBJECTIVE_TYPES = CHOICE_TYPES | set(BINARY_ANSWER_PRESETS)
CONTENT_FIELDS = ("question_text", "answer_key", "marking_guide", "review_feedback", "notes")
PROTECTED_FIELDS = (
	"question_code",
	"ownership_scope",
	"school_branch",
	"institution",
	"program_offering",
	"student_group",
	"version_number",
	"supersedes_question",
	"course",
	"topic",
	"curriculum",
	"exam_body",
	"difficulty",
	"question_type",
	"question_text",
	"answer_key",
	"marking_guide",
	"default_mark",
	"negative_mark",
)
ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Under Review", "Approved"},
	"Under Review": {"Draft", "Under Review", "Approved"},
	"Approved": {"Approved", "Retired"},
	"Retired": {"Retired"},
}


def option_label(position: int) -> str:
	value = cint(position)
	label = ""
	while value > 0:
		value -= 1
		label = chr(65 + (value % 26)) + label
		value //= 26
	return label


def sanitize_question_content(value) -> str:
	return sanitize_html(str(value or "")).strip()


def can_review_questions(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	return user_has_role_permission(
		"EduEdge CBT Question", "write", resolved_user
	) and user_has_role_permission("EduEdge CBT Question", "report", resolved_user)


def _require_question_author() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not (
		frappe.has_permission("EduEdge CBT Question", "create")
		or frappe.has_permission("EduEdge CBT Question", "write")
	):
		frappe.throw(_("You are not permitted to configure CBT questions."), frappe.PermissionError)


class EduEdgeCBTQuestion(Document):
	def autoname(self) -> None:
		self.question_code = (self.question_code or "").strip().upper()
		if self.question_code:
			self.name = self.question_code

	def validate(self) -> None:
		self._sanitize_stored_content()
		self.question_code = (self.question_code or "").strip().upper()
		self._validate_identity()
		self._validate_scope()
		self._validate_topic()
		self._validate_version()
		self._validate_marks()
		self._prepare_answer_options()
		self._validate_answers()
		self._validate_status_transition()
		self._prevent_approved_content_mutation()

	def on_trash(self) -> None:
		if self.status in {"Approved", "Retired"}:
			frappe.throw(
				_("Approved or Retired CBT questions cannot be deleted. Retain the record for audit history."),
				frappe.ValidationError,
			)
		if self.ownership_scope == PLATFORM_BANK:
			require_public_exam_authoring()

	def _sanitize_stored_content(self) -> None:
		for fieldname in CONTENT_FIELDS:
			if self.get(fieldname) is not None:
				self.set(fieldname, sanitize_question_content(self.get(fieldname)))
		for row in self.get("options") or []:
			row.option_text = sanitize_question_content(row.option_text)

	def _validate_identity(self) -> None:
		if not self.question_code:
			frappe.throw(_("Question Code is required."), frappe.ValidationError)
		if not (self.question_text or "").strip():
			frappe.throw(_("Question is required."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.ownership_scope == SCHOOL_BANK:
			self._validate_school_context()
			return
		if self.ownership_scope == PLATFORM_BANK:
			require_public_exam_authoring()
			self.school_branch = None
			self.institution = None
			self.program_offering = None
			self.student_group = None
			return
		frappe.throw(_("Select a valid Question Bank."), frappe.ValidationError)

	def _validate_school_context(self) -> None:
		if not self.school_branch:
			frappe.throw(
				_("School Branch / Campus is required for a School Question Bank question."),
				frappe.ValidationError,
			)
		assert_branch_access(self.school_branch)
		branch_institution = frappe.db.get_value("EduEdge School Branch", self.school_branch, "institution")
		if not branch_institution:
			frappe.throw(_("The selected Branch has no Institution context."), frappe.ValidationError)
		self.institution = branch_institution
		if is_teacher_user() and not self.program_offering:
			frappe.throw(_("Assigned teachers must select the Class / Programme Offering for a CBT question."), frappe.ValidationError)
		if not self.program_offering:
			self.student_group = None
			return
		offering = frappe.db.get_value(
			"EduEdge Program Offering",
			self.program_offering,
			["name", "institution", "school_branch", "program", "is_active"],
			as_dict=True,
		)
		if not offering or not offering.is_active:
			frappe.throw(_("Select an active Class / Programme Offering."), frappe.ValidationError)
		if offering.school_branch != self.school_branch or offering.institution != branch_institution:
			frappe.throw(_("Class / Programme Offering must belong to the selected Branch and Institution."), frappe.ValidationError)
		if self.course and not frappe.db.exists(
			"Program Course",
			{"parent": offering.program, "parenttype": "Program", "course": self.course},
		):
			frappe.throw(_("Subject / Course is not configured for the selected Class / Programme."), frappe.ValidationError)
		if self.student_group:
			meta = frappe.get_meta("Student Group")
			fields = ["name", BRANCH_FIELD, "program", "disabled"]
			if meta.has_field(OFFERING_FIELD):
				fields.append(OFFERING_FIELD)
			group = frappe.db.get_value("Student Group", self.student_group, fields, as_dict=True)
			if not group or group.disabled:
				frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
			if group.get(BRANCH_FIELD) != self.school_branch or group.program != offering.program:
				frappe.throw(_("Class Arm must belong to the selected Class / Programme Offering."), frappe.ValidationError)
			if meta.has_field(OFFERING_FIELD) and group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != offering.name:
				frappe.throw(_("Class Arm must belong to the selected Class / Programme Offering."), frappe.ValidationError)
		if is_teacher_user() and self.course:
			require_course_assignment(
				self.course,
				branch=self.school_branch,
				program_offering=self.program_offering,
				student_group=self.student_group,
			)

	def _validate_topic(self) -> None:
		if not self.topic:
			return
		if not self.course:
			frappe.throw(_("Select a Subject / Course before selecting a Topic."), frappe.ValidationError)
		if not frappe.db.exists(
			"Course Topic",
			{
				"parent": self.course,
				"parenttype": "Course",
				"parentfield": "topics",
				"topic": self.topic,
			},
		):
			frappe.throw(
				_("Topic {0} is not configured under Subject / Course {1}.").format(
					frappe.bold(self.topic), frappe.bold(self.course)
				),
				frappe.ValidationError,
			)
		meta = frappe.get_meta("Topic")
		if not meta.has_field(TOPIC_SCOPE_FIELD):
			return
		topic = frappe.db.get_value(
			"Topic",
			self.topic,
			[TOPIC_SCOPE_FIELD, TOPIC_OFFERING_FIELD, TOPIC_GROUP_FIELD],
			as_dict=True,
		) or {}
		scope = topic.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
		if scope == TOPIC_SCOPE_CLASS and topic.get(TOPIC_OFFERING_FIELD) != self.program_offering:
			frappe.throw(_("Topic is not available in the selected Class."), frappe.ValidationError)
		if scope == TOPIC_SCOPE_CLASS_ARM and (
			topic.get(TOPIC_OFFERING_FIELD) != self.program_offering
			or topic.get(TOPIC_GROUP_FIELD) != self.student_group
		):
			frappe.throw(_("Topic is not available in the selected Class Arm."), frappe.ValidationError)

	def _validate_version(self) -> None:
		if cint(self.version_number) < 1:
			frappe.throw(_("Question Version must be at least 1."), frappe.ValidationError)
		if not self.supersedes_question:
			return
		if self.supersedes_question == self.name:
			frappe.throw(_("A question cannot supersede itself."), frappe.ValidationError)
		previous = frappe.db.get_value(
			"EduEdge CBT Question",
			self.supersedes_question,
			[
				"status", "ownership_scope", "school_branch", "program_offering", "student_group",
				"course", "version_number",
			],
			as_dict=True,
		)
		if not previous:
			frappe.throw(_("The question selected to supersede does not exist."), frappe.ValidationError)
		if previous.status not in {"Approved", "Retired"}:
			frappe.throw(_("Only an Approved or Retired question can be superseded."), frappe.ValidationError)
		if (
			previous.ownership_scope != self.ownership_scope
			or previous.school_branch != self.school_branch
			or previous.program_offering != self.program_offering
			or previous.student_group != self.student_group
			or previous.course != self.course
		):
			frappe.throw(
				_("A new question version must keep the same Question Bank, Branch, Class context, and Subject / Course."),
				frappe.ValidationError,
			)
		if cint(self.version_number) <= cint(previous.version_number):
			frappe.throw(
				_("The new Question Version must be greater than the superseded version."),
				frappe.ValidationError,
			)

	def _validate_marks(self) -> None:
		if flt(self.default_mark) <= 0:
			frappe.throw(_("Default Mark must be greater than zero."), frappe.ValidationError)
		if flt(self.negative_mark) < 0:
			frappe.throw(_("Negative Mark cannot be negative."), frappe.ValidationError)
		if flt(self.negative_mark) > flt(self.default_mark):
			frappe.throw(_("Negative Mark cannot exceed the Default Mark."), frappe.ValidationError)

	def _prepare_answer_options(self) -> None:
		rows = list(self.get("options") or [])
		if self.question_type not in BINARY_ANSWER_PRESETS or rows:
			return
		for index, answer_text in enumerate(BINARY_ANSWER_PRESETS[self.question_type], start=1):
			self.append(
				"options",
				{
					"option_key": option_label(index),
					"option_text": answer_text,
					"display_order": index,
				},
			)

	def _validate_answers(self) -> None:
		rows = list(self.get("options") or [])
		if self.question_type not in OBJECTIVE_TYPES:
			if rows:
				frappe.throw(
					_("Answer Choices are only allowed for objective question types."),
					frappe.ValidationError,
				)
			if self.question_type in {"Short Answer", "Numeric"} and not (self.answer_key or "").strip():
				frappe.throw(_("Answer Key is required for this question type."), frappe.ValidationError)
			if self.question_type == "Essay" and not (self.marking_guide or "").strip():
				frappe.throw(_("Marking Guide is required for an Essay question."), frappe.ValidationError)
			return
		if len(rows) < 2:
			frappe.throw(_("Objective questions require at least two Answers."), frappe.ValidationError)
		if self.question_type in BINARY_ANSWER_PRESETS and len(rows) != 2:
			frappe.throw(_("{0} questions require exactly two Answers.").format(self.question_type), frappe.ValidationError)
		correct_count = 0
		for index, row in enumerate(rows, start=1):
			label = option_label(index)
			row.option_key = label
			row.option_text = sanitize_question_content(row.option_text)
			if not row.option_text:
				frappe.throw(_("Enter an Answer for option {0}.").format(label), frappe.ValidationError)
			row.display_order = index
			correct_count += cint(row.is_correct)
		if self.question_type in {"Single Choice", "True/False", "Yes/No"} and correct_count != 1:
			frappe.throw(_("This question type requires exactly one Correct Answer."), frappe.ValidationError)
		if self.question_type == "Multiple Choice" and correct_count < 1:
			frappe.throw(_("Multiple Choice questions require at least one Correct Answer."), frappe.ValidationError)

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.status if before else "Draft"
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.status not in allowed:
			frappe.throw(_("Question Status cannot change from {0} to {1}.").format(previous_status, self.status), frappe.ValidationError)
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
			before_value = before.get(fieldname)
			if fieldname in CONTENT_FIELDS:
				before_value = sanitize_question_content(before_value)
			if before_value != self.get(fieldname):
				frappe.throw(_("Approved question content is immutable. Create a new version instead."), frappe.ValidationError)
		if self._option_fingerprint(before) != self._option_fingerprint(self):
			frappe.throw(_("Approved Answers are immutable. Create a new question version instead."), frappe.ValidationError)

	def _assert_review_authority(self) -> None:
		if self.ownership_scope == PLATFORM_BANK:
			require_public_exam_authoring()
			return
		if not can_review_questions(frappe.session.user):
			frappe.throw(_("You are not permitted to approve or retire CBT questions."), frappe.PermissionError)

	@staticmethod
	def _option_fingerprint(doc) -> tuple:
		return tuple(
			(
				(row.option_key or "").strip().upper(),
				sanitize_question_content(row.option_text),
				cint(row.is_correct),
				cint(row.display_order),
			)
			for row in (doc.get("options") or [])
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def course_topic_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters,
):
	_require_question_author()
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	course = filters.get("course")
	if not course or not frappe.db.exists("Course", course):
		return []
	course_doc = frappe.get_doc("Course", course)
	if not course_doc.has_permission("read"):
		frappe.throw(_("You are not permitted to view this Subject / Course."), frappe.PermissionError)
	program_offering = filters.get("program_offering")
	student_group = filters.get("student_group")
	conditions = [
		f"(ifnull(topic.`{TOPIC_SCOPE_FIELD}`, '') in ('', %(institution_scope)s))"
	]
	if program_offering:
		conditions.append(
			f"(topic.`{TOPIC_SCOPE_FIELD}` = %(class_scope)s AND topic.`{TOPIC_OFFERING_FIELD}` = %(program_offering)s)"
		)
	if program_offering and student_group:
		conditions.append(
			f"(topic.`{TOPIC_SCOPE_FIELD}` = %(arm_scope)s AND topic.`{TOPIC_OFFERING_FIELD}` = %(program_offering)s AND topic.`{TOPIC_GROUP_FIELD}` = %(student_group)s)"
		)
	return frappe.db.sql(
		f"""
		SELECT DISTINCT topic.name, topic.topic_name, COALESCE(topic.description, '')
		FROM `tabCourse Topic` course_topic
		INNER JOIN `tabTopic` topic ON topic.name = course_topic.topic
		WHERE course_topic.parent = %(course)s
			AND course_topic.parenttype = 'Course'
			AND course_topic.parentfield = 'topics'
			AND ({' OR '.join(conditions)})
			AND (topic.name LIKE %(txt)s OR topic.topic_name LIKE %(txt)s)
		ORDER BY topic.topic_name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"course": course,
			"program_offering": program_offering,
			"student_group": student_group,
			"institution_scope": TOPIC_SCOPE_INSTITUTION,
			"class_scope": TOPIC_SCOPE_CLASS,
			"arm_scope": TOPIC_SCOPE_CLASS_ARM,
			"txt": f"%{txt or ''}%",
			"start": cint(start),
			"page_len": cint(page_len) or 20,
		},
	)
