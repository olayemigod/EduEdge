from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate


CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"


def execute() -> None:
	if not frappe.db.exists("DocType", CALENDAR_DOCTYPE):
		return

	institutions = frappe.get_all(
		CALENDAR_DOCTYPE,
		filters={"enabled": 1},
		pluck="institution",
		order_by="institution asc",
	)
	for institution in dict.fromkeys(value for value in institutions if value):
		if frappe.db.exists(
			CALENDAR_DOCTYPE,
			{"institution": institution, "enabled": 1, "is_current": 1},
		):
			continue
		calendar = _preferred_calendar(institution)
		if calendar:
			frappe.db.set_value(
				CALENDAR_DOCTYPE,
				calendar,
				"is_current",
				1,
				update_modified=False,
			)
	frappe.clear_cache(doctype=CALENDAR_DOCTYPE)


def _preferred_calendar(institution: str) -> str | None:
	today = getdate(nowdate())
	rows = frappe.get_all(
		CALENDAR_DOCTYPE,
		filters={
			"institution": institution,
			"enabled": 1,
			"start_date": ["<=", today],
			"end_date": [">=", today],
		},
		pluck="name",
		order_by="start_date desc, modified desc",
		limit=1,
	)
	if rows:
		return rows[0]
	rows = frappe.get_all(
		CALENDAR_DOCTYPE,
		filters={"institution": institution, "enabled": 1},
		pluck="name",
		order_by="start_date desc, modified desc",
		limit=1,
	)
	return rows[0] if rows else None
