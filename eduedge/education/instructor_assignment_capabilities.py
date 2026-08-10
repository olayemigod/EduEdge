from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint, getdate, nowdate

from eduedge.education.instructor_scope import get_active_instructor_names_for_user
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"
CAPABILITY_FIELDS = (
    "can_view_subject_content",
    "can_manage_subject_topics",
    "can_author_cbt",
    "can_create_assessment_plans",
    "can_enter_marks",
)
CAPABILITY_LABELS = {
    "can_view_subject_content": "View Subject Content",
    "can_manage_subject_topics": "Manage Subject Topics",
    "can_author_cbt": "Author CBT Questions",
    "can_create_assessment_plans": "Create Assessment Plans",
    "can_enter_marks": "Enter Marks",
}


def _blank_state(*, user: str, school_branch: str, program_offering: str, course: str, student_group: str = "") -> dict:
    return {
        "user": user,
        "identity_status": "missing",
        "instructor": "",
        "school_branch": school_branch,
        "program_offering": program_offering,
        "student_group": student_group,
        "course": course,
        "assignment_names": [],
        **{fieldname: False for fieldname in CAPABILITY_FIELDS},
    }


def _effective(row: Any, on_date) -> bool:
    if not cint(row.get("enabled") if hasattr(row, "get") else getattr(row, "enabled", 0)):
        return False
    valid_from = row.get("valid_from") if hasattr(row, "get") else getattr(row, "valid_from", None)
    valid_to = row.get("valid_to") if hasattr(row, "get") else getattr(row, "valid_to", None)
    if valid_from and getdate(valid_from) > on_date:
        return False
    if valid_to and getdate(valid_to) < on_date:
        return False
    return True


def _scope_matches(row: Any, student_group: str) -> bool:
    scope = row.get("assignment_scope") if hasattr(row, "get") else getattr(row, "assignment_scope", "")
    assigned_group = row.get("student_group") if hasattr(row, "get") else getattr(row, "student_group", "")
    if scope == CLASS_SCOPE:
        return True
    if scope == CLASS_ARM_SCOPE:
        return bool(student_group and assigned_group == student_group)
    return False


def get_matching_instructor_capability_assignments(
    *,
    user: str,
    school_branch: str,
    program_offering: str,
    course: str,
    student_group: str | None = None,
    on_date=None,
) -> tuple[str, str, list[dict]]:
    """Return the exact effective subject assignments that may grant capabilities.

    Identity must resolve to exactly one active Instructor. No capability is inferred
    from role, Branch Eligibility, an Instructor master alone, or a broad Subject match.
    Class-scope Subject assignments cover their Offering; Class Arm assignments require
    the exact Student Group when one is supplied by the operational context.
    """
    resolved_user = str(user or "").strip()
    branch = str(school_branch or "").strip()
    offering = str(program_offering or "").strip()
    subject = str(course or "").strip()
    group = str(student_group or "").strip()
    if not resolved_user or not branch or not offering or not subject:
        return "missing", "", []

    instructors = get_active_instructor_names_for_user(resolved_user)
    if not instructors:
        return "missing", "", []
    if len(instructors) != 1:
        return "ambiguous", "", []
    instructor = instructors[0]

    rows = frappe.get_all(
        ASSIGNMENT_DOCTYPE,
        filters={
            "instructor": instructor,
            "school_branch": branch,
            "program_offering": offering,
            "course": subject,
            "assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
            "enabled": 1,
        },
        fields=[
            "name",
            "assignment_title",
            "assignment_type",
            "assignment_scope",
            "student_group",
            "valid_from",
            "valid_to",
            *CAPABILITY_FIELDS,
        ],
        order_by="assignment_scope asc, valid_from desc, modified desc",
        limit_page_length=100,
    )
    resolved_date = getdate(on_date or nowdate())
    matched = [dict(row) for row in rows if _effective(row, resolved_date) and _scope_matches(row, group)]
    return "resolved", instructor, matched


def get_instructor_assignment_capability_state(
    *,
    user: str,
    school_branch: str,
    program_offering: str,
    course: str,
    student_group: str | None = None,
    on_date=None,
) -> dict:
    resolved_user = str(user or "").strip()
    branch = str(school_branch or "").strip()
    offering = str(program_offering or "").strip()
    subject = str(course or "").strip()
    group = str(student_group or "").strip()
    state = _blank_state(
        user=resolved_user,
        school_branch=branch,
        program_offering=offering,
        course=subject,
        student_group=group,
    )
    identity_status, instructor, rows = get_matching_instructor_capability_assignments(
        user=resolved_user,
        school_branch=branch,
        program_offering=offering,
        course=subject,
        student_group=group,
        on_date=on_date,
    )
    state["identity_status"] = identity_status
    state["instructor"] = instructor
    state["assignment_names"] = [row.get("name") for row in rows if row.get("name")]
    for row in rows:
        for fieldname in CAPABILITY_FIELDS:
            state[fieldname] = bool(state[fieldname] or cint(row.get(fieldname)))
    return state


def user_has_instructor_assignment_capability(
    capability: str,
    *,
    user: str,
    school_branch: str,
    program_offering: str,
    course: str,
    student_group: str | None = None,
    on_date=None,
) -> bool:
    if capability not in CAPABILITY_FIELDS:
        return False
    state = get_instructor_assignment_capability_state(
        user=user,
        school_branch=school_branch,
        program_offering=program_offering,
        course=course,
        student_group=student_group,
        on_date=on_date,
    )
    return bool(state.get(capability))
