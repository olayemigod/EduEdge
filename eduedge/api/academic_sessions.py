from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.platform.access import require_eduedge_access
from eduedge.services.institution_context import get_effective_institution_context

ACADEMIC_YEAR_DOCTYPE = "Academic Year"
ACADEMIC_TERM_DOCTYPE = "Academic Term"
CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
MAX_SESSIONS = 500
MAX_TERMS = 1000


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_read_access() -> None:
	_require_login()
	require_eduedge_access(feature_key="academics", action="get_academic_sessions_page")
	for doctype in (ACADEMIC_YEAR_DOCTYPE, ACADEMIC_TERM_DOCTYPE):
		if not frappe.has_permission(doctype, "read"):
			frappe.throw(
				_("You are not permitted to view {0} records.").format(doctype),
				frappe.PermissionError,
			)


def _normalise(value: str | None) -> str:
	return " ".join(str(value or "").split())


def _active_context() -> dict:
	try:
		return get_effective_institution_context()
	 except Exception:
		return {}


def _session_rows(search: str = "") -> list[dict]:
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {
			"name": ["like", like],
			"academic_year_name": ["like", like],
		}
	return [
		dict(row)
		for row in frappe.get_list(
			ACADEMIC_YEAR_DOCTYPE,
			or_filters=or_filters,
			fields=["name", "academic_year_name", "year_start_date", "year_end_date", "modified"],
			order_by="year_start_date desc, name desc",
			page_length=MAX_SESSIONS,
		)
	]


def _term_rows(session_names: list[str]) -> list[dict]:
	if not session_names:
		return []
	return [
		dict(row)
		for row in frappe.get_list(
			ACADEMIC_TERM_DOCTYPE,
			filters={"academic_year": ["in", session_names]},
			fields=[
				"name",
				"title",
				"academic_year",
				"term_name",
				"term_start_date",
				"term_end_date",
				"modified",
			],
			order_by="academic_year desc, term_start_date asc, name asc",
			page_length=MAX_TERMS,
		)
	]


def _calendar_counts(session_names: list[str]) -> dict[str, int]:
	if not session_names or not frappe.db.exists("DocType", CALENDAR_DOCTYPE):
		return {}
	if not frappe.has_permission(CALENDAR_DOCTYPE, "read"):
		return {}
	counts: dict[str, int] = defaultdict(int)
	for row in frappe.get_list(
		CALENDAR_DOCTYPE,
		filters={"academic_year": ["in", session_names]},
		fields=["academic_year"],
		page_length=MAX_SESSIONS,
	):
		if row.academic_year:
			counts[row.academic_year] += 1
	return dict(counts)


def _status(start_date, end_date) -> str:
	today = getdate(nowdate())
	start = getdate(start_date)
	end = getdate(end_date)
	if start <= today <= end:
		return "Current"
	if today < start:
		return "Upcoming"
	return "Past"


@frappe.whitelist()
def get_academic_sessions_page(
	academic_year: str | None = None,
	search: str | None = None,
) -> dict:
	_require_read_access()
	search = _normalise(search)
	sessions = _session_rows(search)
	session_names = [row["name"] for row in sessions]
	terms = _term_rows(session_names)
	terms_by_year: dict[str, list[dict]] = defaultdict(list)
	for row in terms:
		terms_by_year[row["academic_year"]].append(row)
	calendar_counts = _calendar_counts(session_names)

	for row in sessions:
		row["term_count"] = len(terms_by_year.get(row["name"], []))
		row["calendar_count"] = calendar_counts.get(row["name"], 0)
		row["status"] = _status(row["year_start_date"], row["year_end_date"])

	selected = _normalise(academic_year)
	if selected not in session_names:
		selected = next((row["name"] for row in sessions if row["status"] == "Current"), "")
	if not selected and sessions:
		selected = sessions[0]["name"]
	selected_session = next((row for row in sessions if row["name"] == selected), None)
	selected_terms = terms_by_year.get(selected, [])

	return {
		"active_context": _active_context(),
		"filters": {"academic_year": selected, "search": search},
		"sessions": sessions,
		"selected_session": selected_session,
		"terms": selected_terms,
		"summary": {
			"session_count": len(sessions),
			"selected_term_count": len(selected_terms),
			"linked_calendar_count": calendar_counts.get(selected, 0),
			"current_session": next((row["name"] for row in sessions if row["status"] == "Current"), ""),
		},
		"permissions": {
			"can_create_session": frappe.has_permission(ACADEMIC_YEAR_DOCTYPE, "create"),
			"can_write_session": frappe.has_permission(ACADEMIC_YEAR_DOCTYPE, "write"),
			"can_create_term": frappe.has_permission(ACADEMIC_TERM_DOCTYPE, "create"),
			"can_write_term": frappe.has_permission(ACADEMIC_TERM_DOCTYPE, "write"),
		},
	}


def _validate_date_range(start_date: str | None, end_date: str | None, label: str) -> tuple:
	if not start_date or not end_date:
		frappe.throw(_("Enter Start Date and End Date for the {0}.").format(label), frappe.ValidationError)
	start = getdate(start_date)
	end = getdate(end_date)
	if end < start:
		frappe.throw(_("{0} End Date cannot be earlier than Start Date.").format(label), frappe.ValidationError)
	return start, end


def _validate_existing_terms_inside_session(session: str, start, end) -> None:
	rows = frappe.get_list(
		ACADEMIC_TERM_DOCTYPE,
		filters={"academic_year": session},
		fields=["name", "term_start_date", "term_end_date"],
		page_length=MAX_TERMS,
	)
	invalid = [
		row.name
		for row in rows
		if getdate(row.term_start_date) < start or getdate(row.term_end_date) > end
	]
	if invalid:
		frappe.throw(
			_("The new Session dates would exclude these Terms: {0}").format(", ".join(invalid)),
			frappe.ValidationError,
		)


@frappe.whitelist(methods=["POST"])
def save_academic_session(
	academic_year_name: str,
	start_date: str,
	end_date: str,
	session: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_session")
	name = _normalise(academic_year_name)
	if not name:
		frappe.throw(_("Enter the Academic Session name."), frappe.ValidationError)
	start, end = _validate_date_range(start_date, end_date, _("Session"))
	resolved_session = _normalise(session)

	if resolved_session:
		doc = frappe.get_doc(ACADEMIC_YEAR_DOCTYPE, resolved_session)
		doc.check_permission("write")
		if name != doc.academic_year_name:
			frappe.throw(
				_("Session identity cannot be changed in quick edit. Use the advanced form and Rename action when governance permits."),
				frappe.ValidationError,
			)
		_validate_existing_terms_inside_session(doc.name, start, end)
	else:
		if not frappe.has_permission(ACADEMIC_YEAR_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create Academic Sessions."), frappe.PermissionError)
		doc = frappe.new_doc(ACADEMIC_YEAR_DOCTYPE)
		doc.academic_year_name = name

	doc.year_start_date = start
	doc.year_end_date = end
	doc.save()
	return {
		"name": doc.name,
		"academic_year_name": doc.academic_year_name,
		"year_start_date": doc.year_start_date,
		"year_end_date": doc.year_end_date,
	}


def _validate_term_overlap(term_name: str, academic_year: str, start, end) -> None:
	rows = frappe.get_list(
		ACADEMIC_TERM_DOCTYPE,
		filters={"academic_year": academic_year, "name": ["!=", term_name or ""]},
		fields=["name", "term_start_date", "term_end_date"],
		page_length=MAX_TERMS,
	)
	for row in rows:
		other_start = getdate(row.term_start_date)
		other_end = getdate(row.term_end_date)
		if start <= other_end and end >= other_start:
			frappe.throw(
				_("Term dates overlap with {0}.").format(row.name),
				frappe.ValidationError,
			)


@frappe.whitelist(methods=["POST"])
def save_academic_term(
	academic_year: str,
	term_name: str,
	start_date: str,
	end_date: str,
	term: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_academic_term")
	resolved_year = _normalise(academic_year)
	resolved_name = _normalise(term_name)
	if not resolved_year or not frappe.db.exists(ACADEMIC_YEAR_DOCTYPE, resolved_year):
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	if not resolved_name:
		frappe.throw(_("Enter the Term name."), frappe.ValidationError)
	start, end = _validate_date_range(start_date, end_date, _("Term"))
	year = frappe.db.get_value(
		ACADEMIC_YEAR_DOCTYPE,
		resolved_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	if start < getdate(year.year_start_date) or end > getdate(year.year_end_date):
		frappe.throw(_("Term dates must fall inside the selected Academic Session."), frappe.ValidationError)

	resolved_term = _normalise(term)
	_validate_term_overlap(resolved_term, resolved_year, start, end)
	if resolved_term:
		doc = frappe.get_doc(ACADEMIC_TERM_DOCTYPE, resolved_term)
		doc.check_permission("write")
		if resolved_year != doc.academic_year or resolved_name != doc.term_name:
			frappe.throw(
				_("Term identity and Session cannot be changed in quick edit. Use the advanced form and Rename action when governance permits."),
				frappe.ValidationError,
			)
	else:
		if not frappe.has_permission(ACADEMIC_TERM_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create Academic Terms."), frappe.PermissionError)
		doc = frappe.new_doc(ACADEMIC_TERM_DOCTYPE)
		doc.academic_year = resolved_year
		doc.term_name = resolved_name

	doc.term_start_date = start
	doc.term_end_date = end
	doc.save()
	return {
		"name": doc.name,
		"academic_year": doc.academic_year,
		"term_name": doc.term_name,
		"term_start_date": doc.term_start_date,
		"term_end_date": doc.term_end_date,
	}
