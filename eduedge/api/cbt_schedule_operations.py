from __future__ import annotations

from typing import Any

import frappe

from eduedge.api import cbt_schedule_operations_hardened as hardened
from eduedge.api.cbt_schedule_operations_hardened import (
	get_candidate,
	get_context,
	get_schedule,
	get_template_context,
	record_intervention,
	save_candidate,
	save_schedule,
	set_candidate_status,
	set_schedule_status,
)
from eduedge.education.custom_fields import BRANCH_FIELD


def _session_term_compatible(group_term: str | None, selected_term: str | None) -> bool:
	return not selected_term or not group_term or str(group_term) == str(selected_term)


def _course_compatible(group_course: str | None, selected_course: str | None) -> bool:
	# Batch/Class based Student Groups normally have no Course. A blank Course means
	# the session-wide Class Arm is usable for any curriculum Course on the Schedule.
	return not selected_course or not group_course or str(group_course) == str(selected_course)


def _sessional_student_group_options(payload: dict, query: str) -> list[dict]:
	hardened._require_permission("Student Group", "read")
	branch = payload.get("school_branch") or payload.get("page_branch") or ""
	if not branch:
		return []
	hardened._branch_row(branch)

	filters: dict[str, Any] = {BRANCH_FIELD: branch, "disabled": 0}
	if payload.get("academic_year"):
		filters["academic_year"] = payload.get("academic_year")
	if payload.get("program"):
		filters["program"] = payload.get("program")

	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=["name", "student_group_name", "academic_year", "academic_term", "program", "course"],
		order_by="student_group_name asc",
		limit_page_length=hardened.MAX_LIST_ROWS,
	)
	selected_term = payload.get("academic_term")
	selected_course = payload.get("course")
	options = []
	for row in rows:
		if not _session_term_compatible(row.academic_term, selected_term):
			continue
		if not _course_compatible(row.course, selected_course):
			continue
		options.append(
			{
				"value": row.name,
				"label": row.student_group_name or row.name,
				"description": " · ".join(
					filter(
						None,
						[
							row.academic_year,
							row.academic_term or "Full session",
							row.program,
							row.course,
						],
					)
				),
			}
		)
	return hardened._filter_options(options, query)


@frappe.whitelist()
def search_options(fieldname: str, txt: str | None = None, values: str | dict | None = None) -> list[dict]:
	"""Preserve hardened option search, with session-aware Class Arm selection for CBT."""
	if fieldname != "student_group":
		return hardened.search_options(fieldname, txt, values)
	hardened._require_login()
	payload = hardened._parse_json(values)
	return _sessional_student_group_options(payload, str(txt or "").strip())


@frappe.whitelist()
def assign_template_student_group(schedule: str) -> dict:
	"""Retry once when a concurrent request wins a candidate unique constraint.

	The hardened implementation recalculates existing assignments on each call,
	so the retry becomes an idempotent skip rather than a duplicate failure.
	"""
	try:
		return hardened.assign_template_student_group(schedule)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		return hardened.assign_template_student_group(schedule)


__all__ = (
	"assign_template_student_group",
	"get_candidate",
	"get_context",
	"get_schedule",
	"get_template_context",
	"record_intervention",
	"save_candidate",
	"save_schedule",
	"search_options",
	"set_candidate_status",
	"set_schedule_status",
)
