from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from eduedge.cbt.question_responsibilities import assert_responsibility_scope_access


class EduEdgeQuestionResponsibilityAssignment(Document):
	def validate(self) -> None:
		self._validate_user()
		self._validate_institution()
		self._validate_branch()
		self._validate_course()
		self._validate_responsibilities()
		self._validate_dates()
		self._validate_duplicate()
		assert_responsibility_scope_access(self.institution, self.school_branch)

	def _validate_user(self) -> None:
		row = frappe.db.get_value("User", self.user, ["enabled", "user_type"], as_dict=True)
		if not row or not row.enabled or row.user_type != "System User":
			frappe.throw(_("Select an enabled System User."), frappe.ValidationError)

	def _validate_institution(self) -> None:
		row = frappe.db.get_value(
			"EduEdge Institution",
			self.institution,
			["enabled", "company"],
			as_dict=True,
		)
		if not row or not row.enabled:
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)

	def _validate_branch(self) -> None:
		if not self.school_branch:
			return
		row = frappe.db.get_value(
			"EduEdge School Branch",
			self.school_branch,
			["enabled", "institution"],
			as_dict=True,
		)
		if not row or not row.enabled:
			frappe.throw(_("Select an enabled Branch / Campus."), frappe.ValidationError)
		if row.institution != self.institution:
			frappe.throw(
				_("The selected Branch / Campus does not belong to this Institution."),
				frappe.ValidationError,
			)

	def _validate_course(self) -> None:
		if not frappe.db.exists("Course", self.course):
			frappe.throw(_("Select a valid Subject / Course."), frappe.ValidationError)
		meta = frappe.get_meta("Course")
		if not meta.has_field("eduedge_institution"):
			return
		course_institution = frappe.db.get_value("Course", self.course, "eduedge_institution")
		if course_institution and course_institution != self.institution:
			frappe.throw(
				_("The selected Subject / Course belongs to another Institution."),
				frappe.ValidationError,
			)

	def _validate_responsibilities(self) -> None:
		if not any((self.can_author, self.can_subject_review, self.can_final_approve)):
			frappe.throw(
				_("Select at least one Question responsibility."),
				frappe.ValidationError,
			)

	def _validate_dates(self) -> None:
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

	def _validate_duplicate(self) -> None:
		duplicate = frappe.db.exists(
			self.doctype,
			{
				"user": self.user,
				"course": self.course,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("User {0} already has a Question responsibility assignment for Subject / Course {1}.").format(
					self.user,
					self.course,
				),
				frappe.DuplicateEntryError,
			)
