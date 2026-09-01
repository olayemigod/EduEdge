from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.education.instructor_scope import (
    get_active_instructor_names_for_user,
    is_limited_instructor_user,
)
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


def assignment_capability_enforcement_enabled() -> bool:
    """Return the migration-safe capability enforcement switch.

    Missing settings/schema intentionally fail open to the existing assignment rules
    during deployment. Once the setting is present and enabled, limited Instructor
    users fail closed on the exact capability checks below.
    """
    try:
        meta = frappe.get_meta("EduEdge Settings")
        if not meta.has_field("enforce_instructor_assignment_capabilities"):
            return False
        return bool(cint(frappe.db.get_single_value("EduEdge Settings", "enforce_instructor_assignment_capabilities")))
    except Exception:
        return False


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


def get_user_capability_assignment_rows(
    capability: str,
    *,
    user: str | None = None,
    school_branch: str | None = None,
    on_date=None,
) -> list[dict]:
    """Return effective exact assignment rows that explicitly enable one capability."""
    if capability not in CAPABILITY_FIELDS:
        return []
    resolved_user = user or frappe.session.user
    instructors = get_active_instructor_names_for_user(resolved_user)
    if len(instructors) != 1:
        return []
    filters = {
        "instructor": instructors[0],
        "assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
        "enabled": 1,
        capability: 1,
    }
    if school_branch:
        filters["school_branch"] = school_branch
    rows = frappe.get_all(
        ASSIGNMENT_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "school_branch",
            "program_offering",
            "assignment_scope",
            "student_group",
            "course",
            "valid_from",
            "valid_to",
        ],
        order_by="school_branch asc, program_offering asc, course asc, valid_from desc",
        limit_page_length=0,
    )
    resolved_date = getdate(on_date or nowdate())
    return [dict(row) for row in rows if _effective(row, resolved_date)]


def require_instructor_assignment_capability(
    capability: str,
    *,
    user: str | None = None,
    school_branch: str,
    program_offering: str,
    course: str,
    student_group: str | None = None,
    on_date=None,
) -> bool:
    """Enforce one exact capability for limited Teacher/Instructor users when enabled.

    Managers and privileged users keep their established role/permission paths. The
    rollout switch defaults off so existing sites can migrate, review identity mappings
    and configure capability flags before activating stricter operational enforcement.
    """
    resolved_user = user or frappe.session.user
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):
        return True
    state = get_instructor_assignment_capability_state(
        user=resolved_user,
        school_branch=school_branch,
        program_offering=program_offering,
        course=course,
        student_group=student_group,
        on_date=on_date,
    )
    if state.get(capability):
        return True
    label = CAPABILITY_LABELS.get(capability, "the required operation")
    if state.get("identity_status") == "ambiguous":
        frappe.throw(
            _("Your User account resolves to more than one active Instructor. {0} is blocked until the identity mapping is corrected.").format(label),
            frappe.PermissionError,
        )
    frappe.throw(
        _("Your exact active Instructor Assignment does not grant {0} for this Branch, Class, Class Arm and Subject context.").format(label),
        frappe.PermissionError,
    )
