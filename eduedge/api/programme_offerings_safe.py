from __future__ import annotations

import frappe

from eduedge.api import programme_offerings as base
from eduedge.services.academic_calendar import assert_institution_calendar_context


@frappe.whitelist()
def get_programme_offerings_page(**kwargs) -> dict:
	payload = base.get_programme_offerings_page(**kwargs)
	institution = (payload.get("filters") or {}).get("institution") or (payload.get("active_context") or {}).get("institution")
	if institution:
		payload.setdefault("options", {})["academic_years"] = _institution_academic_years(institution)
	return payload


@frappe.whitelist()
def get_programme_offering_options(
	branch: str | None = None,
	academic_year: str | None = None,
) -> dict:
	payload = base.get_programme_offering_options(branch=branch, academic_year=academic_year)
	institution = payload.get("institution")
	if institution:
		payload.setdefault("options", {})["academic_years"] = _institution_academic_years(institution)
	return payload


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
) -> dict:
	assert_institution_calendar_context(
		branch=school_branch,
		academic_year=academic_year,
		academic_term=academic_term or None,
	)
	return base.save_programme_offering(
		school_branch=school_branch,
		program=program,
		academic_year=academic_year,
		offering=offering,
		academic_level=academic_level,
		academic_term=academic_term,
		student_batch=student_batch,
		offering_title=offering_title,
		offering_code=offering_code,
		study_mode=study_mode,
		delivery_mode=delivery_mode,
		start_date=start_date,
		end_date=end_date,
		is_active=is_active,
		admission_enabled=admission_enabled,
		enrollment_enabled=enrollment_enabled,
		capacity=capacity,
		application_start_date=application_start_date,
		application_end_date=application_end_date,
		notes=notes,
	)


def _institution_academic_years(institution: str) -> list[dict]:
	if not frappe.has_permission("Academic Year", "read") or not frappe.has_permission(
		"EduEdge Institution Academic Calendar", "read"
	):
		return []
	calendars = frappe.get_list(
		"EduEdge Institution Academic Calendar",
		filters={"institution": institution, "enabled": 1},
		fields=["academic_year", "start_date", "end_date", "is_current"],
		order_by="is_current desc, start_date desc, academic_year desc",
		page_length=500,
	)
	year_names = list(dict.fromkeys(row.academic_year for row in calendars if row.academic_year))
	if not year_names:
		return []
	years = frappe.get_list(
		"Academic Year",
		filters={"name": ["in", year_names]},
		fields=["name", "year_start_date", "year_end_date"],
		page_length=len(year_names),
	)
	by_name = {row.name: row for row in years}
	return [by_name[name] for name in year_names if name in by_name]
