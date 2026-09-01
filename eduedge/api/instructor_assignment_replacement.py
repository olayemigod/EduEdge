from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from eduedge.api.instructor_assignments import (
    _branch_periods,
    _period_dates,
    _require_assignment_manager,
    _save_branch_period,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
    CLASS_ARM_SCOPE,
    LEGACY_SUBJECT_TEACHER,
    SUBJECT_INSTRUCTOR,
    UNIQUE_PRIMARY_ASSIGNMENT_TYPES,
)
from eduedge.platform.access import require_eduedge_access


def _clean_reason(reason: str | None) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(
            _("Give a short reason for replacing this Instructor Assignment."),
            frappe.ValidationError,
        )
    return value


def _handover_date(value: str | None):
    resolved = getdate(value or nowdate())
    today = getdate(nowdate())
    if resolved < today:
        frappe.throw(
            _("Handover Date cannot be earlier than today. Historical replacement is not backdated through this action."),
            frappe.ValidationError,
        )
    return resolved


def _overlap(start_a=None, end_a=None, start_b=None, end_b=None) -> bool:
    minimum = getdate("1900-01-01")
    maximum = getdate("2999-12-31")
    a_start = getdate(start_a) if start_a else minimum
    a_end = getdate(end_a) if end_a else maximum
    b_start = getdate(start_b) if start_b else minimum
    b_end = getdate(end_b) if end_b else maximum
    return a_start <= b_end and b_start <= a_end


def _same_date(left, right) -> bool:
    if not left and not right:
        return True
    if not left or not right:
        return False
    return getdate(left) == getdate(right)


def _source_assignment(name: str):
    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment to replace."), frappe.ValidationError)
    doc = frappe.get_doc("EduEdge Instructor Assignment", assignment_name)
    doc.check_permission("write")
    assert_branch_access(doc.school_branch)
    return doc


def _replacement_instructor(name: str, source):
    instructor_name = str(name or "").strip()
    if not instructor_name:
        frappe.throw(_("Select the replacement Instructor."), frappe.ValidationError)
    if instructor_name == source.instructor:
        frappe.throw(
            _("Replacement Instructor must be different from the outgoing Instructor."),
            frappe.ValidationError,
        )
    doc = frappe.get_doc("Instructor", instructor_name)
    doc.check_permission("read")
    if str(doc.status or "") != "Active":
        frappe.throw(_("Select an active replacement Instructor."), frappe.ValidationError)
    return doc


def _successor_dates(source, handover):
    today = getdate(nowdate())
    if not cint(source.enabled):
        frappe.throw(
            _("Disabled Instructor Assignments cannot be replaced through the active handover action."),
            frappe.ValidationError,
        )
    if source.ended_on:
        frappe.throw(
            _("This Instructor Assignment already has an End lifecycle action."),
            frappe.ValidationError,
        )
    if source.valid_from and getdate(source.valid_from) > today:
        frappe.throw(
            _("This Instructor Assignment has not started yet. Scheduled assignments need a separate planned replacement action."),
            frappe.ValidationError,
        )
    if source.valid_to and getdate(source.valid_to) < today:
        frappe.throw(
            _("This Instructor Assignment has already ended by its validity period and will not be rewritten."),
            frappe.ValidationError,
        )
    if source.valid_from and handover < getdate(source.valid_from):
        frappe.throw(_("Handover Date cannot be earlier than Valid From."), frappe.ValidationError)
    if source.valid_to and handover > getdate(source.valid_to):
        frappe.throw(
            _("Handover Date cannot be later than the outgoing assignment Valid To date."),
            frappe.ValidationError,
        )

    successor_start = getdate(add_days(handover, 1))
    period_start, period_end = _period_dates(source.academic_year, source.academic_term)
    if period_end and source.valid_to and getdate(source.valid_to) > getdate(period_end):
        frappe.throw(
            _("The outgoing assignment extends beyond its academic period. Correct that record before replacing it."),
            frappe.ValidationError,
        )
    successor_end = getdate(source.valid_to) if source.valid_to else (getdate(period_end) if period_end else None)
    if successor_end and successor_start > successor_end:
        frappe.throw(
            _("No responsibility period remains after the Handover Date. End the assignment instead of replacing it."),
            frappe.ValidationError,
        )
    if period_start and successor_start < getdate(period_start):
        frappe.throw(
            _("Replacement responsibility cannot start before the selected Class academic period."),
            frappe.ValidationError,
        )
    if period_end and successor_start > getdate(period_end):
        frappe.throw(
            _("Replacement responsibility would start after the selected Class academic period."),
            frappe.ValidationError,
        )
    return successor_start, successor_end


def _type_variants(value: str) -> list[str]:
    return [SUBJECT_INSTRUCTOR, LEGACY_SUBJECT_TEACHER] if value == SUBJECT_INSTRUCTOR else [value]


def _replacement_conflicts(source, replacement_instructor: str, successor_start, successor_end) -> list[dict]:
    conflicts: list[dict] = []
    records = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "instructor": replacement_instructor,
            "school_branch": source.school_branch,
            "program_offering": source.program_offering,
            "assignment_scope": source.assignment_scope,
            "assignment_type": ["in", _type_variants(source.assignment_type)],
            "enabled": 1,
        },
        fields=["name", "student_group", "course", "valid_from", "valid_to"],
        limit_page_length=0,
    )
    for row in records:
        if (row.student_group or "") != (source.student_group or ""):
            continue
        if (row.course or "") != (source.course or ""):
            continue
        if _overlap(successor_start, successor_end, row.valid_from, row.valid_to):
            conflicts.append(
                {
                    "name": row.name,
                    "type": "replacement-instructor-overlap",
                    "reason": _("Replacement Instructor already has an overlapping exact academic responsibility."),
                }
            )

    if source.assignment_type in UNIQUE_PRIMARY_ASSIGNMENT_TYPES:
        filters = {
            "school_branch": source.school_branch,
            "program_offering": source.program_offering,
            "assignment_scope": source.assignment_scope,
            "assignment_type": source.assignment_type,
            "enabled": 1,
            "name": ["!=", source.name],
        }
        if source.assignment_scope == CLASS_ARM_SCOPE:
            filters["student_group"] = source.student_group
        primary_rows = frappe.get_all(
            "EduEdge Instructor Assignment",
            filters=filters,
            fields=["name", "instructor", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in primary_rows:
            if _overlap(successor_start, successor_end, row.valid_from, row.valid_to):
                conflicts.append(
                    {
                        "name": row.name,
                        "type": "primary-responsibility-overlap",
                        "other_instructor": row.instructor,
                        "reason": _("Another Instructor already owns this primary responsibility during the successor period."),
                    }
                )
    return conflicts


def _period_covers(row, start, end) -> bool:
    start_ok = not row.valid_from or getdate(row.valid_from) <= getdate(start)
    if end:
        end_ok = not row.valid_to or getdate(row.valid_to) >= getdate(end)
    else:
        end_ok = not row.valid_to
    return bool(start_ok and end_ok)


def _branch_access_preview(instructor: str, branch: str, start, end) -> dict:
    periods = _branch_periods(instructor, branch)
    covering = next(
        (row for row in periods if cint(row.enabled) and _period_covers(row, start, end)),
        None,
    )
    if covering:
        return {
            "action": "existing",
            "name": covering.name,
            "school_branch": branch,
            "valid_from": str(covering.valid_from or ""),
            "valid_to": str(covering.valid_to or ""),
            "changed": False,
        }
    exact_disabled = next(
        (
            row
            for row in periods
            if not cint(row.enabled)
            and _same_date(row.valid_from, start)
            and _same_date(row.valid_to, end)
        ),
        None,
    )
    if exact_disabled:
        return {
            "action": "enable",
            "name": exact_disabled.name,
            "school_branch": branch,
            "valid_from": str(start or ""),
            "valid_to": str(end or ""),
            "changed": True,
        }
    overlapping = next(
        (
            row
            for row in periods
            if cint(row.enabled) and _overlap(start, end, row.valid_from, row.valid_to)
        ),
        None,
    )
    if overlapping:
        return {
            "action": "extend",
            "name": overlapping.name,
            "school_branch": branch,
            "valid_from": str(start or ""),
            "valid_to": str(end or ""),
            "changed": True,
        }
    return {
        "action": "create",
        "name": None,
        "school_branch": branch,
        "valid_from": str(start or ""),
        "valid_to": str(end or ""),
        "changed": True,
    }


def _replacement_plan(source, replacement_instructor: str, handover_date: str | None, reason: str | None) -> dict:
    resolved_reason = _clean_reason(reason)
    handover = _handover_date(handover_date)
    incoming = _replacement_instructor(replacement_instructor, source)
    successor_start, successor_end = _successor_dates(source, handover)
    conflicts = _replacement_conflicts(source, incoming.name, successor_start, successor_end)
    branch_access = _branch_access_preview(incoming.name, source.school_branch, successor_start, successor_end)
    return {
        "source": {
            "name": source.name,
            "assignment_title": source.assignment_title,
            "instructor": source.instructor,
            "assignment_type": source.assignment_type,
            "assignment_scope": source.assignment_scope,
            "school_branch": source.school_branch,
            "program_offering": source.program_offering,
            "student_group": source.student_group,
            "course": source.course,
            "valid_from": str(source.valid_from or ""),
            "previous_valid_to": str(source.valid_to or ""),
            "final_valid_to": str(handover),
        },
        "successor": {
            "instructor": incoming.name,
            "instructor_name": incoming.instructor_name or incoming.name,
            "assignment_type": source.assignment_type,
            "assignment_scope": source.assignment_scope,
            "school_branch": source.school_branch,
            "program_offering": source.program_offering,
            "student_group": source.student_group,
            "course": source.course,
            "valid_from": str(successor_start),
            "valid_to": str(successor_end or ""),
        },
        "handover_date": str(handover),
        "reason": resolved_reason,
        "incoming_branch_eligibility": branch_access,
        "outgoing_branch_eligibility_changed": False,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


def _already_replaced(source, replacement_instructor: str, handover_date: str | None, reason: str | None) -> dict | None:
    if not source.replaced_by_assignment:
        return None
    resolved_reason = _clean_reason(reason)
    handover = getdate(handover_date or source.ended_on or nowdate())
    successor = frappe.get_doc("EduEdge Instructor Assignment", source.replaced_by_assignment)
    successor.check_permission("read")
    expected_start = getdate(add_days(handover, 1))
    if (
        source.ended_on
        and getdate(source.ended_on) == handover
        and str(source.end_reason or "").strip() == resolved_reason
        and successor.instructor == str(replacement_instructor or "").strip()
        and successor.replaces_assignment == source.name
        and str(successor.replacement_reason or "").strip() == resolved_reason
        and successor.valid_from
        and getdate(successor.valid_from) == expected_start
    ):
        return {
            "action": "already-replaced",
            "source_name": source.name,
            "successor_name": successor.name,
            "handover_date": str(source.ended_on),
            "successor_valid_from": str(successor.valid_from),
            "successor_valid_to": str(successor.valid_to or ""),
            "outgoing_branch_eligibility_changed": False,
        }
    frappe.throw(
        _("This Instructor Assignment was already replaced. Its replacement history will not be rewritten."),
        frappe.ValidationError,
    )


def _ensure_incoming_branch_access(instructor: str, branch: str, start, end) -> dict:
    preview = _branch_access_preview(instructor, branch, start, end)
    if preview["action"] == "existing":
        return preview
    result = _save_branch_period(
        instructor,
        branch,
        start,
        end,
        enabled=1,
        make_primary=False,
    )
    return {
        **result,
        "school_branch": branch,
        "changed": True,
    }


@frappe.whitelist(methods=["POST"])
def preview_instructor_assignment_replacement(
    name: str,
    replacement_instructor: str,
    handover_date: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_replacement")
    source = _source_assignment(name)
    if source.replaced_by_assignment:
        return {
            "already_replaced": True,
            "source_name": source.name,
            "successor_name": source.replaced_by_assignment,
        }
    if source.ended_on:
        frappe.throw(
            _("This Instructor Assignment has already ended and cannot be replaced."),
            frappe.ValidationError,
        )
    return _replacement_plan(source, replacement_instructor, handover_date, reason)


@frappe.whitelist(methods=["POST"])
def replace_instructor_assignment(
    name: str,
    replacement_instructor: str,
    handover_date: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="replace_instructor_assignment")
    if not frappe.has_permission("EduEdge Instructor Assignment", "create"):
        frappe.throw(_("You are not permitted to create the replacement Instructor Assignment."), frappe.PermissionError)

    savepoint = "eduedge_instructor_assignment_replace"
    frappe.db.savepoint(savepoint)
    try:
        assignment_name = str(name or "").strip()
        if not assignment_name:
            frappe.throw(_("Select an Instructor Assignment to replace."), frappe.ValidationError)
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (assignment_name,),
        )
        source = _source_assignment(assignment_name)
        existing = _already_replaced(source, replacement_instructor, handover_date, reason)
        if existing:
            return existing
        if source.ended_on:
            frappe.throw(
                _("This Instructor Assignment has already ended and cannot be replaced."),
                frappe.ValidationError,
            )

        plan = _replacement_plan(source, replacement_instructor, handover_date, reason)
        if plan["conflict_count"]:
            frappe.throw(
                _("Replacement plan has {0} conflict(s). Resolve them before saving.").format(plan["conflict_count"]),
                frappe.ValidationError,
            )

        handover = getdate(plan["handover_date"])
        successor_start = getdate(plan["successor"]["valid_from"])
        successor_end = getdate(plan["successor"]["valid_to"]) if plan["successor"]["valid_to"] else None
        resolved_reason = plan["reason"]

        source.valid_to = handover
        source.ended_on = handover
        source.ended_by = frappe.session.user
        source.end_reason = resolved_reason
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            source.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        branch_result = _ensure_incoming_branch_access(
            plan["successor"]["instructor"],
            source.school_branch,
            successor_start,
            successor_end,
        )

        successor = frappe.new_doc("EduEdge Instructor Assignment")
        successor.instructor = plan["successor"]["instructor"]
        successor.assignment_type = source.assignment_type
        successor.assignment_scope = source.assignment_scope
        successor.enabled = 1
        successor.school_branch = source.school_branch
        successor.program_offering = source.program_offering
        successor.student_group = source.student_group
        successor.course = source.course
        successor.valid_from = successor_start
        successor.valid_to = successor_end
        successor.replaces_assignment = source.name
        successor.replacement_reason = resolved_reason
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            successor.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        source.replaced_by_assignment = successor.name
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            source.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        source.add_comment(
            "Info",
            _("Instructor Assignment handed over. Final responsibility date: {0}. Successor: {1}. Reason: {2}").format(
                handover,
                successor.name,
                resolved_reason,
            ),
        )
        successor.add_comment(
            "Info",
            _("Created by Instructor Assignment replacement. Predecessor: {0}. Responsibility starts: {1}. Reason: {2}").format(
                source.name,
                successor_start,
                resolved_reason,
            ),
        )

        return {
            "action": "replaced",
            "source_name": source.name,
            "successor_name": successor.name,
            "handover_date": str(handover),
            "source_final_valid_to": str(source.valid_to),
            "successor_valid_from": str(successor.valid_from),
            "successor_valid_to": str(successor.valid_to or ""),
            "replacement_instructor": successor.instructor,
            "reason": resolved_reason,
            "incoming_branch_eligibility": branch_result,
            "outgoing_branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
