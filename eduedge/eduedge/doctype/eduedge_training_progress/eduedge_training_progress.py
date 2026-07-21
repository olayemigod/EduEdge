from __future__ import annotations

import frappe
from frappe.model.document import Document

from eduedge.access_control import user_has_role_permission

TRAINING_PROGRESS_DOCTYPE = "EduEdge Training Progress"


class EduEdgeTrainingProgress(Document):
	def validate(self) -> None:
		self._validate_owner()
		self.progress_percent = max(0, min(100, float(self.progress_percent or 0)))

	def _validate_owner(self) -> None:
		user = frappe.session.user
		if user == "Administrator":
			return
		if self.user == user:
			return
		if user_has_role_permission(TRAINING_PROGRESS_DOCTYPE, "delete", user):
			return
		frappe.throw(
			"You can update only your own training progress.",
			frappe.PermissionError,
		)
