from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from eduedge.cbt.service import _refresh_timeout_state


def refresh_attempt_timeouts() -> None:
	"""Advance expired active attempts without discarding pending offline answers."""
	now = now_datetime()
	attempt_names = frappe.get_all(
		"EduEdge CBT Attempt",
		filters={
			"status": ["in", ["In Progress", "Pending Sync"]],
			"server_deadline": ["<", now],
		},
		pluck="name",
		page_length=5000,
	)
	for name in attempt_names:
		attempt = frappe.get_doc("EduEdge CBT Attempt", name)
		_refresh_timeout_state(attempt)
