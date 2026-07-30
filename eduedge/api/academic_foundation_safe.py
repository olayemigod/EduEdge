from __future__ import annotations

from frappe.utils import getdate, nowdate

from eduedge.api import academic_foundation as base


@base.frappe.whitelist()
def get_academic_foundation() -> dict:
	"""Return the existing permission-aware foundation payload with consistent calendar readiness.

	A configured enabled calendar is operationally usable even before an older record is
	repaired to carry the Current flag. Migration still normalises the database, while
	this response prevents the UI from reporting a false missing-calendar condition.
	"""
	payload = base.get_academic_foundation()
	calendars_by_institution: dict[str, list[dict]] = {}
	for calendar in payload.get("calendars") or []:
		if calendar.get("enabled"):
			calendars_by_institution.setdefault(calendar.get("institution"), []).append(calendar)

	for readiness in payload.get("readiness") or []:
		institution = readiness.get("institution")
		calendars = calendars_by_institution.get(institution, [])
		effective = _effective_calendar(calendars)
		if not effective:
			continue
		readiness["current_calendar"] = effective.get("name")
		readiness["effective_calendar"] = effective.get("name")
		readiness["effective_calendar_is_explicit_current"] = int(bool(effective.get("is_current")))
		readiness["issues"] = [
			issue
			for issue in readiness.get("issues") or []
			if issue.get("code") != "no_current_calendar"
		]
		if not effective.get("period_count") and not any(
			issue.get("code") == "calendar_without_periods" for issue in readiness["issues"]
		):
			readiness["issues"].append(
				{
					"code": "calendar_without_periods",
					"severity": "danger",
					"message": "The current calendar has no Academic Periods.",
				}
			)
		readiness["ready"] = not any(
			issue.get("severity") == "danger" for issue in readiness["issues"]
		)
	return payload


def _effective_calendar(calendars: list[dict]) -> dict | None:
	if not calendars:
		return None
	explicit = next((row for row in calendars if row.get("is_current")), None)
	if explicit:
		return explicit
	today = getdate(nowdate())
	covering = [
		row
		for row in calendars
		if row.get("start_date")
		and row.get("end_date")
		and getdate(row["start_date"]) <= today <= getdate(row["end_date"])
	]
	if covering:
		return sorted(
			covering,
			key=lambda row: (getdate(row.get("start_date")), row.get("modified") or ""),
			reverse=True,
		)[0]
	return sorted(
		calendars,
		key=lambda row: (getdate(row.get("start_date")), row.get("modified") or ""),
		reverse=True,
	)[0]
