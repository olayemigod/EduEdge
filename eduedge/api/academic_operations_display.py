from __future__ import annotations

import frappe

from eduedge.api import academic_operations_review as base
from eduedge.api.native_display import annotate_link, annotate_master_rows, label_map


@frappe.whitelist()
def get_operations_context(
	branch: str | None = None,
	date: str | None = None,
	student_group: str | None = None,
) -> dict:
	payload = base.get_operations_context(branch=branch, date=date, student_group=student_group)
	groups = payload.get("student_groups") or []
	annotate_master_rows(groups, "Student Group", "student_group_name")
	annotate_link(groups, "program", "Program", "program_display_name")
	annotate_link(groups, "department", "Department", "department_display_name")
	annotate_link(groups, "course", "Course", "course_display_name")
	for group in groups:
		group["program_name"] = group.get("program_display_name") or group.get("program_name") or group.get("program") or ""
		group["department"] = group.get("department_display_name") or group.get("department") or ""
		group["hierarchy_label"] = " → ".join(
			value for value in (group.get("department"), group.get("program_name"), group.get("student_group_name")) if value
		)

	schedules = payload.get("schedules") or []
	annotate_link(schedules, "student_group", "Student Group", "student_group_display_name")
	annotate_link(schedules, "course", "Course", "course_display_name")
	coverage = payload.get("attendance_coverage") or []
	annotate_link(coverage, "student_group", "Student Group", "student_group_display_name")
	annotate_link(coverage, "course", "Course", "course_display_name")
	for row in coverage:
		row["student_group_name"] = row.get("student_group_display_name") or row.get("student_group_name") or row.get("student_group") or ""
	return payload


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_group_query(doctype, txt, searchfield, start, page_len, filters):
	rows = base.student_group_query(doctype, txt, searchfield, start, page_len, filters)
	group_names = [row[0] for row in rows if row]
	group_labels = label_map("Student Group", group_names)
	for row in rows:
		if row:
			row[1] = group_labels.get(row[0]) or row[1]
	return rows
