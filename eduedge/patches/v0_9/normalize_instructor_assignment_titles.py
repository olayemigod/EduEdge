from __future__ import annotations

import frappe

from eduedge.eduedge.doctype.eduedge_instructor_assignment.eduedge_instructor_assignment import (
    _assignment_target_label,
    _course_label,
)


def execute() -> None:
    """Backfill readable titles without changing assignment identity or scope."""
    if not frappe.db.exists("DocType", "EduEdge Instructor Assignment"):
        return

    rows = frappe.get_all(
        "EduEdge Instructor Assignment",
        fields=[
            "name",
            "assignment_title",
            "assignment_type",
            "assignment_scope",
            "instructor",
            "instructor_name",
            "program_offering",
            "student_group",
            "course",
        ],
        limit_page_length=0,
    )
    for row in rows:
        target = _assignment_target_label(
            row.assignment_scope,
            row.program_offering,
            row.student_group,
        )
        parts = [row.instructor_name or row.instructor, row.assignment_type, target]
        if row.course:
            parts.append(_course_label(row.course))
        readable_title = " · ".join(value for value in parts if value)
        if readable_title and readable_title != (row.assignment_title or ""):
            frappe.db.set_value(
                "EduEdge Instructor Assignment",
                row.name,
                "assignment_title",
                readable_title,
                update_modified=False,
            )

    frappe.clear_cache(doctype="EduEdge Instructor Assignment")
