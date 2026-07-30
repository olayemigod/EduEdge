from __future__ import annotations

from typing import Literal

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import ACADEMIC_LEVEL_FIELD
from eduedge.education.academic_progression import OFFERING_LEVEL_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

Purpose = Literal["admission", "enrollment"]
PURPOSE_FIELD = {
	"admission": "admission_enabled",
	"enrollment": "enrollment_enabled",
}


def validate_program_offering(
	*,
	branch: str | None,
	program: str | None,
	academic_year: str | None,
	academic_term: str | None = None,
	academic_level: str | None = None,
	purpose: Purpose,
	reference_date: str | None = None,
) -> dict:
	if not branch or not program or not academic_year:
		frappe.throw(
			_("School Branch, Program, and Academic Year are required."),
			frappe.ValidationError,
		)

	_validate_term_year(academic_year, academic_term)
	rows = get_matching_offerings(
		branch=branch,
		program=program,
		academic_year=academic_year,
		academic_term=academic_term,
		academic_level=academic_level,
		purpose=purpose,
	)
	if not rows:
		frappe.throw(
			_("Program {0} is not enabled for {1} at School Branch / Campus {2} for Academic Year {3}.").format(
				program, purpose, branch, academic_year
			),
			frappe.ValidationError,
		)

	if purpose == "admission" and reference_date:
		date = getdate(reference_date)
		open_rows = [
			row
			for row in rows
			if (not row.application_start_date or getdate(row.application_start_date) <= date)
			and (not row.application_end_date or getdate(row.application_end_date) >= date)
		]
		if not open_rows:
			frappe.throw(
				_("Applications for Program {0} are not open on {1}.").format(program, date),
				frappe.ValidationError,
			)
		rows = open_rows

	if len(rows) > 1 and not academic_level:
		frappe.throw(
			_("More than one Programme Offering matches this Program and period. Select the exact Offering or Academic Level."),
			frappe.ValidationError,
		)
	return rows[0]


def get_matching_offerings(
	*,
	branch: str,
	program: str,
	academic_year: str,
	academic_term: str | None,
	academic_level: str | None,
	purpose: Purpose,
) -> list[dict]:
	purpose_field = PURPOSE_FIELD[purpose]
	filters = {
		"school_branch": branch,
		"program": program,
		"academic_year": academic_year,
		"is_active": 1,
		purpose_field: 1,
	}
	if academic_level:
		filters[OFFERING_LEVEL_FIELD] = academic_level
	rows = frappe.get_all(
		"EduEdge Program Offering",
		filters=filters,
		fields=[
			"name",
			"school_branch",
			"program",
			OFFERING_LEVEL_FIELD,
			"academic_year",
			"academic_term",
			"application_start_date",
			"application_end_date",
			"capacity",
		],
		order_by="academic_level asc, academic_term asc, modified desc",
	)
	if academic_term:
		return [
			row
			for row in rows
			if not row.get("academic_term") or row.get("academic_term") == academic_term
		]
	return rows


def validate_student_admission(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if not branch or not doc.academic_year:
		return
	_validate_term_year(doc.academic_year, None)
	_validate_admission_dates(doc)
	seen: set[str] = set()
	for row in doc.get("program_details") or []:
		if not row.program:
			continue
		if row.program in seen:
			frappe.throw(
				_("Program {0} is listed more than once in this admission.").format(row.program),
				frappe.ValidationError,
			)
		seen.add(row.program)
		matching = get_matching_offerings(
			branch=branch,
			program=row.program,
			academic_year=doc.academic_year,
			academic_term=None,
			academic_level=None,
			purpose="admission",
		)
		if not matching:
			frappe.throw(
				_("Program {0} has no active admission Offering for this Branch and Academic Year.").format(row.program),
				frappe.ValidationError,
			)


def validate_student_applicant(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if doc.academic_year and doc.academic_term:
		_validate_term_year(doc.academic_year, doc.academic_term)
	if not branch or not doc.program or not doc.academic_year:
		return

	if doc.student_admission:
		admission = frappe.db.get_value(
			"Student Admission",
			doc.student_admission,
			["name", BRANCH_FIELD, "academic_year", "enable_admission_application"],
			as_dict=True,
		)
		if not admission:
			frappe.throw(_("Selected Student Admission does not exist."), frappe.ValidationError)
		if admission.get(BRANCH_FIELD) != branch:
			frappe.throw(
				_("Student Applicant Branch must match the selected Student Admission Branch."),
				frappe.ValidationError,
			)
		if admission.academic_year != doc.academic_year:
			frappe.throw(
				_("Student Applicant Academic Year must match the selected Student Admission."),
				frappe.ValidationError,
			)
		if not admission.enable_admission_application:
			frappe.throw(
				_("The selected Student Admission is not accepting applications."),
				frappe.ValidationError,
			)
		if not frappe.db.exists(
			"Student Admission Program",
			{
				"parent": doc.student_admission,
				"parenttype": "Student Admission",
				"program": doc.program,
			},
		):
			frappe.throw(
				_("Program {0} is not listed in Student Admission {1}.").format(
					doc.program, doc.student_admission
				),
				frappe.ValidationError,
			)

	validate_program_offering(
		branch=branch,
		program=doc.program,
		academic_year=doc.academic_year,
		academic_term=doc.academic_term,
		academic_level=doc.get(ACADEMIC_LEVEL_FIELD) if doc.meta.has_field(ACADEMIC_LEVEL_FIELD) else None,
		purpose="admission",
		reference_date=doc.application_date or nowdate(),
	)


def validate_program_enrollment(doc) -> None:
	branch = doc.get(BRANCH_FIELD)
	if doc.academic_year and doc.academic_term:
		_validate_term_year(doc.academic_year, doc.academic_term)
	if not branch or not doc.program or not doc.academic_year:
		return
	validate_program_offering(
		branch=branch,
		program=doc.program,
		academic_year=doc.academic_year,
		academic_term=doc.academic_term,
		academic_level=doc.get(ACADEMIC_LEVEL_FIELD) if doc.meta.has_field(ACADEMIC_LEVEL_FIELD) else None,
		purpose="enrollment",
	)


def get_context_branch() -> str | None:
	if frappe.session.user != "Guest":
		current = get_current_school_branch()
		if current:
			return current.get("name")
	settings_branch = frappe.db.get_single_value("EduEdge Settings", "default_school_branch")
	if settings_branch and frappe.db.get_value("EduEdge School Branch", settings_branch, "enabled"):
		return settings_branch
	branches = frappe.get_all(
		"EduEdge School Branch",
		filters={"enabled": 1},
		pluck="name",
		limit=2,
	)
	return branches[0] if len(branches) == 1 else None


def assert_branch_access(branch: str) -> None:
	if not frappe.db.get_value("EduEdge School Branch", branch, "enabled"):
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
	if frappe.session.user in {"Guest", "Administrator"}:
		return
	roles = set(frappe.get_roles(frappe.session.user))
	if "System Manager" in roles:
		return
	allowed = {row["name"] for row in get_allowed_school_branches()}
	if branch not in allowed:
		frappe.throw(
			_("You do not have access to School Branch / Campus {0}.").format(branch),
			frappe.PermissionError,
		)


def _validate_term_year(academic_year: str, academic_term: str | None) -> None:
	if not academic_term:
		return
	actual_year = frappe.db.get_value("Academic Term", academic_term, "academic_year")
	if actual_year != academic_year:
		frappe.throw(
			_("Academic Term {0} does not belong to Academic Year {1}.").format(
				academic_term, academic_year
			),
			frappe.ValidationError,
		)


def _validate_admission_dates(doc) -> None:
	if doc.admission_start_date and doc.admission_end_date:
		if getdate(doc.admission_end_date) <= getdate(doc.admission_start_date):
			frappe.throw(
				_("Admission End Date must be later than Admission Start Date."),
				frappe.ValidationError,
			)


def parse_query_filters(filters) -> dict:
	if isinstance(filters, str):
		return frappe.parse_json(filters) or {}
	return filters or {}


def resolve_query_branch(filters: dict) -> str | None:
	branch = filters.get(BRANCH_FIELD) or filters.get("school_branch") or get_context_branch()
	if branch:
		assert_branch_access(branch)
	return branch
