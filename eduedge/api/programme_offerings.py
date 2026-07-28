from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch
from eduedge.services.enrollment_lifecycle import count_capacity_consuming_enrollments
from eduedge.services.institution_context import get_effective_institution_context


DEFAULT_PAGE_LENGTH = 25
MAX_PAGE_LENGTH = 50
MAX_OPTION_ROWS = 500


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_offering_read() -> None:
	_require_login()
	if not frappe.has_permission("EduEdge Program Offering", "read"):
		frappe.throw(_("You are not permitted to view Programme Offerings."), frappe.PermissionError)


@frappe.whitelist()
def get_programme_offerings_page(
	branch: str | None = None,
	institution: str | None = None,
	program: str | None = None,
	academic_section: str | None = None,
	academic_level: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_batch: str | None = None,
	study_mode: str | None = None,
	delivery_mode: str | None = None,
	is_active: str | int | None = None,
	admission_enabled: str | int | None = None,
	enrollment_enabled: str | int | None = None,
	search: str | None = None,
	start: int | str = 0,
	page_length: int | str = DEFAULT_PAGE_LENGTH,
) -> dict:
	_require_offering_read()
	active_context = get_effective_institution_context()
	current_branch = get_current_school_branch() or {}
	branch = str(branch or current_branch.get("name") or "").strip() or None
	institution = str(institution or "").strip() or None
	if branch:
		assert_branch_access(branch)
		branch_institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
		if institution and branch_institution != institution:
			frappe.throw(_("Selected Branch does not belong to the selected Institution."), frappe.ValidationError)
		institution = branch_institution or institution

	start = max(cint(start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
	filters: dict[str, Any] = {}
	for fieldname, value in {
		"school_branch": branch,
		"institution": institution,
		"program": program,
		"academic_section": academic_section,
		"academic_level": academic_level,
		"academic_year": academic_year,
		"academic_term": academic_term,
		"student_batch": student_batch,
		"study_mode": study_mode,
		"delivery_mode": delivery_mode,
	}.items():
		value = str(value or "").strip()
		if value:
			filters[fieldname] = value
	for fieldname, value in {
		"is_active": is_active,
		"admission_enabled": admission_enabled,
		"enrollment_enabled": enrollment_enabled,
	}.items():
		if str(value or "").strip() in {"0", "1"}:
			filters[fieldname] = cint(value)

	search = str(search or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = {
			"name": ["like", like],
			"offering_title": ["like", like],
			"offering_code": ["like", like],
			"program": ["like", like],
		}

	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"school_branch",
			"institution",
			"program",
			"academic_section",
			"academic_level",
			"academic_year",
			"academic_term",
			"student_batch",
			"offering_title",
			"offering_code",
			"study_mode",
			"delivery_mode",
			"start_date",
			"end_date",
			"is_active",
			"admission_enabled",
			"enrollment_enabled",
			"capacity",
			"application_start_date",
			"application_end_date",
			"notes",
			"modified",
		],
		order_by="is_active desc, start_date desc, modified desc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	_attach_runtime_status(rows)

	return {
		"active_context": active_context,
		"filters": {
			"branch": branch,
			"institution": institution,
			"program": str(program or "").strip(),
			"academic_section": str(academic_section or "").strip(),
			"academic_level": str(academic_level or "").strip(),
			"academic_year": str(academic_year or "").strip(),
			"academic_term": str(academic_term or "").strip(),
			"student_batch": str(student_batch or "").strip(),
			"study_mode": str(study_mode or "").strip(),
			"delivery_mode": str(delivery_mode or "").strip(),
			"is_active": "" if is_active is None else str(is_active),
			"admission_enabled": "" if admission_enabled is None else str(admission_enabled),
			"enrollment_enabled": "" if enrollment_enabled is None else str(enrollment_enabled),
			"search": search,
		},
		"offerings": rows,
		"options": _get_context_options(institution, academic_year),
		"summary": {
			"total_offerings": _count_offerings(filters, or_filters),
			"visible_offerings": len(rows),
			"active": sum(1 for row in rows if row.get("operational_status") == "Active"),
			"upcoming": sum(1 for row in rows if row.get("operational_status") == "Upcoming"),
			"full": sum(1 for row in rows if row.get("operational_status") == "Full"),
			"closed_or_disabled": sum(
				1 for row in rows if row.get("operational_status") in {"Closed", "Disabled"}
			),
			"occupied_seats": sum(cint(row.get("occupied_seats")) for row in rows),
			"configured_capacity": sum(cint(row.get("capacity")) for row in rows),
		},
		"paging": {
			"start": start,
			"page_length": page_length,
			"has_more": has_more,
			"next_start": start + len(rows),
		},
		"permissions": {
			"can_create": bool(frappe.has_permission("EduEdge Program Offering", "create")),
			"can_write": bool(frappe.has_permission("EduEdge Program Offering", "write")),
		},
	}


def _count_offerings(filters: dict, or_filters: dict | None) -> int:
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		or_filters=or_filters,
		fields=[{"COUNT": "name", "as": "record_count"}],
		page_length=1,
	)
	return cint(rows[0].record_count) if rows else 0


def _attach_runtime_status(rows: list[dict]) -> None:
	names = [row.name for row in rows]
	locked = _identity_locked_offerings(names)
	today = getdate(nowdate())
	for row in rows:
		occupied = count_capacity_consuming_enrollments(row.name)
		capacity = cint(row.capacity)
		row["occupied_seats"] = occupied
		row["seats_remaining"] = max(capacity - occupied, 0) if capacity else None
		row["identity_locked"] = row.name in locked
		if not cint(row.is_active):
			status = "Disabled"
		elif row.end_date and getdate(row.end_date) < today:
			status = "Closed"
		elif row.start_date and getdate(row.start_date) > today:
			status = "Upcoming"
		elif capacity and occupied >= capacity:
			status = "Full"
		else:
			status = "Active"
		row["operational_status"] = status
		row["application_open"] = bool(
			status not in {"Disabled", "Closed"}
			and cint(row.admission_enabled)
			and (not row.application_start_date or getdate(row.application_start_date) <= today)
			and (not row.application_end_date or getdate(row.application_end_date) >= today)
		)
		row["enrollment_open"] = bool(
			status not in {"Disabled", "Closed", "Full"}
			and cint(row.enrollment_enabled)
		)
		row["admission_status"] = "Admission Open" if row["application_open"] else "Admission Closed"
		row["enrollment_status"] = "Enrollment Open" if row["enrollment_open"] else "Enrollment Closed"


def _identity_locked_offerings(names: list[str]) -> set[str]:
	if not names:
		return set()
	locked: set[str] = set()
	for doctype in ("Student Applicant", "Student Group"):
		if frappe.db.exists("DocType", doctype) and frappe.get_meta(doctype).has_field(OFFERING_FIELD):
			locked.update(
				frappe.get_all(
					doctype,
					filters={OFFERING_FIELD: ["in", names]},
					pluck=OFFERING_FIELD,
				)
			)
	if frappe.db.exists("DocType", "Program Enrollment") and frappe.get_meta(
		"Program Enrollment"
	).has_field(OFFERING_FIELD):
		locked.update(
			frappe.get_all(
				"Program Enrollment",
				filters={OFFERING_FIELD: ["in", names], "docstatus": 1},
				pluck=OFFERING_FIELD,
			)
		)
	return locked


def _get_context_options(institution: str | None, academic_year: str | None) -> dict:
	branches = get_allowed_school_branches()
	for branch in branches:
		if not branch.get("institution"):
			branch["institution"] = frappe.db.get_value(
				"EduEdge School Branch", branch.get("name"), "institution"
			)
		if not branch.get("institution_name") and branch.get("institution"):
			branch["institution_name"] = frappe.db.get_value(
				"EduEdge Institution", branch.get("institution"), "institution_name"
			)
	program_filters = {}
	if institution:
		program_filters[INSTITUTION_FIELD] = institution
	programmes = (
		frappe.get_list(
			"Program",
			filters=program_filters,
			fields=["name", "program_name", "program_abbreviation", INSTITUTION_FIELD, "eduedge_academic_section"],
			order_by="program_name asc",
			page_length=MAX_OPTION_ROWS,
		)
		if frappe.has_permission("Program", "read")
		else []
	)
	sections = _list_institution_master(
		"EduEdge Academic Section",
		institution,
		["name", "section_name", "section_code", "institution", "sequence"],
		"sequence asc, section_name asc",
	)
	levels = _list_institution_master(
		"EduEdge Academic Level",
		institution,
		["name", "level_name", "level_code", "institution", "academic_section", "sequence"],
		"sequence asc, level_name asc",
	)
	years = (
		frappe.get_list(
			"Academic Year",
			fields=["name", "year_start_date", "year_end_date"],
			order_by="year_start_date desc, name desc",
			page_length=MAX_OPTION_ROWS,
		)
		if frappe.has_permission("Academic Year", "read")
		else []
	)
	terms = _list_institution_calendar_terms(institution, academic_year)
	batch_filters = {}
	batch_meta = frappe.get_meta("Student Batch Name")
	if institution and batch_meta.has_field(INSTITUTION_FIELD):
		batch_filters[INSTITUTION_FIELD] = institution
	batches = (
		frappe.get_list(
			"Student Batch Name",
			filters=batch_filters,
			fields=["name"] + ([INSTITUTION_FIELD] if batch_meta.has_field(INSTITUTION_FIELD) else []),
			order_by="name asc",
			page_length=MAX_OPTION_ROWS,
		)
		if frappe.has_permission("Student Batch Name", "read")
		else []
	)
	return {
		"branches": branches,
		"programmes": programmes,
		"sections": sections,
		"levels": levels,
		"academic_years": years,
		"academic_terms": terms,
		"student_batches": batches,
		"study_modes": ["Full-Time", "Part-Time", "Weekend", "Evening", "Short Course", "Flexible"],
		"delivery_modes": ["Onsite", "Online", "Hybrid"],
	}


def _list_institution_calendar_terms(
	institution: str | None,
	academic_year: str | None,
) -> list[dict]:
	if (
		not institution
		or not academic_year
		or not frappe.has_permission("Academic Term", "read")
		or not frappe.db.exists("DocType", "EduEdge Institution Academic Calendar")
	):
		return []
	if not frappe.has_permission("EduEdge Institution Academic Calendar", "read"):
		return []
	calendar_names = frappe.get_list(
		"EduEdge Institution Academic Calendar",
		filters={
			"institution": institution,
			"academic_year": academic_year,
			"enabled": 1,
		},
		pluck="name",
		page_length=MAX_OPTION_ROWS,
	)
	if not calendar_names:
		return []
	period_terms = frappe.get_all(
		"EduEdge Academic Calendar Period",
		filters={
			"parent": ["in", calendar_names],
			"parenttype": "EduEdge Institution Academic Calendar",
		},
		pluck="academic_term",
		limit_page_length=MAX_OPTION_ROWS,
	)
	term_names = list(dict.fromkeys(term for term in period_terms if term))
	if not term_names:
		return []
	return frappe.get_list(
		"Academic Term",
		filters={"name": ["in", term_names], "academic_year": academic_year},
		fields=["name", "academic_year", "term_start_date", "term_end_date"],
		order_by="term_start_date asc, name asc",
		page_length=MAX_OPTION_ROWS,
	)


def _list_institution_master(
	doctype: str,
	institution: str | None,
	fields: list[str],
	order_by: str,
) -> list[dict]:
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		return []
	filters: dict = {"enabled": 1}
	if institution:
		filters["institution"] = institution
	return frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		page_length=MAX_OPTION_ROWS,
	)


@frappe.whitelist()
def get_programme_offering_options(
	branch: str | None = None,
	academic_year: str | None = None,
) -> dict:
	_require_offering_read()
	current_branch = get_current_school_branch() or {}
	branch = str(branch or current_branch.get("name") or "").strip() or None
	institution = None
	if branch:
		assert_branch_access(branch)
		institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	return {
		"branch": branch,
		"institution": institution,
		"options": _get_context_options(institution, academic_year),
	}


@frappe.whitelist()
def save_programme_offering(
	school_branch: str,
	program: str,
	academic_year: str,
	offering: str | None = None,
	academic_level: str | None = None,
	academic_term: str | None = None,
	student_batch: str | None = None,
	offering_title: str | None = None,
	offering_code: str | None = None,
	study_mode: str | None = "Full-Time",
	delivery_mode: str | None = "Onsite",
	start_date: str | None = None,
	end_date: str | None = None,
	is_active: int | str = 1,
	admission_enabled: int | str = 1,
	enrollment_enabled: int | str = 1,
	capacity: int | str = 0,
	application_start_date: str | None = None,
	application_end_date: str | None = None,
	notes: str | None = None,
) -> dict:
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_programme_offering")
	assert_branch_access(school_branch)
	if offering:
		doc = frappe.get_doc("EduEdge Program Offering", offering)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Program Offering", "create"):
			frappe.throw(_("You are not permitted to create Programme Offerings."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Program Offering")
	doc.update(
		{
			"school_branch": school_branch,
			"program": program,
			"academic_level": academic_level or None,
			"academic_year": academic_year,
			"academic_term": academic_term or None,
			"student_batch": student_batch or None,
			"offering_title": str(offering_title or "").strip(),
			"offering_code": str(offering_code or "").strip(),
			"study_mode": study_mode or "Full-Time",
			"delivery_mode": delivery_mode or "Onsite",
			"start_date": start_date or None,
			"end_date": end_date or None,
			"is_active": cint(is_active),
			"admission_enabled": cint(admission_enabled),
			"enrollment_enabled": cint(enrollment_enabled),
			"capacity": max(cint(capacity), 0),
			"application_start_date": application_start_date or None,
			"application_end_date": application_end_date or None,
			"notes": notes or "",
		}
	)
	doc.save()
	return {
		"name": doc.name,
		"offering_title": doc.offering_title,
		"offering_code": doc.offering_code,
	}
