from __future__ import annotations

import frappe

from eduedge.api import programme_offerings_safe as base

MAX_OPTION_ROWS = 500
CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"


def _all_academic_years(institution: str | None) -> list[dict]:
	"""Return readable Academic Sessions even before Institution Calendar setup.

	Programme Offering is sessional, so a newly created Academic Year must be
	discoverable immediately. Calendar readiness is reported separately and is
	still enforced by the existing save/controller validation before the Intake
	becomes operational.
	"""
	if not frappe.has_permission("Academic Year", "read"):
		return []

	years = frappe.get_list(
		"Academic Year",
		fields=["name", "year_start_date", "year_end_date"],
		order_by="year_start_date desc, name desc",
		page_length=MAX_OPTION_ROWS,
	)

	calendar_by_year: dict[str, dict] = {}
	if (
		institution
		and frappe.db.exists("DocType", CALENDAR_DOCTYPE)
		and frappe.has_permission(CALENDAR_DOCTYPE, "read")
	):
		calendars = frappe.get_list(
			CALENDAR_DOCTYPE,
			filters={"institution": institution, "enabled": 1},
			fields=["name", "academic_year", "start_date", "end_date", "is_current"],
			order_by="is_current desc, start_date desc, modified desc",
			page_length=MAX_OPTION_ROWS,
		)
		for calendar in calendars:
			if calendar.academic_year and calendar.academic_year not in calendar_by_year:
				calendar_by_year[calendar.academic_year] = dict(calendar)

	result = []
	for year in years:
		calendar = calendar_by_year.get(year.name) or {}
		result.append(
			{
				"name": year.name,
				"year_start_date": year.year_start_date,
				"year_end_date": year.year_end_date,
				"calendar": calendar.get("name"),
				"calendar_start_date": calendar.get("start_date"),
				"calendar_end_date": calendar.get("end_date"),
				"is_current": int(calendar.get("is_current") or 0),
				"calendar_ready": bool(calendar.get("name")),
			}
		)
	return result


@frappe.whitelist()
def get_programme_offering_session_options(
	institution: str | None = None,
	branch: str | None = None,
	academic_year: str | None = None,
	use_active_branch: int | str | bool = 0,
) -> dict:
	"""Programme Offering options with session discovery separated from calendar readiness."""
	result = base.get_programme_offering_options(
		institution=institution,
		branch=branch,
		academic_year=academic_year,
		use_active_branch=use_active_branch,
	)
	resolved_institution = result.get("institution") or institution
	options = dict(result.get("options") or {})
	options["academic_years"] = _all_academic_years(resolved_institution)
	result["options"] = options

	selected = str(academic_year or "").strip()
	selected_option = next((row for row in options["academic_years"] if row.get("name") == selected), None)
	result["selected_session_calendar_ready"] = bool(selected_option and selected_option.get("calendar_ready")) if selected else None
	return result
