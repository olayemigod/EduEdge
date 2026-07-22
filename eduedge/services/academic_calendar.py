from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate


def resolve_academic_defaults(branch: str, reference_date: str | None = None) -> dict:
	target_date = getdate(reference_date or nowdate())
	institution = frappe.db.get_value("EduEdge School Branch", branch, "institution") if branch else None
	calendar = None
	period = None
	if institution and frappe.db.exists("DocType", "EduEdge Institution Academic Calendar"):
		rows = frappe.get_all(
			"EduEdge Institution Academic Calendar",
			filters={
				"institution": institution,
				"enabled": 1,
				"start_date": ["<=", target_date],
				"end_date": [">=", target_date],
			},
			fields=["name", "institution", "academic_year", "start_date", "end_date", "is_current"],
			order_by="is_current desc, start_date desc, modified desc",
			limit=1,
		)
		calendar = rows[0] if rows else None
		if calendar:
			periods = frappe.get_all(
				"EduEdge Academic Calendar Period",
				filters={
					"parent": calendar.name,
					"parenttype": "EduEdge Institution Academic Calendar",
					"start_date": ["<=", target_date],
					"end_date": [">=", target_date],
				},
				fields=["academic_term", "start_date", "end_date", "sequence", "result_publication_date"],
				order_by="sequence asc, start_date asc",
				limit=1,
			)
			period = periods[0] if periods else None

	if calendar:
		academic_year = calendar.academic_year
		# A gap between configured periods is intentional. Do not leak a site-wide
		# Education Settings term into this Institution's calendar context.
		academic_term = period.academic_term if period else None
	else:
		academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
		academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	return {
		"institution": institution,
		"calendar": calendar.name if calendar else None,
		"academic_year": academic_year,
		"academic_term": academic_term,
		"period_start_date": period.start_date if period else None,
		"period_end_date": period.end_date if period else None,
		"result_publication_date": period.result_publication_date if period else None,
		"source": "institution_calendar" if calendar else "education_settings",
	}
