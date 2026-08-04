from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.academic_calendar import assert_institution_calendar_context
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch
from eduedge.services.enrollment_lifecycle import get_capacity_consuming_enrollment_counts
from eduedge.services.institution_context import get_effective_institution_context

DEFAULT_PAGE_LENGTH = 25
MAX_PAGE_LENGTH = 50
MAX_OPTION_ROWS = 500
CALENDAR_DOCTYPE = "EduEdge Institution Academic Calendar"
PERIOD_DOCTYPE = "EduEdge Academic Calendar Period"


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_read() -> None:
	_require_login()
	if not frappe.has_permission("EduEdge Program Offering", "read"):
		frappe.throw(_("You are not permitted to view Programme Offerings."), frappe.PermissionError)


def _assert_link_read_permission(doctype: str, name: str | None, label: str) -> None:
	if not name:
		return
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} does not exist.").format(label), frappe.DoesNotExistError)
	frappe.get_doc(doctype, name).check_permission("read")


def _assert_institution_access(institution: str | None) -> None:
	if not institution:
		return
	_assert_link_read_permission("EduEdge Institution", institution, _("Institution"))
	if not cint(frappe.db.get_value("EduEdge Institution", institution, "enabled")):
		frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)


def _resolve_page_context(
	*,
	branch: str | None,
	institution: str | None,
	use_active_branch: int | str | bool = 0,
) -> tuple[str | None, str | None]:
	resolved_branch = str(branch or "").strip() or None
	resolved_institution = str(institution or "").strip() or None
	if not resolved_branch and not resolved_institution and cint(use_active_branch):
		current_branch = get_current_school_branch() or {}
		resolved_branch = str(current_branch.get("name") or "").strip() or None

	_assert_institution_access(resolved_institution)
	if resolved_branch:
		assert_branch_access(resolved_branch)
		branch_row = frappe.db.get_value(
			"EduEdge School Branch",
			resolved_branch,
			["institution", "enabled"],
			as_dict=True,
		) or {}
		if not cint(branch_row.get("enabled")):
			frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
		branch_institution = branch_row.get("institution")
		if resolved_institution and branch_institution != resolved_institution:
			frappe.throw(
				_("Selected Branch does not belong to the selected Institution."),
				frappe.ValidationError,
			)
		resolved_institution = branch_institution or resolved_institution
		_assert_institution_access(resolved_institution)
	return resolved_branch, resolved_institution


@frappe.whitelist()
def get_programme_offerings_page(
	branch: str | None = None,
	institution: str | None = None,
	program: str | None = None,
	department: str | None = None,
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
	use_active_branch: int | str | bool = 0,
	**_legacy_filters,
) -> dict:
	_require_read()
	branch, institution = _resolve_page_context(
		branch=branch,
		institution=institution,
		use_active_branch=use_active_branch,
	)
	active_context = get_effective_institution_context(institution=institution, branch=branch)

	start = max(cint(start), 0)
	page_length = min(max(cint(page_length) or DEFAULT_PAGE_LENGTH, 1), MAX_PAGE_LENGTH)
	filters: dict[str, Any] = {}
	for fieldname, value in {
		"school_branch": branch,
		"institution": institution,
		"program": program,
		"department": department,
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
			"department",
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
			"branch": branch or "",
			"institution": institution or "",
			"program": str(program or "").strip(),
			"department": str(department or "").strip(),
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
	occupied_counts = get_capacity_consuming_enrollment_counts(names)
	today = getdate(nowdate())
	for row in rows:
		occupied = occupied_counts.get(row.name, 0)
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
			status not in {"Disabled", "Closed", "Full"} and cint(row.enrollment_enabled)
		)
		row["admission_status"] = "Admission Open" if row["application_open"] else "Admission Closed"
		row["enrollment_status"] = "Enrollment Open" if row["enrollment_open"] else "Enrollment Closed"


def _identity_locked_offerings(names: list[str]) -> set[str]:
	if not names:
		return set()
	locked: set[str] = set()
	for doctype in ("Student Applicant", "Student Group"):
		if frappe.db.exists("DocType", doctype) and frappe.get_meta(doctype).has_field(OFFERING_FIELD):
			locked.update(frappe.get_all(doctype, filters={OFFERING_FIELD: ["in", names]}, pluck=OFFERING_FIELD))
	if frappe.db.exists("DocType", "Program Enrollment") and frappe.get_meta("Program Enrollment").has_field(OFFERING_FIELD):
		locked.update(
			frappe.get_all(
				"Program Enrollment",
				filters={OFFERING_FIELD: ["in", names], "docstatus": 1},
				pluck=OFFERING_FIELD,
			)
		)
	return locked


def _list_institutions() -> list[dict]:
	if not frappe.has_permission("EduEdge Institution", "read"):
		return []
	rows = frappe.get_list(
		"EduEdge Institution",
		filters={"enabled": 1},
		fields=["name", "institution_name", "institution_type", "company", "is_default"],
		order_by="is_default desc, institution_name asc",
		page_length=MAX_OPTION_ROWS,
	)
	for row in rows:
		context = get_effective_institution_context(institution=row.name)
		row["institution_type_name"] = context.get("institution_type_name") or row.get("institution_type")
	return rows


def _get_context_options(institution: str | None, academic_year: str | None) -> dict:
	branches = (
		get_allowed_school_branches(institution=institution)
		if institution
		else get_allowed_school_branches()
	)
	for branch in branches:
		if not branch.get("institution"):
			branch["institution"] = frappe.db.get_value(
				"EduEdge School Branch", branch.get("name"), "institution"
			)
		if not branch.get("institution_name") and branch.get("institution"):
			branch["institution_name"] = frappe.db.get_value(
				"EduEdge Institution", branch.get("institution"), "institution_name"
			)

	program_filters = {INSTITUTION_FIELD: institution} if institution else {}
	programmes = (
		frappe.get_list(
			"Program",
			filters=program_filters,
			fields=["name", "program_name", "program_abbreviation", "department", INSTITUTION_FIELD],
			order_by="department asc, program_name asc",
			page_length=MAX_OPTION_ROWS,
		)
		if frappe.has_permission("Program", "read")
		else []
	)
	department_filters = (
		{INSTITUTION_FIELD: institution}
		if institution and frappe.get_meta("Department").has_field(INSTITUTION_FIELD)
		else {}
	)
	departments = (
		frappe.get_list(
			"Department",
			filters=department_filters,
			fields=["name", "department_name", "parent_department", "is_group", "company", INSTITUTION_FIELD],
			order_by="lft asc, department_name asc",
			page_length=MAX_OPTION_ROWS,
		)
		if frappe.has_permission("Department", "read")
		else []
	)
	academic_years = _institution_academic_years(institution) if institution else []
	academic_terms = _institution_calendar_terms(institution, academic_year)
	calendar_context = _institution_calendar_context(institution, academic_year)

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
		"institutions": _list_institutions(),
		"branches": branches,
		"programmes": programmes,
		"departments": departments,
		"academic_years": academic_years,
		"academic_terms": academic_terms,
		"calendar_context": calendar_context,
		"student_batches": batches,
		"study_modes": ["Full-Time", "Part-Time", "Weekend", "Evening", "Short Course", "Flexible"],
		"delivery_modes": ["Onsite", "Online", "Hybrid"],
	}


def _institution_academic_years(institution: str) -> list[dict]:
	if not frappe.has_permission("Academic Year", "read") or not frappe.has_permission(CALENDAR_DOCTYPE, "read"):
		return []
	calendars = frappe.get_list(
		CALENDAR_DOCTYPE,
		filters={"institution": institution, "enabled": 1},
		fields=["name", "academic_year", "start_date", "end_date", "is_current"],
		order_by="is_current desc, start_date desc, academic_year desc",
		page_length=MAX_OPTION_ROWS,
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
	by_year = {row.name: row for row in years}
	calendar_by_year = {row.academic_year: row for row in calendars if row.academic_year}
	result = []
	for name in year_names:
		year = by_year.get(name)
		calendar = calendar_by_year.get(name)
		if not year or not calendar:
			continue
		result.append(
			{
				"name": year.name,
				"year_start_date": year.year_start_date,
				"year_end_date": year.year_end_date,
				"calendar": calendar.name,
				"calendar_start_date": calendar.start_date,
				"calendar_end_date": calendar.end_date,
				"is_current": cint(calendar.is_current),
			}
		)
	return result


def _institution_calendar_terms(institution: str | None, academic_year: str | None) -> list[dict]:
	if (
		not institution
		or not academic_year
		or not frappe.has_permission("Academic Term", "read")
		or not frappe.has_permission(CALENDAR_DOCTYPE, "read")
	):
		return []
	calendar_names = frappe.get_list(
		CALENDAR_DOCTYPE,
		filters={"institution": institution, "academic_year": academic_year, "enabled": 1},
		pluck="name",
		page_length=MAX_OPTION_ROWS,
	)
	if not calendar_names:
		return []
	periods = frappe.get_all(
		PERIOD_DOCTYPE,
		filters={"parent": ["in", calendar_names], "parenttype": CALENDAR_DOCTYPE},
		fields=["parent", "academic_term", "start_date", "end_date", "sequence"],
		order_by="sequence asc, start_date asc",
		limit_page_length=MAX_OPTION_ROWS,
	)
	term_names = list(dict.fromkeys(row.academic_term for row in periods if row.academic_term))
	if not term_names:
		return []
	terms = frappe.get_list(
		"Academic Term",
		filters={"name": ["in", term_names], "academic_year": academic_year},
		fields=["name", "academic_year", "term_start_date", "term_end_date"],
		page_length=MAX_OPTION_ROWS,
	)
	by_name = {row.name: row for row in terms}
	return [
		{
			"name": row.academic_term,
			"academic_year": academic_year,
			"term_start_date": (by_name.get(row.academic_term) or {}).get("term_start_date"),
			"term_end_date": (by_name.get(row.academic_term) or {}).get("term_end_date"),
			"calendar": row.parent,
			"calendar_start_date": row.start_date,
			"calendar_end_date": row.end_date,
			"sequence": cint(row.sequence),
		}
		for row in periods
		if row.academic_term in by_name
	]


def _institution_calendar_context(institution: str | None, academic_year: str | None) -> dict:
	if not institution or not academic_year or not frappe.has_permission(CALENDAR_DOCTYPE, "read"):
		return {}
	rows = frappe.get_list(
		CALENDAR_DOCTYPE,
		filters={"institution": institution, "academic_year": academic_year, "enabled": 1},
		fields=["name", "institution", "academic_year", "start_date", "end_date", "is_current"],
		order_by="is_current desc, start_date desc, modified desc",
		page_length=1,
	)
	return dict(rows[0]) if rows else {}


@frappe.whitelist()
def get_programme_offering_options(
	institution: str | None = None,
	branch: str | None = None,
	academic_year: str | None = None,
	use_active_branch: int | str | bool = 0,
) -> dict:
	_require_read()
	branch, institution = _resolve_page_context(
		branch=branch,
		institution=institution,
		use_active_branch=use_active_branch,
	)
	return {
		"branch": branch,
		"institution": institution,
		"active_context": get_effective_institution_context(institution=institution, branch=branch),
		"options": _get_context_options(institution, academic_year),
	}


@frappe.whitelist(methods=["POST"])
def save_programme_offering(
	school_branch: str,
	program: str,
	academic_year: str,
	offering: str | None = None,
	institution: str | None = None,
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
	_require_login()
	require_eduedge_access(feature_key="academics", action="save_programme_offering")
	resolved_branch, resolved_institution = _resolve_page_context(
		branch=school_branch,
		institution=institution,
	)
	if not resolved_branch or not resolved_institution:
		frappe.throw(_("Select an Institution and one of its permitted Branches."), frappe.ValidationError)
	_assert_link_read_permission("Program", program, _("Programme / Class"))
	_assert_link_read_permission("Academic Year", academic_year, _("Academic Session"))
	_assert_link_read_permission("Academic Term", academic_term, _("Term / Semester"))
	_assert_link_read_permission("Student Batch Name", student_batch, _("Student Batch / Cohort"))
	assert_institution_calendar_context(
		branch=resolved_branch,
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
			"school_branch": resolved_branch,
			"program": program,
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
		"institution": doc.institution,
		"school_branch": doc.school_branch,
	}
