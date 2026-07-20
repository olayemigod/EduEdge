from __future__ import annotations

import frappe
from frappe.model.document import Document

from eduedge.training.permissions import TRAINING_OVERSIGHT_ROLES


class EduEdgeTrainingProgress(Document):
	def validate(self) -> None:
		self._validate_owner()
		self.progress_percent = max(0, min(100, float(self.progress_percent or 0)))

	def _validate_owner(self) -> None:
		user = frappe.session.user
		if user == "Administrator":
			return
		roles = set(frappe.get_roles(user))
		if self.user != user and not TRAINING_OVERSIGHT_ROLES.intersection(roles):
			frappe.throw(
				"You can update only your own training progress.",
				frappe.PermissionError,
			)
