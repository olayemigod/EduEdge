from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from eduedge.access_control import user_has_role_permission

TRAINING_PROGRESS_DOCTYPE = "EduEdge Training Progress"
TRAINING_OVERSIGHT_PERMISSION = "report"


class EduEdgeTrainingProgress(Document):
	def validate(self) -> None:
		self._validate_owner()
		self.progress_percent = max(0, min(100, float(self.progress_percent or 0)))

	def on_trash(self) -> None:
		frappe.throw(
			_("Training progress records cannot be deleted. They are retained as staff training history."),
			frappe.ValidationError,
		)

	def _validate_owner(self) -> None:
		user = frappe.session.user
		if user == "Administrator":
			return
		if self.user == user:
			return
		if user_has_role_permission(TRAINING_PROGRESS_DOCTYPE, TRAINING_OVERSIGHT_PERMISSION, user):
			return
		frappe.throw(
			_("You can update only your own training progress."),
			frappe.PermissionError,
		)
