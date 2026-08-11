from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.curriculum_fields import (
	TOPIC_GROUP_FIELD,
	TOPIC_OFFERING_FIELD,
	TOPIC_SCOPE_CLASS,
	TOPIC_SCOPE_CLASS_ARM,
	TOPIC_SCOPE_FIELD,
	TOPIC_SCOPE_INSTITUTION,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, resolve_program_offering_period_dates

SCHEME_ACTION_FLAG = "in_eduedge_scheme_of_work_action"
SCHEME_STATUSES = {"Draft", "Approved", "Retired"}
IMMUTABLE_AFTER_APPROVAL = (
	"school_branch",
	"program_offering",
	"student_group",
	"course",
	"version_no",
	"supersedes_scheme",
	"items",
	"notes",
)
ITEM_BUSINESS_FIELDS = (
	"sequence",
	"week_no",
	"topic",
	"topic_name_snapshot",
	"topic_description_snapshot",
	"learning_objective",
	"planned_start_date",
	"planned_end_date",
	"estimated_periods",
	"notes",
)


class EduEdgeSchemeOfWork(Document):
	def before_insert(self) -> None:
		self.prepared_by = self.prepared_by or frappe.session.user

	def validate(self) -> None:
		self.status = self.status or "Draft"
		if self.status not in SCHEME_STATUSES:
			frappe.throw(_("Select a valid Scheme of Work Status."), frappe.ValidationError)
		if cint(self.version_no) < 1:
			frappe.throw(_("Scheme Version must be at least 1."), frappe.ValidationError)
		self._protect_governed_history()
		self._apply_academic_context()
		self._validate_student_group()
		self._validate_course()
		self._validate_items()
		self._validate_version_history()
		self._validate_duplicate_version()
		self.scheme_title = self._build_title()

	def on_trash(self) -> None:
		if self.status != "Draft":
			frappe.throw(_("Approved or Retired Schemes of Work are retained as academic history."), frappe.ValidationError)
		if frappe.db.exists("EduEdge Scheme of Work", {"supersedes_scheme": self.name}):
			frappe.throw(_("This Scheme of Work is part of a version history and cannot be deleted."), frappe.ValidationError)

	def _protect_governed_history(self) -> None:
		before = self.get_doc_before_save()
		action = bool(getattr(frappe.flags, SCHEME_ACTION_FLAG, False))
		if not before:
			if self.status != "Draft" and not action:
				frappe.throw(_("New Schemes of Work start as Draft."), frappe.ValidationError)
			if self.supersedes_scheme and not action:
				frappe.throw(_("Create a new Scheme version through the governed version action."), frappe.ValidationError)
			return
		if before.status != self.status and not action:
			frappe.throw(_("Use Scheme of Work approval or retirement actions to change Status."), frappe.ValidationError)
		if before.status not in {"Approved", "Retired"} or action:
			return
		for fieldname in IMMUTABLE_AFTER_APPROVAL:
			if fieldname == "items":
				if _item_signature(before.get("items") or []) != _item_signature(self.get("items") or []):
					frappe.throw(_("Approved Scheme of Work curriculum is immutable. Create a new version instead."), frappe.ValidationError)
				continue
			if str(before.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(_("Approved Scheme of Work curriculum is immutable. Create a new version instead."), frappe.ValidationError)

	def _apply_academic_context(self) -> None:
		if not self.program_offering:
			frappe.throw(_("Select a Class / Programme Offering."), frappe.ValidationError)
		offering = frappe.db.get_value(
			"EduEdge Program Offering",
			self.program_offering,
			[
				"name",
				"offering_title",
				"institution",
				"school_branch",
				"program",
				"academic_year",
				"academic_term",
				"start_date",
				"end_date",
				"is_active",
			],
			as_dict=True,
		)
		if not offering:
			frappe.throw(_("Select a valid Class / Programme Offering."), frappe.ValidationError)
		if self.status == "Draft" and not cint(offering.is_active):
			frappe.throw(_("Draft Schemes of Work require an active Class / Programme Offering."), frappe.ValidationError)
		assert_branch_access(offering.school_branch)
		if self.school_branch and self.school_branch != offering.school_branch:
			frappe.throw(_("Scheme Branch must match the Class / Programme Offering."), frappe.ValidationError)
		self.school_branch = offering.school_branch
		self.institution = offering.institution
		self.academic_year = offering.academic_year
		self.academic_term = offering.academic_term or None
		period_start, period_end = resolve_program_offering_period_dates(offering)
		self.period_start_date = period_start
		self.period_end_date = period_end
		self._offering = offering

	def _validate_student_group(self) -> None:
		if not self.student_group:
			return
		meta = frappe.get_meta("Student Group")
		fields = ["name", "student_group_name", "program", "academic_year", "academic_term", "disabled", BRANCH_FIELD]
		if meta.has_field(OFFERING_FIELD):
			fields.append(OFFERING_FIELD)
		group = frappe.db.get_value("Student Group", self.student_group, fields, as_dict=True)
		if not group or cint(group.disabled):
			frappe.throw(_("Select an active Class Arm / Student Group."), frappe.ValidationError)
		if group.get(BRANCH_FIELD) != self.school_branch:
			frappe.throw(_("Class Arm must belong to the Scheme Branch."), frappe.ValidationError)
		if group.program and group.program != self._offering.program:
			frappe.throw(_("Class Arm Programme must match the Class / Programme Offering."), frappe.ValidationError)
		if group.academic_year and group.academic_year != self.academic_year:
			frappe.throw(_("Class Arm Academic Session must match the Class / Programme Offering."), frappe.ValidationError)
		if group.academic_term and group.academic_term != self.academic_term:
			frappe.throw(_("Class Arm Term must match the Class / Programme Offering."), frappe.ValidationError)
		if meta.has_field(OFFERING_FIELD) and group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != self.program_offering:
			frappe.throw(_("Class Arm must belong to the selected Class / Programme Offering."), frappe.ValidationError)
		self._student_group = group

	def _validate_course(self) -> None:
		if not self.course or not frappe.db.exists("Course", self.course):
			frappe.throw(_("Select a valid Subject / Course."), frappe.ValidationError)
		if not frappe.db.exists(
			"Program Course",
			{"parent": self._offering.program, "parenttype": "Program", "course": self.course},
		):
			frappe.throw(_("Subject / Course is not configured for the selected Class / Programme Offering."), frappe.ValidationError)
		if frappe.get_meta("Course").has_field(INSTITUTION_FIELD):
			institution = frappe.db.get_value("Course", self.course, INSTITUTION_FIELD)
			if institution and institution != self.institution:
				frappe.throw(_("Subject / Course belongs to another Institution."), frappe.ValidationError)

	def _validate_items(self) -> None:
		sequences: set[int] = set()
		for row in self.get("items") or []:
			sequence = cint(row.sequence)
			week_no = cint(row.week_no)
			if sequence < 1 or week_no < 1:
				frappe.throw(_("Every Scheme item requires positive Sequence and Week values."), frappe.ValidationError)
			if sequence in sequences:
				frappe.throw(_("Scheme item Sequence values must be unique."), frappe.ValidationError)
			sequences.add(sequence)
			if cint(row.estimated_periods) < 1:
				frappe.throw(_("Estimated Periods must be at least 1 for each Scheme item."), frappe.ValidationError)
			if row.planned_start_date and row.planned_end_date and getdate(row.planned_end_date) < getdate(row.planned_start_date):
				frappe.throw(_("A Scheme item Planned End Date cannot precede its Planned Start Date."), frappe.ValidationError)
			for value in (row.planned_start_date, row.planned_end_date):
				if not value:
					continue
				if self.period_start_date and getdate(value) < getdate(self.period_start_date):
					frappe.throw(_("Scheme item dates cannot precede the academic period."), frappe.ValidationError)
				if self.period_end_date and getdate(value) > getdate(self.period_end_date):
					frappe.throw(_("Scheme item dates cannot extend beyond the academic period."), frappe.ValidationError)
			self._validate_topic(row.topic)

	def _validate_topic(self, topic: str | None) -> None:
		if not topic or not frappe.db.exists("Topic", topic):
			frappe.throw(_("Select a valid Topic for every Scheme item."), frappe.ValidationError)
		if not frappe.db.exists(
			"Course Topic",
			{"parent": self.course, "parenttype": "Course", "parentfield": "topics", "topic": topic},
		):
			frappe.throw(_("Scheme Topic {0} is not configured under Subject / Course {1}.").format(topic, self.course), frappe.ValidationError)
		meta = frappe.get_meta("Topic")
		if not meta.has_field(TOPIC_SCOPE_FIELD):
			return
		fields = [TOPIC_SCOPE_FIELD, TOPIC_OFFERING_FIELD, TOPIC_GROUP_FIELD]
		topic_row = frappe.db.get_value("Topic", topic, fields, as_dict=True) or {}
		scope = topic_row.get(TOPIC_SCOPE_FIELD) or TOPIC_SCOPE_INSTITUTION
		if scope == TOPIC_SCOPE_CLASS and topic_row.get(TOPIC_OFFERING_FIELD) != self.program_offering:
			frappe.throw(_("A Class-scoped Topic must belong to this Scheme's Class / Programme Offering."), frappe.ValidationError)
		if scope == TOPIC_SCOPE_CLASS_ARM and (
			topic_row.get(TOPIC_OFFERING_FIELD) != self.program_offering
			or not self.student_group
			or topic_row.get(TOPIC_GROUP_FIELD) != self.student_group
		):
			frappe.throw(_("A Class Arm Topic can be used only in a Scheme for that exact Class Arm."), frappe.ValidationError)

	def _validate_version_history(self) -> None:
		if not self.supersedes_scheme:
			return
		if self.supersedes_scheme == self.name:
			frappe.throw(_("A Scheme of Work cannot supersede itself."), frappe.ValidationError)
		previous = frappe.db.get_value(
			"EduEdge Scheme of Work",
			self.supersedes_scheme,
			["status", "school_branch", "program_offering", "student_group", "course", "version_no"],
			as_dict=True,
		)
		if not previous or previous.status not in {"Approved", "Retired"}:
			frappe.throw(_("A new Scheme version must supersede an Approved or Retired Scheme."), frappe.ValidationError)
		if any(
			str(previous.get(fieldname) or "") != str(self.get(fieldname) or "")
			for fieldname in ("school_branch", "program_offering", "student_group", "course")
		):
			frappe.throw(_("A new Scheme version must keep the same Branch, Class, Class Arm and Subject context."), frappe.ValidationError)
		if cint(self.version_no) <= cint(previous.version_no):
			frappe.throw(_("A new Scheme Version must be greater than the previous version."), frappe.ValidationError)

	def _validate_duplicate_version(self) -> None:
		rows = frappe.get_all(
			"EduEdge Scheme of Work",
			filters={
				"school_branch": self.school_branch,
				"program_offering": self.program_offering,
				"course": self.course,
				"version_no": cint(self.version_no),
				"name": ["!=", self.name or ""],
			},
			fields=["name", "student_group"],
			limit_page_length=20,
		)
		if any(str(row.student_group or "") == str(self.student_group or "") for row in rows):
			frappe.throw(_("This Scheme context already has the selected Version number."), frappe.DuplicateEntryError)

	def _build_title(self) -> str:
		offering = self._offering.offering_title or self.program_offering
		course = frappe.db.get_value("Course", self.course, "course_name") or self.course
		group = ""
		if self.student_group:
			group = getattr(getattr(self, "_student_group", None), "student_group_name", None) or self.student_group
		parts = [course, offering, group, _("Version {0}").format(cint(self.version_no))]
		return " · ".join(str(value) for value in parts if value)


def snapshot_scheme_context(doc: EduEdgeSchemeOfWork) -> None:
	"""Capture readable curriculum labels at approval time without changing source masters."""
	doc.offering_title_snapshot = doc._offering.offering_title or doc.program_offering
	doc.course_name_snapshot = frappe.db.get_value("Course", doc.course, "course_name") or doc.course
	doc.student_group_name_snapshot = ""
	if doc.student_group:
		doc.student_group_name_snapshot = (
			frappe.db.get_value("Student Group", doc.student_group, "student_group_name") or doc.student_group
		)
	for row in doc.get("items") or []:
		topic = frappe.db.get_value("Topic", row.topic, ["topic_name", "description"], as_dict=True) or {}
		row.topic_name_snapshot = topic.get("topic_name") or row.topic
		row.topic_description_snapshot = topic.get("description") or ""


def _item_signature(rows) -> list[tuple]:
	return [
		tuple(str(row.get(fieldname) or "") for fieldname in ITEM_BUSINESS_FIELDS)
		for row in rows
	]