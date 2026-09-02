from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import scheme_of_work as scheme_api
from eduedge.api import scheme_of_work_workbench_sessional as sessional

SCHEME_DOCTYPE = "EduEdge Scheme of Work"
MAX_SCAN_ROWS = 1000


def _normalise(value) -> str:
	return " ".join(str(value or "").split())


def _year_scoped_schemes(
	*,
	school_branch: str,
	academic_year: str,
	program_offering: str,
	student_group: str,
	course: str,
	academic_term: str,
	status: str,
	start: int,
	page_length: int,
) -> dict:
	filters: dict = {
		"school_branch": school_branch,
		"academic_year": academic_year,
	}
	for fieldname, value in {
		"program_offering": program_offering,
		"student_group": student_group,
		"course": course,
		"academic_term": academic_term,
		"status": status,
	}.items():
		if value:
			filters[fieldname] = value

	limit = min(max(cint(page_length) or 25, 1), 50)
	visible_start = max(cint(start), 0)
	wanted = visible_start + limit + 1
	visible: list[dict] = []
	raw_start = 0
	chunk = 100

	while len(visible) < wanted and raw_start < MAX_SCAN_ROWS:
		rows = frappe.get_all(
			SCHEME_DOCTYPE,
			filters=filters,
			fields=[
				"name",
				"scheme_title",
				"status",
				"version_no",
				"school_branch",
				"program_offering",
				"student_group",
				"course",
				"academic_year",
				"academic_term",
				"period_start_date",
				"period_end_date",
			],
			order_by="academic_year desc, academic_term desc, course asc, version_no desc",
			start=raw_start,
			page_length=chunk,
		)
		if not rows:
			break
		for row in rows:
			doc = frappe.get_doc(SCHEME_DOCTYPE, row.name)
			try:
				scheme_api._context_authorized(doc, write=False)
			except frappe.PermissionError:
				continue
			visible.append(dict(row))
			if len(visible) >= wanted:
				break
		raw_start += len(rows)
		if len(rows) < chunk:
			break

	page = visible[visible_start : visible_start + limit]
	return {
		"rows": page,
		"has_more": len(visible) > visible_start + limit,
		"scan_truncated": raw_start >= MAX_SCAN_ROWS and len(visible) < wanted,
	}


@frappe.whitelist()
def get_scheme_workbench(
	school_branch: str | None = None,
	academic_year: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	academic_term: str | None = None,
	status: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	"""Add an authoritative Academic Session constraint to the Scheme workbench.

	Normal Scheme management remains unchanged when no Academic Session preset is
	provided. Session Launch supplies academic_year so history cannot drift into
	another Session merely because the Branch contains older Scheme records.
	"""
	year = _normalise(academic_year)
	payload = sessional.get_scheme_workbench(
		school_branch=school_branch,
		program_offering=program_offering,
		student_group=student_group,
		course=course,
		academic_term=academic_term,
		status=status,
		start=0 if year else start,
		page_length=1 if year else page_length,
	)
	if not year:
		return payload
	if not frappe.db.exists("Academic Year", year):
		frappe.throw(_("Select a valid Academic Session."), frappe.ValidationError)

	branch = _normalise(payload.get("filters", {}).get("school_branch"))
	offering = _normalise(payload.get("filters", {}).get("program_offering"))
	group = _normalise(payload.get("filters", {}).get("student_group"))
	subject = _normalise(payload.get("filters", {}).get("course"))
	term = _normalise(payload.get("filters", {}).get("academic_term"))
	resolved_status = _normalise(status)

	all_offerings = [dict(row) for row in payload.get("offerings") or []]
	if offering:
		offering_year = frappe.db.get_value("EduEdge Program Offering", offering, "academic_year")
		if offering_year != year:
			frappe.throw(
				_("The selected Class / Programme Offering does not belong to Academic Session {0}.").format(year),
				frappe.ValidationError,
			)
	payload["offerings"] = [row for row in all_offerings if _normalise(row.get("academic_year")) == year]
	payload["academic_years"] = [{"value": year, "label": year, "locked": True}]

	schemes = _year_scoped_schemes(
		school_branch=branch,
		academic_year=year,
		program_offering=offering,
		student_group=group,
		course=subject,
		academic_term=term,
		status=resolved_status,
		start=cint(start),
		page_length=cint(page_length) or 25,
	)
	payload["schemes"] = schemes["rows"]
	payload["paging"] = {
		"start": max(cint(start), 0),
		"page_length": min(max(cint(page_length) or 25, 1), 50),
		"has_more": bool(schemes["has_more"]),
	}
	payload.setdefault("filters", {})["academic_year"] = year
	payload["session_context"] = {
		"academic_year": year,
		"locked": True,
		"source": "Academic Session Launch",
		"scan_truncated": bool(schemes["scan_truncated"]),
	}
	return payload
