from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_terminology_map


CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
MAX_EDITOR_PERIODS = 24


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _clean(value: Any, *, limit: int = 500) -> str:
	text = str(value or "").strip()
	if len(text) > limit:
		frappe.throw(_("A calendar value is longer than the allowed limit."), frappe.ValidationError)
	return text


def _parse_periods(value: str | list | None) -> list[dict]:
	if not value:
		return []
	rows = value if isinstance(value, list) else frappe.parse_json(value)
	if not isinstance(rows, list):
		frappe.throw(_("Academic calendar periods must be supplied as a list."), frappe.ValidationError)
	if len(rows) > MAX_EDITOR_PERIODS:
		frappe.throw(
			_("An Institution Academic Calendar cannot contain more than {0} periods in this editor.").format(
				MAX_EDITOR_PERIODS
			),
			frappe.ValidationError,
		)
	cleaned = []
	for index, row in enumerate(rows, start=1):
		if not isinstance(row, dict):
			frappe.throw(_("Each academic calendar period must be an object."), frappe.ValidationError)
		cleaned.append(
			{
				"academic_term": _clean(row.get("academic_term"), limit=140),
				"start_date": _clean(row.get("start_date"), limit=20),
				"end_date": _clean(row.get("end_date"), limit=20),
				"sequence": cint(row.get("sequence")) or index * 10,
				"result_publication_date": _clean(row.get("result_publication_date"), limit=20) or None,
			}
		)
	return cleaned


def _get_institution(institution: str):
	name = _clean(institution, limit=140)
	if not name:
		frappe.throw(_("Select an Institution first."), frappe.ValidationError)
	doc = frappe.get_doc("EduEdge Institution", name)
	doc.check_permission("read")
	if not cint(doc.enabled):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
	return doc


def _institution_terminology(institution_doc) -> dict:
	institution_type = _clean(institution_doc.institution_type, limit=80)
	institution_type_name = institution_type
	if institution_type and frappe.db.exists("EduEdge Institution Type", institution_type):
		institution_type_name = (
			frappe.db.get_value("EduEdge Institution Type", institution_type, "institution_type_name")
			or institution_type
		)
	return {
		"institution": institution_doc.name,
		"institution_name": institution_doc.institution_name or institution_doc.name,
		"institution_type": institution_type,
		"institution_type_name": institution_type_name,
		"company": institution_doc.company or "",
		"terms": get_terminology_map(institution_type),
	}


def _calendar_values(doc) -> dict:
	return {
		"name": doc.name if not doc.is_new() else "",
		"institution": doc.institution or "",
		"academic_year": doc.academic_year or "",
		"is_current": cint(doc.is_current),
		"enabled": cint(doc.enabled),
		"start_date": doc.start_date,
		"end_date": doc.end_date,
		"notes": doc.notes or "",
		"periods": [
			{
				"name": row.name or "",
				"academic_term": row.academic_term or "",
				"start_date": row.start_date,
				"end_date": row.end_date,
				"sequence": cint(row.sequence) or row.idx * 10,
				"result_publication_date": row.result_publication_date,
			}
			for row in (doc.periods or [])
		],
	}


@frappe.whitelist()
def get_institution_terminology(institution: str) -> dict:
	_require_login()
	institution_doc = _get_institution(institution)
	return _institution_terminology(institution_doc)


@frappe.whitelist()
def get_academic_calendar_editor(
	institution: str | None = None,
	calendar: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="view_academic_calendar")

	calendar_name = _clean(calendar, limit=140)
	if calendar_name:
		doc = frappe.get_doc(CALENDAR_DOCTYPE, calendar_name)
		doc.check_permission("read")
		institution_doc = _get_institution(doc.institution)
		can_save = bool(doc.has_permission("write"))
	else:
		institution_doc = _get_institution(institution or "")
		if not frappe.has_permission(CALENDAR_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create Institution Academic Calendars."), frappe.PermissionError)
		doc = frappe.new_doc(CALENDAR_DOCTYPE)
		doc.institution = institution_doc.name
		doc.enabled = 1
		can_save = True

	return {
		"values": _calendar_values(doc),
		"terminology": _institution_terminology(institution_doc),
		"can_save": can_save,
		"is_new": bool(doc.is_new()),
		"full_form_route": f"/app/eduedge-institution-academic-calendar/{doc.name}" if not doc.is_new() else "",
	}


@frappe.whitelist(methods=["POST"])
def save_academic_calendar(
	institution: str,
	academic_year: str,
	start_date: str,
	end_date: str,
	periods: str | list,
	calendar: str | None = None,
	is_current: int | str = 0,
	enabled: int | str = 1,
	notes: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_calendar")

	calendar_name = _clean(calendar, limit=140)
	institution_doc = _get_institution(institution)
	if calendar_name:
		doc = frappe.get_doc(CALENDAR_DOCTYPE, calendar_name)
		doc.check_permission("write")
	else:
		if not frappe.has_permission(CALENDAR_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create Institution Academic Calendars."), frappe.PermissionError)
		doc = frappe.new_doc(CALENDAR_DOCTYPE)

	academic_year_name = _clean(academic_year, limit=140)
	if not academic_year_name:
		frappe.throw(_("Academic Year is required."), frappe.ValidationError)
	academic_year_doc = frappe.get_doc("Academic Year", academic_year_name)
	academic_year_doc.check_permission("read")

	period_rows = _parse_periods(periods)
	for row in period_rows:
		if not row["academic_term"]:
			frappe.throw(_("Academic Term is required on every calendar row."), frappe.ValidationError)
		term_doc = frappe.get_doc("Academic Term", row["academic_term"])
		term_doc.check_permission("read")

	doc.institution = institution_doc.name
	doc.academic_year = academic_year_name
	doc.is_current = cint(is_current)
	doc.enabled = cint(enabled)
	doc.start_date = _clean(start_date, limit=20)
	doc.end_date = _clean(end_date, limit=20)
	doc.notes = _clean(notes, limit=2000)
	doc.set("periods", [])
	for row in period_rows:
		doc.append("periods", row)
	doc.save()
	frappe.clear_cache(doctype=CALENDAR_DOCTYPE)
	return {
		"calendar": _calendar_values(doc),
		"terminology": _institution_terminology(institution_doc),
	}
