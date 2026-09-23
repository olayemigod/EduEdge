from __future__ import annotations

import math
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.api import teacher_assignments as core
from eduedge.api.instructor_assignment_lifecycle import _lifecycle_status
from eduedge.api.instructor_assignments import (
    ASSIGNMENT_TYPES,
    BULK_SCOPES,
    CLASS_RESPONSIBILITY_TYPES,
    SUBJECT_REQUIRED_TYPES,
    _all_options,
    _can_manage_assignments,
    _filter_planner_options_by_instructor,
    _instructors,
)
from eduedge.services.instructor_branch_governance import (
    eligible_branch_names,
    get_instructor_branch_eligibility_rows,
)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MAX_FILTER_SCAN = 5000
LIFECYCLE_STATUSES = ("Current", "Scheduled", "Ended", "Replaced", "Transferred", "Disabled")
ORIGINS = ("Normal", "Prepared", "Replacement", "Transfer")
PRESETS = (
    "current_upcoming",
    "current",
    "scheduled",
    "ended",
    "replaced",
    "transferred",
    "prepared",
    "all",
)

REGISTER_FIELDS = [
    "name",
    "assignment_title",
    "instructor",
    "assignment_type",
    "assignment_scope",
    "school_branch",
    "program_offering",
    "student_group",
    "course",
    "academic_year",
    "academic_term",
    "valid_from",
    "valid_to",
    "enabled",
    "ended_on",
    "ended_by",
    "end_reason",
    "replaced_by_assignment",
    "replaces_assignment",
    "replacement_reason",
    "transferred_from_assignment",
    "transferred_to_assignment",
    "transfer_reason",
    "prepared_from_assignment",
    "preparation_reason",
    "modified",
]


def _row_value(row, key: str, default=None):
    if hasattr(row, "get"):
        return row.get(key, default)
    return getattr(row, key, default)


def _row_name(row) -> str:
    return str(_row_value(row, "name", "") or "").strip()


def _parse_filters(value: str | dict | None) -> dict:
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            value = {}
    source = dict(value or {}) if isinstance(value, dict) else {}
    allowed = {
        "branch",
        "academic_year",
        "academic_term",
        "program_offering",
        "student_group",
        "course",
        "assignment_type",
        "assignment_scope",
        "lifecycle_status",
        "origin",
        "date_from",
        "date_to",
        "search_text",
        "preset",
    }
    filters = {key: str(source.get(key) or "").strip() for key in allowed}
    filters["preset"] = filters.get("preset") or "current_upcoming"
    if filters["preset"] not in PRESETS:
        filters["preset"] = "current_upcoming"
    if filters["lifecycle_status"] and filters["lifecycle_status"] not in LIFECYCLE_STATUSES:
        frappe.throw(_("Select a valid Instructor Assignment status filter."), frappe.ValidationError)
    if filters["origin"] and filters["origin"] not in ORIGINS:
        frappe.throw(_("Select a valid Instructor Assignment origin filter."), frappe.ValidationError)
    if filters["assignment_type"] and filters["assignment_type"] not in ASSIGNMENT_TYPES:
        frappe.throw(_("Select a valid Assignment Type filter."), frappe.ValidationError)
    if filters["assignment_scope"] and filters["assignment_scope"] not in BULK_SCOPES:
        frappe.throw(_("Select a valid Assignment Scope filter."), frappe.ValidationError)
    if filters["date_from"]:
        getdate(filters["date_from"])
    if filters["date_to"]:
        getdate(filters["date_to"])
    if filters["date_from"] and filters["date_to"] and getdate(filters["date_to"]) < getdate(filters["date_from"]):
        frappe.throw(_("History To cannot be earlier than History From."), frappe.ValidationError)
    return filters


def _page(value: Any, default: int = 1) -> int:
    try:
        return max(int(value or default), 1)
    except Exception:
        return default


def _page_size(value: Any) -> int:
    try:
        resolved = int(value or DEFAULT_PAGE_SIZE)
    except Exception:
        resolved = DEFAULT_PAGE_SIZE
    return max(10, min(resolved, MAX_PAGE_SIZE))


def _origin(row) -> str:
    if row.prepared_from_assignment:
        return "Prepared"
    if row.replaces_assignment:
        return "Replacement"
    if row.transferred_from_assignment:
        return "Transfer"
    return "Normal"


def _preset_matches(status: str, origin: str, preset: str) -> bool:
    if preset == "all":
        return True
    if preset == "current_upcoming":
        return status in {"Current", "Scheduled"}
    if preset == "prepared":
        return origin == "Prepared"
    mapping = {
        "current": "Current",
        "scheduled": "Scheduled",
        "ended": "Ended",
        "replaced": "Replaced",
        "transferred": "Transferred",
    }
    return status == mapping.get(preset)


def _overlaps_history(row, date_from: str, date_to: str) -> bool:
    row_start = getdate(row.valid_from) if row.valid_from else None
    row_end = getdate(row.valid_to) if row.valid_to else None
    if date_from and row_end and row_end < getdate(date_from):
        return False
    if date_to and row_start and row_start > getdate(date_to):
        return False
    return True


def _search_text(row, maps: dict) -> str:
    branch = maps["branches"].get(row.school_branch, {})
    offering = maps["offerings"].get(row.program_offering, {})
    group = maps["groups"].get(row.student_group, {})
    course = maps["courses"].get(row.course, {})
    parts = [
        row.assignment_title,
        row.assignment_type,
        row.assignment_scope,
        row.academic_year,
        row.academic_term,
        branch.get("branch_name"),
        branch.get("institution_name"),
        offering.get("offering_title"),
        offering.get("program"),
        group.get("eduedge_display_name"),
        group.get("student_group_name"),
        course.get("course_name"),
    ]
    return " ".join(str(value or "") for value in parts).lower()


def _label_maps(allowed, offering_rows, groups, courses) -> dict:
    return {
        "branches": {_row_name(row): row for row in allowed if _row_name(row)},
        "offerings": {_row_name(row): row for row in offering_rows if _row_name(row)},
        "groups": {_row_name(row): row for row in groups if _row_name(row)},
        "courses": {_row_name(row): row for row in courses if _row_name(row)},
    }


def _candidate_filters(instructor: str, allowed_names: list[str], filters: dict) -> dict:
    result: dict[str, Any] = {"instructor": instructor, "school_branch": ["in", allowed_names]}
    direct = {
        "branch": "school_branch",
        "academic_year": "academic_year",
        "academic_term": "academic_term",
        "program_offering": "program_offering",
        "student_group": "student_group",
        "course": "course",
        "assignment_type": "assignment_type",
        "assignment_scope": "assignment_scope",
    }
    for source, target in direct.items():
        if filters.get(source):
            result[target] = filters[source]
    return result


def _filter_register_rows(instructor: str, allowed_names: list[str], filters: dict, maps: dict) -> tuple[list[dict], dict, bool]:
    if not instructor or not allowed_names:
        return [], {status: 0 for status in LIFECYCLE_STATUSES}, False

    rows = frappe.get_list(
        "EduEdge Instructor Assignment",
        filters=_candidate_filters(instructor, allowed_names, filters),
        fields=REGISTER_FIELDS,
        order_by="modified desc",
        limit_page_length=MAX_FILTER_SCAN + 1,
    )
    truncated = len(rows) > MAX_FILTER_SCAN
    if truncated:
        rows = rows[:MAX_FILTER_SCAN]

    today = getdate(nowdate())
    search = filters.get("search_text", "").lower()
    scoped = []
    for row in rows:
        status = _lifecycle_status(row, today)
        origin = _origin(row)
        if filters.get("origin") and origin != filters["origin"]:
            continue
        if not _overlaps_history(row, filters.get("date_from", ""), filters.get("date_to", "")):
            continue
        if search and search not in _search_text(row, maps):
            continue
        row["register_lifecycle_status"] = status
        row["register_origin"] = origin
        scoped.append(row)

    counts = {status: 0 for status in LIFECYCLE_STATUSES}
    for row in scoped:
        counts[row["register_lifecycle_status"]] = counts.get(row["register_lifecycle_status"], 0) + 1

    status_filter = filters.get("lifecycle_status")
    selected = [
        row
        for row in scoped
        if (not status_filter or row["register_lifecycle_status"] == status_filter)
        and _preset_matches(row["register_lifecycle_status"], row["register_origin"], filters["preset"])
    ]
    return selected, counts, truncated


def _validate_filter_context(filters: dict, allowed, offering_rows, groups, courses) -> None:
    allowed_names = {_row_name(row) for row in allowed if _row_name(row)}
    if filters.get("branch") and filters["branch"] not in allowed_names:
        frappe.throw(_("The selected register Branch / Campus is not available to your user."), frappe.PermissionError)

    offering_map = {_row_name(row): row for row in offering_rows if _row_name(row)}
    if filters.get("program_offering"):
        offering = offering_map.get(filters["program_offering"])
        if not offering:
            frappe.throw(_("The selected register Class / Programme Offering is not available to your user."), frappe.PermissionError)
        if filters.get("branch") and _row_value(offering, "school_branch") != filters["branch"]:
            frappe.throw(_("The selected register Class does not belong to the selected Branch."), frappe.ValidationError)
        if filters.get("academic_year") and _row_value(offering, "academic_year") != filters["academic_year"]:
            frappe.throw(_("The selected register Class does not belong to the selected Academic Session."), frappe.ValidationError)
        if filters.get("academic_term") and _row_value(offering, "academic_term") != filters["academic_term"]:
            frappe.throw(_("The selected register Class does not belong to the selected Term / Semester."), frappe.ValidationError)

    group_map = {_row_name(row): row for row in groups if _row_name(row)}
    if filters.get("student_group") and filters["student_group"] not in group_map:
        frappe.throw(_("The selected register Class Arm is not available to your user."), frappe.PermissionError)

    course_map = {_row_name(row): row for row in courses if _row_name(row)}
    if filters.get("course") and filters["course"] not in course_map:
        frappe.throw(_("The selected register Subject / Course is not available to your user."), frappe.PermissionError)


@frappe.whitelist()
def get_instructor_assignment_register_page(
    instructor: str | None = None,
    branches: str | list | None = None,
    offerings: str | list | None = None,
    register_filters: str | dict | None = None,
    register_page: int | str | None = None,
    register_page_size: int | str | None = None,
) -> dict:
    """Return governed planner options plus permission-scoped assignment history.

    Branch Governance is upstream of the planner: current Instructor Branch
    Eligibility limits where new responsibilities may be created. Historical
    assignment filters intentionally retain every Branch visible to the manager so
    withdrawing eligibility never hides academic history.
    """
    core._require_read()
    permitted = core._allowed_branches()
    permitted_names = [_row_name(row) for row in permitted if _row_name(row)]

    instructors = _instructors(include_history=True)
    if not instructor and not _can_manage_assignments() and len(instructors) == 1:
        instructor = _row_name(instructors[0])
    selected_instructor = next((row for row in instructors if _row_name(row) == instructor), None)
    if instructor and not selected_instructor:
        frappe.throw(_("The selected Instructor is not available to your user."), frappe.PermissionError)
    authoring_available = bool(
        not selected_instructor or str(selected_instructor.get("status") or "") == "Active"
    )

    governed_names = (
        eligible_branch_names(instructor, within=permitted_names)
        if instructor and authoring_available
        else set()
    )
    governed = [row for row in permitted if _row_name(row) in governed_names]
    governed_name_list = [_row_name(row) for row in governed if _row_name(row)]

    selected = core._list_values(branches) if authoring_available else []
    if selected and any(name not in governed_name_list for name in selected):
        frappe.throw(
            _("One or more selected Branches are not covered by this Instructor's Branch Governance eligibility."),
            frappe.PermissionError,
        )
    if not selected:
        current = str((core.get_current_school_branch() or {}).get("name") or "").strip()
        selected = [current] if current in governed_name_list else (
            governed_name_list[:] if len(governed_name_list) == 1 else []
        )

    # Planner data is governed by current Instructor eligibility.
    offering_rows, groups, courses, course_map, configured_course_map = _all_options(governed)
    offering_rows, groups, courses, course_map, configured_course_map = _filter_planner_options_by_instructor(
        instructor,
        offering_rows,
        groups,
        courses,
        course_map,
        configured_course_map,
    )
    requested_offerings = core._list_values(offerings) if authoring_available else []
    offering_names = {_row_name(row) for row in offering_rows if _row_name(row)}
    if requested_offerings and any(name not in offering_names for name in requested_offerings):
        frappe.throw(
            _("One or more selected Classes are outside this Instructor's Branch Governance eligibility."),
            frappe.PermissionError,
        )

    # Historical register options use the manager's full permitted scope so old
    # responsibilities remain findable even after eligibility is withdrawn.
    register_offerings, register_groups, register_courses, _, register_configured_course_map = _all_options(permitted)
    filters = _parse_filters(register_filters)
    _validate_filter_context(
        filters,
        permitted,
        register_offerings,
        register_groups,
        register_courses,
    )
    register_allowed_names = permitted_names
    if filters.get("branch"):
        register_allowed_names = [filters["branch"]]

    maps = _label_maps(
        permitted,
        register_offerings,
        register_groups,
        register_courses,
    )
    filtered_rows, counts, scan_truncated = _filter_register_rows(
        instructor or "",
        register_allowed_names,
        filters,
        maps,
    )

    page_size = _page_size(register_page_size)
    total = len(filtered_rows)
    page_count = max(math.ceil(total / page_size), 1)
    page = min(_page(register_page), page_count)
    start = (page - 1) * page_size
    assignments = filtered_rows[start : start + page_size]

    eligibility_rows = []
    if instructor and _can_manage_assignments():
        eligibility_rows = [
            row
            for row in get_instructor_branch_eligibility_rows(instructor, enabled_only=False)
            if row.get("school_branch") in permitted_names
        ]

    return {
        "allowed_branches": governed,
        "permitted_branches": permitted,
        "selected_branches": selected,
        "instructors": instructors,
        "selected_instructor": selected_instructor,
        "authoring_available": authoring_available,
        "offerings": offering_rows,
        "groups": groups,
        "courses": courses,
        "course_map": {key: sorted(values) for key, values in course_map.items()},
        "configured_course_map": {key: sorted(values) for key, values in configured_course_map.items()},
        "register_offerings": register_offerings,
        "register_groups": register_groups,
        "register_courses": register_courses,
        "register_configured_course_map": {
            key: sorted(values) for key, values in register_configured_course_map.items()
        },
        "assignments": assignments,
        "branch_assignments": eligibility_rows,
        "assignment_types": list(ASSIGNMENT_TYPES),
        "assignment_scopes": list(BULK_SCOPES),
        "subject_required_types": sorted(SUBJECT_REQUIRED_TYPES),
        "class_responsibility_types": sorted(CLASS_RESPONSIBILITY_TYPES),
        "governance": {
            "route": "/app/eduedge-branch-governance",
            "eligible_branch_count": len(governed_names),
            "eligibility_period_count": len(eligibility_rows),
        },
        "assignment_register": {
            "filters": filters,
            "preset": filters["preset"],
            "counts": counts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "page_count": page_count,
            "from_row": start + 1 if total else 0,
            "to_row": min(start + page_size, total),
            "has_previous": page > 1,
            "has_next": page < page_count,
            "scan_truncated": scan_truncated,
            "max_filter_scan": MAX_FILTER_SCAN,
        },
        "permissions": {
            "can_manage": _can_manage_assignments(),
            "can_create": frappe.has_permission("EduEdge Instructor Assignment", "create"),
            "can_write": frappe.has_permission("EduEdge Instructor Assignment", "write"),
            "can_view_branch_governance": frappe.has_permission(
                "EduEdge Instructor Branch Assignment",
                "read",
            ),
        },
    }

