from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api import scheme_of_work as scheme_api
from eduedge.api import scheme_of_work_workbench as base
from eduedge.services.academic_calendar import (
	CALENDAR_DOCTYPE,
	PERIOD_DOCTYPE,
	get_enabled_institution_calendar,
)


def _offering_row(offering: str) -> frappe._dict | None:
	if not offering:
		return None
	return frappe.db.get_value(
		"EduEdge Program Offering",
		offering,
		[
			"name",
			"institution",
			"school_branch",
			"academic_year",
			"academic_term",
			"start_date",
			"end_date",
		],
		as_dict=True,
	)


def _term_options(offering: frappe._dict | None) -> list[dict]:
	if not offering:
		return []
	if offering.academic_term:
		# Historical term-bound Offering: preserve the exact period and do not offer
		# other Terms against that legacy identity.
		return [
			{
				"value": offering.academic_term,
				"label": offering.academic_term,
				"start_date": offering.start_date,
				"end_date": offering.end_date,
				"legacy_offering": True,
			}
		]
	calendar = get_enabled_institution_calendar(
		offering.institution,
		academic_year=offering.academic_year,
	)
	if not calendar:
		return []
	rows = frappe.get_all(
		PERIOD_DOCTYPE,
		filters={"parent": calendar.name, "parenttype": CALENDAR_DOCTYPE},
		fields=["academic_term", "start_date", "end_date", "sequence", "result_publication_date"],
		order_by="sequence asc, start_date asc",
		limit_page_length=100,
	)
	return [
		{
			"value": row.academic_term,
			"label": row.academic_term,
			"start_date": row.start_date,
			"end_date": row.end_date,
			"sequence": cint(row.sequence),
			"result_publication_date": row.result_publication_date,
			"calendar": calendar.name,
			"legacy_offering": False,
		}
		for row in rows
		if row.academic_term
	]


def _term_scoped_schemes(
	*,
	school_branch: str,
	program_offering: str,
	student_group: str,
	course: str,
	academic_term: str,
	status: str,
	start: int,
	page_length: int,
) -> dict:
	filters: dict = {"school_branch": school_branch}
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
	rows = frappe.get_all(
		scheme_api.SCHEME_DOCTYPE,
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
		start=max(cint(start), 0),
		page_length=limit + 1,
	)
	visible: list[dict] = []
	for row in rows:
		doc = frappe.get_doc(scheme_api.SCHEME_DOCTYPE, row.name)
		try:
			scheme_api._context_authorized(doc, write=False)
		except frappe.PermissionError:
			continue
		visible.append(dict(row))
	return {"rows": visible[:limit], "has_more": len(visible) > limit}


@frappe.whitelist()
def get_scheme_workbench(
	school_branch: str | None = None,
	program_offering: str | None = None,
	student_group: str | None = None,
	course: str | None = None,
	academic_term: str | None = None,
	status: str | None = None,
	start: int = 0,
	page_length: int = 25,
) -> dict:
	"""Return term-aware Scheme planning context below a sessional Offering/Class Arm."""
	payload = base.get_scheme_workbench(
		school_branch=school_branch,
		program_offering=program_offering,
		student_group=student_group,
		course=course,
		status=status,
		start=0,
		page_length=1,
	)
	resolved_offering = str(payload.get("filters", {}).get("program_offering") or "").strip()
	offering = _offering_row(resolved_offering)
	terms = _term_options(offering)
	term_names = {row["value"] for row in terms}
	requested_term = str(academic_term or "").strip()
	if offering and offering.academic_term:
		if requested_term and requested_term != offering.academic_term:
			frappe.throw(_("Historical term-bound Offering can only use its recorded Academic Term."), frappe.ValidationError)
		requested_term = offering.academic_term
	elif requested_term and requested_term not in term_names:
		frappe.throw(
			_("Select an Academic Term / Semester configured in the Institution Academic Calendar for this Session."),
			frappe.ValidationError,
		)

	branch = str(payload.get("filters", {}).get("school_branch") or "").strip()
	group = str(payload.get("filters", {}).get("student_group") or "").strip()
	subject = str(payload.get("filters", {}).get("course") or "").strip()
	schemes = _term_scoped_schemes(
		school_branch=branch,
		program_offering=resolved_offering,
		student_group=group,
		course=subject,
		academic_term=requested_term,
		status=str(status or "").strip(),
		start=cint(start),
		page_length=cint(page_length) or 25,
	)
	payload["terms"] = terms
	payload["schemes"] = schemes["rows"]
	payload["paging"] = {
		"start": max(cint(start), 0),
		"page_length": min(max(cint(page_length) or 25, 1), 50),
		"has_more": bool(schemes["has_more"]),
	}
	payload.setdefault("filters", {})["academic_term"] = requested_term
	payload.setdefault("permissions", {})["can_create_in_context"] = bool(
		payload.get("permissions", {}).get("can_create_in_context")
		and requested_term
	)
	payload["selected_term"] = next((row for row in terms if row["value"] == requested_term), None)
	return payload
