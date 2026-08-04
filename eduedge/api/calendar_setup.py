from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.platform.access import require_eduedge_access

CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
PERIOD_DOCTYPE = "EduEdge Academic Calendar Period"
MAX_ACADEMIC_YEARS = 500
MAX_TERMS = 1000


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _get_institution(institution: str):
	institution = str(institution or "").strip()
	if not institution:
		frappe.throw(_("Select an Institution."), frappe.ValidationError)
	doc = frappe.get_doc("EduEdge Institution", institution)
	doc.check_permission("read")
	if not cint(doc.enabled):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
	return doc


def _academic_year_rows() -> list[dict]:
	if not frappe.has_permission("Academic Year", "read"):
		frappe.throw(_("You are not permitted to view Academic Years."), frappe.PermissionError)
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Year",
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc, name desc",
			page_length=MAX_ACADEMIC_YEARS,
		)
	]


def _term_rows(academic_year: str) -> list[dict]:
	if not frappe.has_permission("Academic Term", "read"):
		frappe.throw(_("You are not permitted to view Academic Terms."), frappe.PermissionError)
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Term",
			filters={"academic_year": academic_year},
			fields=["name", "academic_year", "term_start_date", "term_end_date"],
			order_by="term_start_date asc, name asc",
			page_length=MAX_TERMS,
		)
	]


@frappe.whitelist()
def get_calendar_dialog_context(
	institution: str,
	academic_year: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="get_calendar_dialog_context")
	institution_doc = _get_institution(institution)
	if not frappe.has_permission(CALENDAR_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create Institution Academic Calendars."), frappe.PermissionError)

	years = _academic_year_rows()
	calendar_rows = frappe.get_list(
		CALENDAR_DOCTYPE,
		filters={"institution": institution_doc.name},
		fields=["name", "academic_year", "is_current", "enabled"],
		page_length=MAX_ACADEMIC_YEARS,
	) if frappe.has_permission(CALENDAR_DOCTYPE, "read") else []
	existing_by_year = {row.academic_year: row.name for row in calendar_rows if row.academic_year}
	has_current_calendar = any(cint(row.is_current) and cint(row.enabled) for row in calendar_rows)

	options = [
		{
			"value": row["name"],
			"label": row["name"],
			"start_date": row.get("year_start_date"),
			"end_date": row.get("year_end_date"),
			"existing_calendar": existing_by_year.get(row["name"]),
			"available": not bool(existing_by_year.get(row["name"])),
		}
		for row in years
	]

	selected_year = str(academic_year or "").strip()
	preview = None
	if selected_year:
		year = next((row for row in years if row["name"] == selected_year), None)
		if not year:
			frappe.throw(_("Select a valid Academic Year."), frappe.ValidationError)
		terms = _term_rows(selected_year)
		preview = {
			"academic_year": selected_year,
			"start_date": year.get("year_start_date"),
			"end_date": year.get("year_end_date"),
			"existing_calendar": existing_by_year.get(selected_year),
			"periods": [
				{
					"academic_term": row["name"],
					"start_date": row.get("term_start_date"),
					"end_date": row.get("term_end_date"),
					"sequence": (index + 1) * 10,
				}
				for index, row in enumerate(terms)
			],
		}

	return {
		"institution": {
			"name": institution_doc.name,
			"institution_name": institution_doc.institution_name,
			"company": institution_doc.company,
		},
		"academic_year_options": options,
		"preview": preview,
		"has_current_calendar": has_current_calendar,
	}


@frappe.whitelist(methods=["POST"])
def create_calendar_from_foundation(
	institution: str,
	academic_year: str,
	is_current: int | str = 0,
	notes: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="create_calendar_from_foundation")
	institution_doc = _get_institution(institution)
	if not frappe.has_permission(CALENDAR_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create Institution Academic Calendars."), frappe.PermissionError)

	academic_year = str(academic_year or "").strip()
	if not academic_year:
		frappe.throw(_("Select an Academic Year."), frappe.ValidationError)
	year_doc = frappe.get_doc("Academic Year", academic_year)
	year_doc.check_permission("read")
	if not year_doc.year_start_date or not year_doc.year_end_date:
		frappe.throw(
			_("The selected Academic Year must have Start Date and End Date before it can be used."),
			frappe.ValidationError,
		)

	existing = frappe.db.exists(
		CALENDAR_DOCTYPE,
		{"institution": institution_doc.name, "academic_year": academic_year},
	)
	if existing:
		frappe.throw(
			_("An Institution Academic Calendar already exists for this Academic Year: {0}").format(existing),
			frappe.DuplicateEntryError,
		)

	terms = _term_rows(academic_year)
	if not terms:
		frappe.throw(
			_("Create at least one Academic Term for this Academic Year before creating the Institution calendar."),
			frappe.ValidationError,
		)
	missing_dates = [row["name"] for row in terms if not row.get("term_start_date") or not row.get("term_end_date")]
	if missing_dates:
		frappe.throw(
			_("Complete Start Date and End Date for these Academic Terms: {0}").format(
				", ".join(missing_dates)
			),
			frappe.ValidationError,
		)

	doc = frappe.new_doc(CALENDAR_DOCTYPE)
	doc.institution = institution_doc.name
	doc.academic_year = academic_year
	doc.start_date = year_doc.year_start_date
	doc.end_date = year_doc.year_end_date
	doc.enabled = 1
	doc.is_current = cint(is_current)
	doc.notes = str(notes or "").strip()
	for index, term in enumerate(terms):
		doc.append(
			"periods",
			{
				"academic_term": term["name"],
				"start_date": term.get("term_start_date"),
				"end_date": term.get("term_end_date"),
				"sequence": (index + 1) * 10,
			},
		)
	doc.insert()
	return {
		"name": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"start_date": doc.start_date,
		"end_date": doc.end_date,
		"is_current": cint(doc.is_current),
		"enabled": cint(doc.enabled),
		"period_count": len(doc.periods or []),
		"periods": [
			{
				"academic_term": row.academic_term,
				"start_date": row.start_date,
				"end_date": row.end_date,
				"sequence": row.sequence,
			}
			for row in doc.periods or []
		],
	}
