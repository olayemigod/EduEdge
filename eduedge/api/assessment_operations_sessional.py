from __future__ import annotations

import frappe

from eduedge.api import assessment_operations as base
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_CONTEXT_ROWS = 200


def _term_compatible(group_term: str | None, selected_term: str | None) -> bool:
	"""A session-wide Class Arm is valid in every Term of its Academic Session.

	Grandfathered term-bound Student Groups remain valid only in their exact historical
	Term. New sessional Student Groups intentionally have no academic_term value.
	"""
	return not selected_term or not group_term or str(group_term) == str(selected_term)


def _student_groups(branch: str, academic_year: str | None, academic_term: str | None) -> list[dict]:
	filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	if academic_year:
		filters["academic_year"] = academic_year
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=["name", "student_group_name", "program", "course", "academic_year", "academic_term"],
		order_by="student_group_name asc",
		page_length=MAX_CONTEXT_ROWS,
	)
	return [dict(row) for row in rows if _term_compatible(row.academic_term, academic_term)]


@frappe.whitelist()
def get_assessment_context(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	assessment_group: str | None = None,
) -> dict:
	"""Compatibility wrapper for the hardened Assessment Operations context.

	Session-wide Class Arms are now handled by the primary Assessment Operations
	service. Delegate here so legacy callers inherit the same Branch, exact
	Instructor scope, Class/Form publication responsibility and readiness gates
	instead of maintaining a second authorization path.
	"""
	return base.get_assessment_context(
		branch=branch,
		academic_year=academic_year,
		academic_term=academic_term,
		student_group=student_group,
		assessment_group=assessment_group,
		result_mode="Terminal",
	)
