from __future__ import annotations

from datetime import datetime, time
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch


EVENT_DOCTYPE = "EduEdge School Event"
MAX_ITEMS = 5000
EVENT_STATUSES = {"Draft", "Scheduled", "Published", "Cancelled", "Completed", "Archived"}
STATUS_TRANSITIONS = {
	"Draft": {"Scheduled", "Published", "Cancelled", "Archived"},
	"Scheduled": {"Draft", "Published", "Cancelled", "Archived"},
	"Published": {"Completed", "Cancelled", "Archived"},
	"Cancelled": {"Scheduled", "Archived"},
	"Completed": {"Archived"},
	"Archived": set(),
}
EDITABLE_EVENT_FIELDS = (
	"event_title",
	"event_type",
	"school_branch",
	"academic_year",
	"academic_term",
	"starts_on",
	"ends_on",
	"all_day",
	"venue",
	"audience_scope",
	"program",
	"student_group",
	"visibility",
	"registration_required",
	"attendance_required",
	"organiser",
	"reminder_minutes_before",
	"publish_from",
	"publish_until",
	"description",
)


def _require_login() -> None:
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	require_eduedge_access(feature_key="academics", action="school_calendar")


def _parse_json(value: Any) -> dict:
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Expected a JSON object."), frappe.ValidationError)
	return parsed


def _branch_options() -> list[dict]:
	return [dict(row) for row in get_allowed_school_branches() if row.get("name")]


def _resolve_branch(branch: str | None, options: list[dict]) -> str:
	allowed = {row["name"] for row in options}
	if branch:
		if branch not in allowed:
			frappe.throw(_("Select a permitted School Branch / Campus."), frappe.PermissionError)
		return branch
	current = (get_current_school_branch() or {}).get("name")
	if current in allowed:
		return current
	return options[0]["name"] if options else ""


def _session_options() -> list[dict]:
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Year",
			fields=["name", "academic_year_name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc, name desc",
			page_length=500,
		)
	]


def _default_session(sessions: list[dict]) -> str:
	today = getdate()
	for row in sessions:
		if row.get("year_start_date") and row.get("year_end_date") and getdate(row["year_start_date"]) <= today <= getdate(row["year_end_date"]):
			return row["name"]
	return sessions[0]["name"] if sessions else ""


def _terms(academic_year: str) -> list[dict]:
	if not academic_year:
		return []
	return [
		dict(row)
		for row in frappe.get_list(
			"Academic Term",
			filters={"academic_year": academic_year},
			fields=["name", "term_name", "term_start_date", "term_end_date"],
			order_by="term_start_date asc, name asc",
			page_length=500,
		)
	]


def _range(academic_year: str, start: str | None, end: str | None) -> tuple:
	year = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
		as_dict=True,
	)
	if not year:
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	start_date = getdate(start) if start else getdate(year.year_start_date)
	end_date = getdate(end) if end else getdate(year.year_end_date)
	if end_date < start_date:
		frappe.throw(_("Calendar end cannot be earlier than start."), frappe.ValidationError)
	if (end_date - start_date).days > 370:
		frappe.throw(_("School Calendar requests are limited to 370 days."), frappe.ValidationError)
	return start_date, end_date


def _datetime_on(date_value, time_value=None, *, end_of_day: bool = False) -> str:
	day = getdate(date_value)
	if time_value in (None, ""):
		clock = time(23, 59, 59) if end_of_day else time(0, 0, 0)
	else:
		text = str(time_value)
		parts = text.split(":")
		clock = time(int(parts[0]), int(parts[1]), int(float(parts[2])) if len(parts) > 2 else 0)
	return datetime.combine(day, clock).isoformat(sep=" ")


def _calendar_item(*, source_type: str, source_name: str, title: str, starts_on: str, ends_on: str, all_day: bool, category: str, status: str = "", route: str = "", audience: str = "", venue: str = "", editable: bool = False) -> dict:
	return {
		"id": f"{source_type}:{source_name}",
		"source_type": source_type,
		"source_name": source_name,
		"title": title,
		"starts_on": starts_on,
		"ends_on": ends_on,
		"all_day": bool(all_day),
		"category": category,
		"status": status,
		"route": route,
		"audience": audience,
		"venue": venue,
		"editable": bool(editable),
	}


def _academic_period_items(institution: str, academic_year: str, start_date, end_date) -> list[dict]:
	calendar = frappe.db.get_value(
		"EduEdge Institution Academic Calendar",
		{"institution": institution, "academic_year": academic_year, "enabled": 1},
		"name",
	)
	if not calendar:
		return []
	rows = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={"parent": calendar, "parenttype": "EduEdge Institution Academic Calendar"},
		fields=["name", "academic_term", "start_date", "end_date", "result_publication_date"],
		order_by="sequence asc, start_date asc",
		page_length=500,
	)
	items: list[dict] = []
	for row in rows:
		if getdate(row.end_date) < start_date or getdate(row.start_date) > end_date:
			continue
		items.append(
			_calendar_item(
				source_type="Academic Period",
				source_name=row.name,
				title=row.academic_term,
				starts_on=_datetime_on(row.start_date),
				ends_on=_datetime_on(row.end_date, end_of_day=True),
				all_day=True,
				category="Academic",
				status="Academic Period",
				route="/app/eduedge-academic-foundation",
			)
		)
		if row.result_publication_date and start_date <= getdate(row.result_publication_date) <= end_date:
			items.append(
				_calendar_item(
					source_type="Academic Milestone",
					source_name=f"{row.name}:result-publication",
					title=f"{row.academic_term} · Result Publication",
					starts_on=_datetime_on(row.result_publication_date),
					ends_on=_datetime_on(row.result_publication_date, end_of_day=True),
					all_day=True,
					category="Result Publication",
					status="Planned",
					route="/app/eduedge-assessment-operations",
				)
			)
	return items


def _assessment_items(branch: str, academic_year: str, academic_term: str | None, start_date, end_date) -> list[dict]:
	if not frappe.has_permission("Assessment Plan", "read"):
		return []
	filters: dict = {BRANCH_FIELD: branch, "academic_year": academic_year, "schedule_date": ["between", [start_date, end_date]]}
	if academic_term:
		filters["academic_term"] = academic_term
	rows = frappe.get_list(
		"Assessment Plan",
		filters=filters,
		fields=["name", "assessment_name", "course", "student_group", "schedule_date", "from_time", "to_time", "room", "docstatus"],
		order_by="schedule_date asc, from_time asc",
		page_length=MAX_ITEMS,
	)
	return [
		_calendar_item(
			source_type="Assessment Plan",
			source_name=row.name,
			title=f"{row.assessment_name or 'Assessment'}{f' · {row.course}' if row.course else ''}",
			starts_on=_datetime_on(row.schedule_date, row.from_time),
			ends_on=_datetime_on(row.schedule_date, row.to_time or row.from_time),
			all_day=False,
			category="Assessment",
			status="Submitted" if cint(row.docstatus) == 1 else "Draft",
			route=f"/app/assessment-plan/{row.name}",
			venue=row.room or "",
		)
		for row in rows
	]


def _cbt_items(branch: str, academic_year: str, academic_term: str | None, start_date, end_date) -> list[dict]:
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read"):
		return []
	filters: dict = {"exam_scope": "School Examination", "school_branch": branch, "academic_year": academic_year, "scheduled_start": ["between", [_datetime_on(start_date), _datetime_on(end_date, end_of_day=True)]]}
	if academic_term:
		filters["academic_term"] = academic_term
	rows = frappe.get_list(
		"EduEdge CBT Exam Schedule",
		filters=filters,
		fields=["name", "schedule_title", "course", "student_group", "scheduled_start", "scheduled_end", "examination_centre", "status"],
		order_by="scheduled_start asc",
		page_length=MAX_ITEMS,
	)
	return [
		_calendar_item(
			source_type="CBT Schedule",
			source_name=row.name,
			title=f"{row.schedule_title}{f' · {row.course}' if row.course else ''}",
			starts_on=str(row.scheduled_start),
			ends_on=str(row.scheduled_end or row.scheduled_start),
			all_day=False,
			category="CBT",
			status=row.status,
			route="/app/eduedge-cbt-schedules",
			venue=row.examination_centre or "",
		)
		for row in rows
	]


def _school_event_items(branch: str, academic_year: str, academic_term: str | None, start_date, end_date, event_type: str | None, audience: str | None) -> list[dict]:
	if not frappe.has_permission(EVENT_DOCTYPE, "read"):
		return []
	filters: dict = {
		"school_branch": branch,
		"academic_year": academic_year,
		"status": ["!=", "Archived"],
		"starts_on": ["<=", _datetime_on(end_date, end_of_day=True)],
		"ends_on": [">=", _datetime_on(start_date)],
	}
	if academic_term:
		filters["academic_term"] = academic_term
	if event_type:
		filters["event_type"] = event_type
	if audience:
		filters["audience_scope"] = audience
	rows = frappe.get_list(
		EVENT_DOCTYPE,
		filters=filters,
		fields=["name", "event_title", "event_type", "starts_on", "ends_on", "all_day", "venue", "audience_scope", "visibility", "status"],
		order_by="starts_on asc, event_title asc",
		page_length=MAX_ITEMS,
	)
	return [
		_calendar_item(
			source_type="School Event",
			source_name=row.name,
			title=row.event_title,
			starts_on=str(row.starts_on),
			ends_on=str(row.ends_on),
			all_day=bool(cint(row.all_day)),
			category=row.event_type,
			status=row.status,
			route=f"/app/eduedge-school-event/{row.name}",
			audience=row.audience_scope,
			venue=row.venue or "",
			editable=bool(frappe.has_permission(EVENT_DOCTYPE, "write")),
		)
		for row in rows
	]


def _teaching_items(branch: str, academic_year: str, start_date, end_date) -> list[dict]:
	if not frappe.has_permission("Course Schedule", "read") or not frappe.get_meta("Course Schedule").has_field(BRANCH_FIELD):
		return []
	rows = frappe.get_list(
		"Course Schedule",
		filters={BRANCH_FIELD: branch, "schedule_date": ["between", [start_date, end_date]]},
		fields=["name", "course", "student_group", "schedule_date", "from_time", "to_time", "room", "instructor"],
		order_by="schedule_date asc, from_time asc",
		page_length=MAX_ITEMS,
	)
	return [
		_calendar_item(
			source_type="Course Schedule",
			source_name=row.name,
			title=f"{row.course or 'Teaching'}{f' · {row.student_group}' if row.student_group else ''}",
			starts_on=_datetime_on(row.schedule_date, row.from_time),
			ends_on=_datetime_on(row.schedule_date, row.to_time or row.from_time),
			all_day=False,
			category="Teaching",
			status="Scheduled",
			route=f"/app/course-schedule/{row.name}",
			venue=row.room or "",
		)
		for row in rows
	]


def _event_form_options(branch: str, academic_year: str, program: str | None = None) -> dict:
	terms = _terms(academic_year)
	offerings = frappe.get_list(
		"EduEdge Program Offering",
		filters={"school_branch": branch, "academic_year": academic_year},
		fields=["program"],
		order_by="program asc",
		page_length=1000,
	)
	programs = sorted({row.program for row in offerings if row.program})
	group_filters: dict = {BRANCH_FIELD: branch, "academic_year": academic_year, "disabled": 0}
	if program:
		group_filters["program"] = program
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=["name", "student_group_name", "program"],
		order_by="student_group_name asc, name asc",
		page_length=2000,
	)
	return {
		"terms": terms,
		"programs": [{"value": name, "label": name} for name in programs],
		"class_arms": [{"value": row.name, "label": row.student_group_name or row.name, "program": row.program or ""} for row in groups],
	}


@frappe.whitelist()
def get_school_calendar_context(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	start: str | None = None,
	end: str | None = None,
	event_type: str | None = None,
	audience: str | None = None,
	include_teaching: int | str | None = 0,
) -> dict:
	_require_login()
	branches = _branch_options()
	selected_branch = _resolve_branch(branch, branches)
	if not selected_branch:
		return {"branches": [], "sessions": [], "terms": [], "items": [], "event_options": {"terms": [], "programs": [], "class_arms": []}}
	branch_row = next(row for row in branches if row["name"] == selected_branch)
	sessions = _session_options()
	selected_year = academic_year or _default_session(sessions)
	if selected_year and selected_year not in {row["name"] for row in sessions}:
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)
	terms = _terms(selected_year)
	if academic_term and academic_term not in {row["name"] for row in terms}:
		frappe.throw(_("Select a Term in the chosen Academic Session."), frappe.ValidationError)
	start_date, end_date = _range(selected_year, start, end)

	items: list[dict] = []
	items.extend(_academic_period_items(branch_row.get("institution"), selected_year, start_date, end_date))
	items.extend(_assessment_items(selected_branch, selected_year, academic_term, start_date, end_date))
	items.extend(_cbt_items(selected_branch, selected_year, academic_term, start_date, end_date))
	items.extend(_school_event_items(selected_branch, selected_year, academic_term, start_date, end_date, event_type, audience))
	if cint(include_teaching):
		items.extend(_teaching_items(selected_branch, selected_year, start_date, end_date))
	items.sort(key=lambda row: (str(row.get("starts_on") or ""), str(row.get("title") or "")))

	return {
		"branch": selected_branch,
		"branches": branches,
		"institution": branch_row.get("institution") or "",
		"institution_name": branch_row.get("institution_name") or branch_row.get("institution") or "",
		"academic_year": selected_year,
		"academic_term": academic_term or "",
		"sessions": sessions,
		"terms": terms,
		"range": {"start": str(start_date), "end": str(end_date)},
		"items": items,
		"event_options": _event_form_options(selected_branch, selected_year),
		"permissions": {
			"event_read": bool(frappe.has_permission(EVENT_DOCTYPE, "read")),
			"event_create": bool(frappe.has_permission(EVENT_DOCTYPE, "create")),
			"event_write": bool(frappe.has_permission(EVENT_DOCTYPE, "write")),
		},
	}


@frappe.whitelist()
def get_event_form_options(branch: str, academic_year: str, program: str | None = None) -> dict:
	_require_login()
	branches = _branch_options()
	_resolve_branch(branch, branches)
	return _event_form_options(branch, academic_year, program)


@frappe.whitelist()
def get_school_event(name: str) -> dict:
	_require_login()
	_require_read = frappe.has_permission(EVENT_DOCTYPE, "read")
	if not _require_read:
		frappe.throw(_("You are not permitted to view School Events."), frappe.PermissionError)
	doc = frappe.get_doc(EVENT_DOCTYPE, name)
	doc.check_permission("read")
	allowed = {row["name"] for row in _branch_options()}
	if doc.school_branch not in allowed:
		frappe.throw(_("This School Event is outside your Branch access."), frappe.PermissionError)
	return {"name": doc.name, "values": {field: doc.get(field) for field in (*EDITABLE_EVENT_FIELDS, "institution", "status", "cancellation_reason")}}


@frappe.whitelist(methods=["POST"])
def save_school_event(values: str | dict, name: str | None = None) -> dict:
	_require_login()
	payload = _parse_json(values)
	if name:
		doc = frappe.get_doc(EVENT_DOCTYPE, name)
		doc.check_permission("write")
		if doc.status in {"Completed", "Archived"}:
			frappe.throw(_("Completed or Archived School Events cannot be edited."), frappe.ValidationError)
	else:
		if not frappe.has_permission(EVENT_DOCTYPE, "create"):
			frappe.throw(_("You are not permitted to create School Events."), frappe.PermissionError)
		doc = frappe.new_doc(EVENT_DOCTYPE)
		doc.status = "Draft"
	for fieldname in EDITABLE_EVENT_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def set_school_event_status(name: str, status: str, reason: str | None = None) -> dict:
	_require_login()
	doc = frappe.get_doc(EVENT_DOCTYPE, name)
	doc.check_permission("write")
	requested = str(status or "").strip()
	if requested not in EVENT_STATUSES:
		frappe.throw(_("Select a valid School Event status."), frappe.ValidationError)
	current = doc.status or "Draft"
	if requested != current and requested not in STATUS_TRANSITIONS.get(current, set()):
		frappe.throw(_("School Event cannot move from {0} to {1}.").format(current, requested), frappe.ValidationError)
	if requested == "Cancelled":
		doc.cancellation_reason = str(reason or "").strip()
	elif requested in {"Draft", "Scheduled", "Published"}:
		doc.cancellation_reason = ""
	doc.status = requested
	doc.save()
	return {"name": doc.name, "status": doc.status, "cancellation_reason": doc.cancellation_reason or ""}
