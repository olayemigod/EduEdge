from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.cbt.domain import canonical_response, stable_hash

FINAL_ATTEMPT_STATUSES = {"Submitted", "Timed Out", "Cancelled"}


class EduEdgeCBTAttemptAnswer(Document):
	def before_naming(self) -> None:
		if self.attempt and self.question_key:
			self.answer_key = stable_hash({"attempt": self.attempt, "question_key": self.question_key})

	def validate(self) -> None:
		self._require_service_mutation()
		attempt = self._validate_attempt_scope()
		self._validate_question_snapshot()
		self._validate_response_hash()
		if not self.is_new():
			for fieldname in ("attempt", "exam", "student", "school_branch", "question_key", "source_question"):
				if self.has_value_changed(fieldname):
					frappe.throw(_("CBT answer identity cannot change after creation."), frappe.ValidationError)
		if attempt.status in FINAL_ATTEMPT_STATUSES and not self.flags.get("allow_final_attempt_sync"):
			frappe.throw(_("Answers cannot change after the CBT Attempt is final."), frappe.ValidationError)

	def on_trash(self) -> None:
		frappe.throw(_("CBT answer history is immutable and cannot be deleted."), frappe.ValidationError)

	def _require_service_mutation(self) -> None:
		if not self.flags.get("from_cbt_service"):
			frappe.throw(
				_("CBT answers must be saved through the offline-resilient sync service."),
				frappe.PermissionError,
			)

	def _validate_attempt_scope(self):
		attempt = frappe.db.get_value(
			"EduEdge CBT Attempt",
			self.attempt,
			["exam", "student", "user", "school_branch", "status"],
			as_dict=True,
		)
		if not attempt:
			frappe.throw(_("CBT Attempt was not found."), frappe.DoesNotExistError)
		for fieldname in ("exam", "student", "school_branch"):
			if self.get(fieldname) != attempt.get(fieldname):
				frappe.throw(_("CBT answer does not match the attempt {0}.").format(fieldname), frappe.ValidationError)
		if frappe.session.user != "Administrator" and "Student" in frappe.get_roles(frappe.session.user):
			if attempt.user != frappe.session.user:
				frappe.throw(_("Students can only sync answers for their own CBT Attempt."), frappe.PermissionError)
		return attempt

	def _validate_question_snapshot(self) -> None:
		row = frappe.db.get_value(
			"EduEdge CBT Attempt Question",
			{
				"parent": self.attempt,
				"parenttype": "EduEdge CBT Attempt",
				"snapshot_key": self.question_key,
			},
			["source_question"],
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Question is not part of this CBT Attempt."), frappe.ValidationError)
		if row.source_question != self.source_question:
			frappe.throw(_("CBT answer source question does not match the attempt snapshot."), frappe.ValidationError)

	def _validate_response_hash(self) -> None:
		try:
			response = frappe.parse_json(self.response_json) if self.response_json else None
		except Exception as exc:
			frappe.throw(_("CBT answer response must contain valid JSON: {0}").format(exc), frappe.ValidationError)
		canonical = canonical_response(response)
		self.response_json = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
		expected_hash = stable_hash(canonical)
		if self.response_hash and self.response_hash != expected_hash:
			frappe.throw(_("CBT answer response hash does not match its payload."), frappe.ValidationError)
		self.response_hash = expected_hash
		self.is_answered = canonical not in (None, "", [])
