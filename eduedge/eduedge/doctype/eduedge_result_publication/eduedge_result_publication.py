from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.education.assessment_operations import validate_publication_scope
from eduedge.education.result_profile import (
	get_publication_result_profile_config,
	set_publication_result_profile_config,
	validate_publication_profile,
)


class EduEdgeResultPublication(Document):
	def before_naming(self) -> None:
		if not self.publication_version:
			self.publication_version = 1
		if not self.title:
			parts = [self.student_group, self.assessment_group or self.result_profile, self.academic_term or self.academic_year]
			base_title = " · ".join(part for part in parts if part)
			self.title = f"{base_title} · v{self.publication_version}" if self.publication_version > 1 else base_title

	def validate(self) -> None:
		validate_publication_scope(self)
		validate_publication_profile(self)
		self._validate_revision_identity()
		self._validate_scope_change()
		self._validate_duplicate_scope()

	def on_trash(self) -> None:
		if self.status != "Draft":
			frappe.throw(
				_("Only Draft Result Publications can be deleted."),
				frappe.ValidationError,
			)

	def _validate_revision_identity(self) -> None:
		scope_fields = (
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
		)
		if self.is_new():
			if not self.publication_version:
				self.publication_version = 1
			if not self.supersedes_publication:
				if int(self.publication_version or 1) != 1:
					frappe.throw(
						_("A first Result Publication must use publication version 1."),
						frappe.ValidationError,
					)
				return
			source = frappe.get_doc("EduEdge Result Publication", self.supersedes_publication)
			if source.status != "Published":
				frappe.throw(
					_("A Result Publication revision must supersede a Published publication."),
					frappe.ValidationError,
				)
			if int(self.publication_version or 0) != int(source.publication_version or 1) + 1:
				frappe.throw(
					_("A Result Publication revision must use the next sequential version."),
					frappe.ValidationError,
				)
			for fieldname in scope_fields:
				if (self.get(fieldname) or "") != (source.get(fieldname) or ""):
					frappe.throw(
						_("A Result Publication revision must preserve the original result scope."),
						frappe.ValidationError,
					)
			if self.result_profile:
				set_publication_result_profile_config(
					self,
					get_publication_result_profile_config(source),
				)
			return
		for fieldname in ("publication_version", "supersedes_publication"):
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("Result Publication revision identity cannot change after creation."),
					frappe.ValidationError,
				)


	def _validate_scope_change(self) -> None:
		scope_fields = (
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
		)
		if not self.is_new() and self.supersedes_publication:
			for fieldname in scope_fields:
				if self.has_value_changed(fieldname):
					frappe.throw(
						_("A Result Publication revision scope cannot change."),
						frappe.ValidationError,
					)
			return
		if self.is_new() or self.status in {"Draft", "Rejected"}:
			return
		for fieldname in (
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
		):
			if self.has_value_changed(fieldname):
				frappe.throw(
					_("Result Publication scope cannot change after approval begins."),
					frappe.ValidationError,
				)

	def _validate_duplicate_scope(self) -> None:
		filters = {
			"name": ["!=", self.name],
			"school_branch": self.school_branch,
			"student_group": self.student_group,
			"academic_year": self.academic_year,
			"academic_term": self.academic_term or "",
			"assessment_group": self.assessment_group if self.assessment_group else ["is", "not set"],
			"result_profile": self.result_profile if self.result_profile else ["is", "not set"],
			"result_mode": self.result_mode or "Terminal",
			"publication_version": self.publication_version or 1,
		}
		duplicate = frappe.db.exists("EduEdge Result Publication", filters)
		if duplicate:
			frappe.throw(
				_("Result Publication {0} already exists for this scope.").format(duplicate),
				frappe.DuplicateEntryError,
			)
