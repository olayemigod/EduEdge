from __future__ import annotations

from datetime import timedelta
from typing import Iterable

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import INSTITUTION_FIELD


ELIGIBILITY_DOCTYPE = "EduEdge Instructor Branch Assignment"
MIN_DATE = getdate("1900-01-01")
MAX_DATE = getdate("2999-12-31")


def _start(value):
	return getdate(value) if value else MIN_DATE


def _end(value):
	return getdate(value) if value else MAX_DATE


def instructor_home_institution(instructor: str) -> str:
	name = str(instructor or "").strip()
	if not name or not frappe.db.exists("Instructor", name):
		return ""
	meta = frappe.get_meta("Instructor")
	if not meta.has_field(INSTITUTION_FIELD):
		return ""
	return str(frappe.db.get_value("Instructor", name, INSTITUTION_FIELD) or "").strip()


def branch_matches_instructor_home_institution(
	instructor: str,
	branch: str,
	*,
	require_home: bool = False,
) -> bool:
	home_institution = instructor_home_institution(instructor)
	if not home_institution:
		return not require_home
	branch_institution = str(
		frappe.db.get_value("EduEdge School Branch", branch, "institution") or ""
	).strip()
	return bool(branch_institution and branch_institution == home_institution)

def get_instructor_branch_eligibility_rows(
	instructor: str,
	*,
	branch: str | None = None,
	enabled_only: bool = True,
) -> list[dict]:
	"""Return Instructor Branch Eligibility periods without changing them.

	Branch Governance owns these records. Academic assignment code may read them,
	but must never create, extend, enable, disable or otherwise mutate them.
	"""
	name = str(instructor or "").strip()
	if not name or not frappe.db.exists("Instructor", name):
		return []

	filters: dict = {"instructor": name}
	if branch:
		filters["school_branch"] = str(branch).strip()
	if enabled_only:
		filters["enabled"] = 1

	return [
		dict(row)
		for row in frappe.get_all(
			ELIGIBILITY_DOCTYPE,
			filters=filters,
			fields=[
				"name",
				"instructor",
				"instructor_name",
				"school_branch",
				"branch_name",
				"enabled",
				"is_primary",
				"valid_from",
				"valid_to",
				"creation",
				"modified",
			],
			order_by="school_branch asc, valid_from asc, valid_to asc, creation asc",
			limit_page_length=0,
		)
	]


def eligibility_covers_period(
	instructor: str,
	branch: str,
	valid_from=None,
	valid_to=None,
) -> bool:
	"""Return whether enabled Branch Governance periods cover the full target period.

	Coverage may be supplied by adjacent eligibility rows, but gaps are never
	bridged. This is deliberately stricter than an overlap check: an Instructor
	cannot receive an academic responsibility for dates outside governed Branch
	Eligibility.
	"""
	rows = get_instructor_branch_eligibility_rows(
		instructor,
		branch=branch,
		enabled_only=True,
	)
	if not rows:
		return False

	target_start = _start(valid_from)
	target_end = _end(valid_to)
	if target_end < target_start:
		return False

	intervals = sorted(
		((_start(row.get("valid_from")), _end(row.get("valid_to"))) for row in rows),
		key=lambda item: (item[0], item[1]),
	)
	merged: list[list] = []
	for start, end in intervals:
		if not merged:
			merged.append([start, end])
			continue
		previous = merged[-1]
		if start <= previous[1] + timedelta(days=1):
			if end > previous[1]:
				previous[1] = end
		else:
			merged.append([start, end])

	return any(start <= target_start and end >= target_end for start, end in merged)


def assignment_eligibility_covers_period(
	instructor: str,
	branch: str,
	valid_from=None,
	valid_to=None,
) -> bool:
	"""Strict authoring check for new academic responsibilities.

	Historical runtime access keeps using eligibility_covers_period so legacy
	records remain readable and operational history is not silently rewritten.
	New assignments require a classified Home Institution and a Branch in that
	same Institution.
	"""
	if not branch_matches_instructor_home_institution(
		instructor,
		branch,
		require_home=True,
	):
		return False
	return eligibility_covers_period(instructor, branch, valid_from, valid_to)

def assert_instructor_branch_eligibility(
	instructor: str,
	branch: str,
	valid_from=None,
	valid_to=None,
	*,
	label: str | None = None,
) -> None:
	if assignment_eligibility_covers_period(instructor, branch, valid_from, valid_to):
		return
	branch_label = (
		frappe.db.get_value("EduEdge School Branch", branch, "branch_name")
		or branch
		or _("Branch / Campus")
	)
	prefix = f"{label}: " if label else ""
	frappe.throw(
		_(
			"{0}Instructor Branch Eligibility in Branch Governance does not cover {1} for the full assignment period. "
			"Update Branch Governance first, then return to Instructor Assignments."
		).format(prefix, branch_label),
		frappe.ValidationError,
	)


def eligible_branch_names(
	instructor: str,
	*,
	within: Iterable[str] | None = None,
) -> set[str]:
	rows = get_instructor_branch_eligibility_rows(instructor, enabled_only=True)
	names = {
		str(row.get("school_branch") or "").strip()
		for row in rows
		if row.get("school_branch")
		and branch_matches_instructor_home_institution(
			instructor,
			row.get("school_branch"),
			require_home=True,
		)
	}
	if within is None:
		return names
	allowed = {str(value or "").strip() for value in within if str(value or "").strip()}
	return names.intersection(allowed)


def primary_branch(instructor: str, *, on_date=None) -> str | None:
	"""Return the effective primary governed Branch for the supplied day."""
	day = getdate(on_date or nowdate())
	rows = get_instructor_branch_eligibility_rows(instructor, enabled_only=True)
	current = [
		row
		for row in rows
		if row.get("is_primary")
		and _start(row.get("valid_from")) <= day <= _end(row.get("valid_to"))
	]
	if len(current) == 1:
		return str(current[0].get("school_branch") or "") or None
	return None
