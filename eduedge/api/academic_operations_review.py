from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import academic_operations_safe as safe


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	payload = safe.get_operations_context(branch=branch, date=date, student_group=student_group)
	calendar = payload.get("academic_calendar") or {}
	selected_branch = payload.get("selected_branch") or {}
	institution = selected_branch.get("institution")

	if institution and calendar.get("source") != "institution_calendar":
		# Never expose every active Student Group merely because a Branch-specific
		# Session could not be resolved. Existing schedules remain visible for the
		# selected date so historical operational records are not hidden.
		payload["student_groups"] = []
		payload.setdefault("counts", {})["student_groups"] = 0
		payload.setdefault("filters", {})["student_group"] = None
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _(
				"No enabled Institution Academic Calendar covers the selected date. Configure the Academic Session and its Terms before creating or selecting a Class Arm."
			),
		}
	elif institution and not calendar.get("academic_term"):
		payload["academic_calendar"] = {
			**calendar,
			"ready": False,
			"blocking_issue": _(
				"The selected date is inside the Academic Session but outside every configured Term / Academic Period."
			),
		}
	else:
		payload["academic_calendar"] = {**calendar, "ready": bool(calendar.get("academic_year"))}
	return payload
