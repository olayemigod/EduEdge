from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgePublishedResultSnapshot(Document):
	def validate(self) -> None:
		if not self.is_new():
			frappe.throw(
				_("Published Result Snapshots are immutable."),
				frappe.ValidationError,
			)
		publication = frappe.db.get_value(
			"EduEdge Result Publication",
			self.result_publication,
			[
				"school_branch",
				"student_group",
				"academic_year",
				"academic_term",
				"result_profile",
				"result_mode",
				"publication_version",
			],
			as_dict=True,
		)
		if not publication:
			frappe.throw(_("Result Publication does not exist."), frappe.DoesNotExistError)
		for fieldname in (
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"result_profile",
			"result_mode",
			"publication_version",
		):
			if self.get(fieldname) != publication.get(fieldname):
				frappe.throw(
					_("Snapshot scope must match the Result Publication."),
					frappe.ValidationError,
				)
		expected_hash = hashlib.sha256((self.payload_json or "").encode("utf-8")).hexdigest()
		if self.payload_hash != expected_hash:
			frappe.throw(_("Snapshot payload hash is invalid."), frappe.ValidationError)
		duplicate = frappe.db.exists(
			"EduEdge Published Result Snapshot",
			{
				"name": ["!=", self.name],
				"result_publication": self.result_publication,
				"student": self.student,
			},
		)
		if duplicate:
			frappe.throw(
				_("A published snapshot already exists for this Student and Result Publication."),
				frappe.DuplicateEntryError,
			)

	def on_trash(self) -> None:
		frappe.throw(
			_("Published Result Snapshots are immutable and cannot be deleted."),
			frappe.ValidationError,
		)
