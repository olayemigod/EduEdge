from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate


CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
PERIOD_DOCTYPE = "EduEdge Academic Calendar Period"
MAX_TERMS = 1000


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


def _configured_session_terms(academic_year: str) -> tuple[frappe._dict, list[frappe._dict]]:
	if not academic_year or not frappe.db.exists("Academic Year", academic_year):
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	if not frappe.has_permission("Academic Year", "read"):
		frappe.throw(_("You are not permitted to view Academic Sessions."), frappe.PermissionError)
	if not frappe.has_permission("Academic Term", "read"):
		frappe.throw(_("You are not permitted to view Academic Terms."), frappe.PermissionError)

	year = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	if not year or not year.year_start_date or not year.year_end_date:
		frappe.throw(
			_("Academic Session {0} must have Start Date and End Date before it can be used.").format(academic_year),
			frappe.ValidationError,
		)
	terms = frappe.get_all(
		"Academic Term",
		filters={"academic_year": academic_year},
		fields=["name", "term_start_date", "term_end_date"],
		order_by="term_start_date asc, name asc",
		limit_page_length=MAX_TERMS,
	)
	if not terms:
		frappe.throw(
			_("Create at least one dated Academic Term for Academic Session {0} before creating a Class Intake.").format(
				academic_year
			),
			frappe.ValidationError,
		)
	missing_dates = [row.name for row in terms if not row.term_start_date or not row.term_end_date]
	if missing_dates:
		frappe.throw(
			_("Complete Start Date and End Date for these Academic Terms before using the Session: {0}").format(
				", ".join(missing_dates)
			),
			frappe.ValidationError,
		)
	return year, terms


def ensure_institution_calendar(institution: str, academic_year: str) -> dict:
	"""Create or reconcile the internal Institution calendar for a configured Session.

	Academic Year and Academic Term remain Frappe Education's shared masters. The
	Institution calendar is EduEdge's institution-specific operational mapping and
	should not require a second manual setup step for ordinary Class Intake work.
	Existing period-level governance such as result publication dates is preserved.
	"""
	institution = str(institution or "").strip()
	academic_year = str(academic_year or "").strip()
	if not institution or not frappe.db.exists("EduEdge Institution", institution):
		frappe.throw(_("Select a valid Institution."), frappe.ValidationError)
	institution_doc = frappe.get_doc("EduEdge Institution", institution)
	institution_doc.check_permission("read")
	if not institution_doc.enabled:
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)

	year, terms = _configured_session_terms(academic_year)
	existing = frappe.db.exists(
		CALENDAR_DOCTYPE,
		{"institution": institution, "academic_year": academic_year},
	)
	created = False
	changed = False
	if existing:
		doc = frappe.get_doc(CALENDAR_DOCTYPE, existing)
		if not doc.enabled:
			frappe.throw(
				_("The Institution Academic Calendar for {0} exists but is disabled. Enable it before using the Session.").format(
					academic_year
				),
				frappe.ValidationError,
			)
		if getdate(doc.start_date) != getdate(year.year_start_date):
			doc.start_date = year.year_start_date
			changed = True
		if getdate(doc.end_date) != getdate(year.year_end_date):
			doc.end_date = year.year_end_date
			changed = True
		existing_periods = {row.academic_term: row for row in doc.periods or [] if row.academic_term}
		for index, term in enumerate(terms, start=1):
			period = existing_periods.get(term.name)
			if not period:
				doc.append(
					"periods",
					{
						"academic_term": term.name,
						"start_date": term.term_start_date,
						"end_date": term.term_end_date,
						"sequence": index * 10,
					},
				)
				changed = True
				continue
			if getdate(period.start_date) != getdate(term.term_start_date):
				period.start_date = term.term_start_date
				changed = True
			if getdate(period.end_date) != getdate(term.term_end_date):
				period.end_date = term.term_end_date
				changed = True
			if period.sequence != index * 10:
				period.sequence = index * 10
				changed = True
		if changed:
			doc.check_permission("write")
			doc.save()
	else:
		if not frappe.has_permission(CALENDAR_DOCTYPE, "create"):
			frappe.throw(
				_("You are not permitted to prepare the Institution Academic Calendar required for this Class Intake."),
				frappe.PermissionError,
			)
		doc = frappe.new_doc(CALENDAR_DOCTYPE)
		doc.institution = institution
		doc.academic_year = academic_year
		doc.start_date = year.year_start_date
		doc.end_date = year.year_end_date
		doc.enabled = 1
		for index, term in enumerate(terms, start=1):
			doc.append(
				"periods",
				{
					"academic_term": term.name,
					"start_date": term.term_start_date,
					"end_date": term.term_end_date,
					"sequence": index * 10,
				},
			)
		doc.insert()
		created = True
		changed = True

	return {
		"name": doc.name,
		"institution": doc.institution,
		"academic_year": doc.academic_year,
		"start_date": doc.start_date,
		"end_date": doc.end_date,
		"enabled": int(doc.enabled or 0),
		"is_current": int(doc.is_current or 0),
		"period_count": len(doc.periods or []),
		"created": created,
		"changed": changed,
	}


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
