from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import programme_offerings_display as display
from eduedge.api import programme_offerings_safe as base
from eduedge.education.academic_progression import (
	OFFERING_LEVEL_FIELD,
	PROGRAM_PROGRESSION_MODE_FIELD,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.academic_calendar import assert_institution_calendar_context
from eduedge.services.branch_context import get_current_school_branch
from eduedge.services.institution_context import get_effective_institution_context


@frappe.whitelist()
def get_programme_offerings_page(
	branch: str | None = None,
	institution: str | None = None,
	program: str | None = None,
	department: str | None = None,
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
	page_length: int | str = base.DEFAULT_PAGE_LENGTH,
	**_legacy_filters,
) -> dict:
	base._require_read()
	current_branch = get_current_school_branch() or {}
	branch = str(branch or current_branch.get("name") or "").strip() or None
	institution = str(institution or "").strip() or None
	if branch:
		assert_branch_access(branch)
		branch_institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
		if institution and branch_institution != institution:
			frappe.throw(_("Selected Branch does not belong to the selected Institution."), frappe.ValidationError)
		institution = branch_institution or institution
	active_context = get_effective_institution_context(institution=institution, branch=branch)

	start = max(cint(start), 0)
	page_length = min(max(cint(page_length) or base.DEFAULT_PAGE_LENGTH, 1), base.MAX_PAGE_LENGTH)
	filters: dict[str, Any] = {}
	for fieldname, value in {
		"school_branch": branch,
		"institution": institution,
		"program": program,
		"department": department,
		OFFERING_LEVEL_FIELD: academic_level,
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
			"department": ["like", like],
			OFFERING_LEVEL_FIELD: ["like", like],
		}
	rows = frappe.get_list(
		"EduEdge Program Offering",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "school_branch", "institution", "program", "department", OFFERING_LEVEL_FIELD,
			"academic_year", "academic_term", "student_batch", "offering_title",
			"offering_code", "study_mode", "delivery_mode", "start_date", "end_date",
			"is_active", "admission_enabled", "enrollment_enabled", "capacity",
			"application_start_date", "application_end_date", "notes", "modified",
		],
		order_by="is_active desc, start_date desc, modified desc",
		start=start,
		page_length=page_length + 1,
	)
	has_more = len(rows) > page_length
	rows = rows[:page_length]
	base._attach_runtime_status(rows)
	options = _get_context_options(institution, academic_year, program)
	payload = {
		"active_context": active_context,
		"filters": {
			"branch": branch,
			"institution": institution,
			"program": str(program or "").strip(),
			"department": str(department or "").strip(),
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
		"options": options,
		"summary": {
			"total_offerings": base._count_offerings(filters, or_filters),
			"visible_offerings": len(rows),
			"active": sum(1 for row in rows if row.get("operational_status") == "Active"),
			"upcoming": sum(1 for row in rows if row.get("operational_status") == "Upcoming"),
			"full": sum(1 for row in rows if row.get("operational_status") == "Full"),
			"closed_or_disabled": sum(1 for row in rows if row.get("operational_status") in {"Closed", "Disabled"}),
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
	display._annotate_payload(payload)
	_annotate_levels(payload)
	return payload


@frappe.whitelist()
def get_programme_offering_options(
	branch: str | None = None,
	academic_year: str | None = None,
	program: str | None = None,
) -> dict:
	base._require_read()
	current_branch = get_current_school_branch() or {}
	branch = str(branch or current_branch.get("name") or "").strip() or None
	institution = None
	if branch:
		assert_branch_access(branch)
		institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
	payload = {
		"branch": branch,
		"institution": institution,
		"active_context": get_effective_institution_context(institution=institution, branch=branch),
		"options": _get_context_options(institution, academic_year, program),
	}
	display._annotate_options(payload["options"])
	_annotate_levels(payload)
	return payload


def _get_context_options(institution: str | None, academic_year: str | None, program: str | None) -> dict:
	options = base._get_context_options(institution, academic_year)
	program_meta = frappe.get_meta("Program")
	if program_meta.has_field(PROGRAM_PROGRESSION_MODE_FIELD):
		values = {
			row.name: row
			for row in frappe.get_all(
				"Program",
				filters={"name": ["in", [item.get("name") for item in options.get("programmes") or []]]},
				fields=["name", PROGRAM_PROGRESSION_MODE_FIELD, "eduedge_next_program", "eduedge_terminal_program"],
				page_length=max(len(options.get("programmes") or []), 1),
			)
		} if options.get("programmes") else {}
		for row in options.get("programmes") or []:
			progression = values.get(row.get("name")) or {}
			row[PROGRAM_PROGRESSION_MODE_FIELD] = progression.get(PROGRAM_PROGRESSION_MODE_FIELD) or ""
			row["eduedge_next_program"] = progression.get("eduedge_next_program") or ""
			row["eduedge_terminal_program"] = cint(progression.get("eduedge_terminal_program"))
	options["academic_levels"] = _levels(institution, program)
	return options


def _levels(institution: str | None, program: str | None) -> list[dict]:
	if not institution or not program or not frappe.has_permission("EduEdge Academic Level", "read"):
		return []
	return frappe.get_list(
		"EduEdge Academic Level",
		filters={"institution": institution, "program": program, "enabled": 1},
		fields=["name", "level_name", "level_code", "program", "sequence", "next_level", "is_terminal"],
		order_by="sequence asc, level_name asc",
		page_length=base.MAX_OPTION_ROWS,
	)


def _annotate_levels(payload: dict) -> None:
	options = payload.get("options") or {}
	for row in options.get("academic_levels") or []:
		row["display_name"] = row.get("level_name") or row.get("name") or ""
	level_names = [row.get(OFFERING_LEVEL_FIELD) for row in payload.get("offerings") or [] if row.get(OFFERING_LEVEL_FIELD)]
	labels = {
		row.name: row.level_name
		for row in frappe.get_all(
			"EduEdge Academic Level",
			filters={"name": ["in", level_names]},
			fields=["name", "level_name"],
			page_length=max(len(level_names), 1),
		)
	} if level_names else {}
	for row in payload.get("offerings") or []:
		row["academic_level_display_name"] = labels.get(row.get(OFFERING_LEVEL_FIELD)) or row.get(OFFERING_LEVEL_FIELD) or ""


@frappe.whitelist(methods=["POST"])
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
	**_legacy_values,
) -> dict:
	base._require_login()
	require_eduedge_access(feature_key="academics", action="save_programme_offering")
	assert_branch_access(school_branch)
	base._assert_link_read_permission("Program", program, _("Programme / Class"))
	base._assert_link_read_permission("EduEdge Academic Level", academic_level, _("Academic Level"))
	base._assert_link_read_permission("Academic Year", academic_year, _("Academic Session"))
	base._assert_link_read_permission("Academic Term", academic_term, _("Term / Semester"))
	base._assert_link_read_permission("Student Batch Name", student_batch, _("Student Batch / Cohort"))
	assert_institution_calendar_context(
		branch=school_branch,
		academic_year=academic_year,
		academic_term=academic_term or None,
	)
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
			OFFERING_LEVEL_FIELD: academic_level or None,
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
	return {"name": doc.name, "offering_title": doc.offering_title, "offering_code": doc.offering_code}
