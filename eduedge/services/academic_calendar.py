from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
PERIOD_DOCTYPE = "EduEdge Academic Calendar Period"


def get_branch_institution(branch: str | None) -> str | None:
	if not branch:
		return None
	return frappe.db.get_value("EduEdge School Branch", branch, "institution")


def get_enabled_institution_calendar(
	institution: str | None,
	*,
	academic_year: str | None = None,
	reference_date: str | None = None,
) -> frappe._dict | None:
	if not institution or not frappe.db.exists("DocType", CALENDAR_DOCTYPE):
		return None
	filters: dict = {"institution": institution, "enabled": 1}
	if academic_year:
		filters["academic_year"] = academic_year
	if reference_date:
		target_date = getdate(reference_date)
		filters["start_date"] = ["<=", target_date]
		filters["end_date"] = [">=", target_date]
	rows = frappe.get_all(
		CALENDAR_DOCTYPE,
		filters=filters,
		fields=["name", "institution", "academic_year", "start_date", "end_date", "is_current"],
		order_by="is_current desc, start_date desc, modified desc",
		limit=1,
	)
	return rows[0] if rows else None


def get_calendar_period(
	calendar: str | None,
	*,
	academic_term: str | None = None,
	reference_date: str | None = None,
) -> frappe._dict | None:
	if not calendar or not frappe.db.exists("DocType", PERIOD_DOCTYPE):
		return None
	filters: dict = {
		"parent": calendar,
		"parenttype": CALENDAR_DOCTYPE,
	}
	if academic_term:
		filters["academic_term"] = academic_term
	if reference_date:
		target_date = getdate(reference_date)
		filters["start_date"] = ["<=", target_date]
		filters["end_date"] = [">=", target_date]
	rows = frappe.get_all(
		PERIOD_DOCTYPE,
		filters=filters,
		fields=["academic_term", "start_date", "end_date", "sequence", "result_publication_date"],
		order_by="sequence asc, start_date asc",
		limit=1,
	)
	return rows[0] if rows else None


def resolve_academic_defaults(branch: str, reference_date: str | None = None) -> dict:
	target_date = getdate(reference_date or nowdate())
	institution = get_branch_institution(branch)

	if institution:
		calendar = get_enabled_institution_calendar(institution, reference_date=str(target_date))
		period = get_calendar_period(calendar.name, reference_date=str(target_date)) if calendar else None
		return {
			"institution": institution,
			"calendar": calendar.name if calendar else None,
			"academic_year": calendar.academic_year if calendar else None,
			"academic_term": period.academic_term if period else None,
			"calendar_start_date": calendar.start_date if calendar else None,
			"calendar_end_date": calendar.end_date if calendar else None,
			"period_start_date": period.start_date if period else None,
			"period_end_date": period.end_date if period else None,
			"result_publication_date": period.result_publication_date if period else None,
			"source": "institution_calendar" if calendar else "institution_calendar_missing",
			"ready": bool(calendar and period),
			"calendar_gap": bool(calendar and not period),
		}

	# Compatibility only for installations that have no Institution context yet.
	academic_year = frappe.db.get_single_value("Education Settings", "current_academic_year")
	academic_term = frappe.db.get_single_value("Education Settings", "current_academic_term")
	return {
		"institution": None,
		"calendar": None,
		"academic_year": academic_year,
		"academic_term": academic_term,
		"calendar_start_date": None,
		"calendar_end_date": None,
		"period_start_date": None,
		"period_end_date": None,
		"result_publication_date": None,
		"source": "education_settings_legacy",
		"ready": bool(academic_year),
		"calendar_gap": False,
	}


def assert_institution_calendar_context(
	*,
	branch: str,
	academic_year: str,
	academic_term: str | None = None,
	reference_date: str | None = None,
) -> dict:
	institution = get_branch_institution(branch)
	if not institution:
		frappe.throw(
			_("The selected School Branch / Campus must belong to an Institution."),
			frappe.ValidationError,
		)
	calendar = get_enabled_institution_calendar(
		institution,
		academic_year=academic_year,
		reference_date=reference_date,
	)
	if not calendar:
		date_suffix = _(" covering {0}").format(getdate(reference_date)) if reference_date else ""
		frappe.throw(
			_("Configure an enabled Institution Academic Calendar for Academic Session {0}{1}.").format(
				academic_year,
				date_suffix,
			),
			frappe.ValidationError,
		)

	period = None
	if academic_term or reference_date:
		period = get_calendar_period(
			calendar.name,
			academic_term=academic_term,
			reference_date=reference_date,
		)
	if academic_term and not period:
		frappe.throw(
			_("Academic Period {0} is not configured on this Institution's Academic Calendar for {1}.").format(
				academic_term,
				academic_year,
			),
			frappe.ValidationError,
		)
	if reference_date and not academic_term and not period:
		frappe.throw(
			_("The selected date falls outside every configured Academic Period for Academic Session {0}.").format(
				academic_year
			),
			frappe.ValidationError,
		)
	return {
		"institution": institution,
		"calendar": calendar.name,
		"academic_year": calendar.academic_year,
		"academic_term": period.academic_term if period else academic_term,
		"period_start_date": period.start_date if period else None,
		"period_end_date": period.end_date if period else None,
	}
