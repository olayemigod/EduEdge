from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api.fuzzy_search import get_bounded_candidates, rank_link_rows
from eduedge.api import student_enrollments as enrollment
from eduedge.education.custom_fields import BRANCH_FIELD

MAX_RESULTS = 50


def _limit(value: int | str | None) -> int:
	return min(max(cint(value) or 20, 1), MAX_RESULTS)


@frappe.whitelist()
def search_eligible_students(
	branch: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Search enabled Students the user may enroll within the Branch institution."""
	enrollment._require_permission("read")
	resolved, selected_branch, allowed = enrollment._resolve_branch(branch)
	institution = selected_branch.get("institution")
	branches = enrollment._same_institution_allowed_branches(institution, allowed)
	if not branches:
		return []

	rows = get_bounded_candidates(
		"Student",
		filters={BRANCH_FIELD: ["in", branches], "enabled": 1},
		fields=[
			"name",
			"student_name",
			BRANCH_FIELD,
			"student_email_id",
			"student_mobile_number",
		],
		query=query,
		search_fields=("student_name", "student_email_id", "student_mobile_number"),
		order_by="student_name asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("student_name") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get(BRANCH_FIELD),
				row.get("student_mobile_number"),
				row.get("student_email_id"),
			)
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value", "student_mobile_number", "student_email_id"),
		search_fields=("label", "description"),
		start=0,
		page_length=_limit(page_length),
	)


@frappe.whitelist()
def search_enrollment_offerings(
	branch: str,
	student: str,
	query: str = "",
	page_length: int | str = 20,
) -> list[dict]:
	"""Search active enrollment-enabled Programme Offerings for a validated Student/Branch pair."""
	enrollment._require_permission("read")
	resolved, selected_branch, allowed = enrollment._resolve_branch(branch)
	student_row = enrollment._student_row(student)
	if not cint(student_row.enabled):
		frappe.throw(_("Only enabled Students can be enrolled."), frappe.ValidationError)
	institution = selected_branch.get("institution")
	if enrollment._student_institution(student_row) != institution:
		frappe.throw(
			_("A Student may enroll across Campuses only within the same Institution."),
			frappe.ValidationError,
		)
	if student_row.get(BRANCH_FIELD) not in enrollment._same_institution_allowed_branches(
		institution, allowed
	):
		frappe.throw(
			_("You do not have access to the Student's home Branch."),
			frappe.PermissionError,
		)

	rows = get_bounded_candidates(
		"EduEdge Program Offering",
		filters={
			"school_branch": resolved,
			"institution": institution,
			"is_active": 1,
			"enrollment_enabled": 1,
		},
		fields=[
			"name",
			"offering_title",
			"offering_code",
			"program",
			"department",
			"academic_year",
			"academic_term",
			"student_batch",
		],
		query=query,
		search_fields=(
			"offering_title",
			"offering_code",
			"program",
			"department",
			"academic_year",
			"academic_term",
		),
		order_by="academic_year desc, offering_title asc",
	)
	candidates = []
	for source in rows:
		row = dict(source)
		row["value"] = row.get("name")
		row["label"] = row.get("offering_title") or row.get("name")
		row["description"] = " · ".join(
			str(value)
			for value in (
				row.get("offering_code"),
				row.get("program"),
				row.get("department"),
				row.get("academic_year"),
				row.get("academic_term"),
			)
			if value
		)
		candidates.append(row)
	return rank_link_rows(
		candidates,
		str(query or "").strip(),
		exact_fields=("value", "offering_code"),
		search_fields=("label", "description"),
		start=0,
		page_length=_limit(page_length),
	)
