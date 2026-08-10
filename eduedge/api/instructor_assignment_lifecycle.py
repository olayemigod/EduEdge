from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.api.instructor_assignments import _can_manage_assignments, _require_assignment_manager
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access


def _clean_reason(reason: str | None) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(
            _("Give a short reason for ending this Instructor Assignment."),
            frappe.ValidationError,
        )
    return value


def _end_date(value: str | None):
    resolved = getdate(value or nowdate())
    today = getdate(nowdate())
    if resolved < today:
        frappe.throw(
            _("End Date cannot be earlier than today. Historical assignment periods are not backdated through this action."),
            frappe.ValidationError,
        )
    return resolved


def _assignment_names(names: str | list | tuple | None) -> list[str]:
    if isinstance(names, str):
        try:
            parsed = frappe.parse_json(names)
            names = parsed if isinstance(parsed, list) else [names]
        except Exception:
            names = [names]
    if not isinstance(names, (list, tuple)):
        return []
    values = list(dict.fromkeys(str(value or "").strip() for value in names if str(value or "").strip()))
    if len(values) > 500:
        frappe.throw(_("Request lifecycle state for at most 500 Instructor Assignments at a time."), frappe.ValidationError)
    return values


def _lifecycle_status(row, today) -> str:
    if not cint(row.enabled):
        return "Disabled"
    if row.replaced_by_assignment:
        return "Replaced"
    if row.transferred_to_assignment:
        return "Transferred"
    if row.ended_on:
        return "Ended"
    if row.valid_from and getdate(row.valid_from) > today:
        return "Scheduled"
    if row.valid_to and getdate(row.valid_to) < today:
        return "Ended"
    return "Current"


def _readable_instructor_from_assignment(row) -> str:
    title = str(row.assignment_title or "").strip()
    if title:
        first = title.split(" · ", 1)[0].strip()
        if first:
            return first
    return _("Instructor")


def _relation_summaries(rows: list) -> dict[str, dict]:
    """Return permission-scoped readable relationship summaries.

    Relationship enrichment must never be required to calculate lifecycle state.
    Keep internal assignment keys for navigation only; visible labels come from the
    assignment title and other readable business fields.
    """
    relation_names = sorted(
        {
            str(name or "").strip()
            for row in rows
            for name in (
                row.replaced_by_assignment,
                row.replaces_assignment,
                row.transferred_to_assignment,
                row.transferred_from_assignment,
            )
            if str(name or "").strip()
        }
    )
    if not relation_names:
        return {}
    relations = frappe.get_list(
        "EduEdge Instructor Assignment",
        filters={"name": ["in", relation_names]},
        fields=[
            "name",
            "assignment_title",
            "instructor",
            "valid_from",
            "valid_to",
        ],
        limit_page_length=len(relation_names),
    )
    return {
        row.name: {
            "name": row.name,
            "assignment_title": row.assignment_title or "",
            "instructor_name": _readable_instructor_from_assignment(row),
            "valid_from": str(row.valid_from or ""),
            "valid_to": str(row.valid_to or ""),
        }
        for row in relations
    }


@frappe.whitelist()
def get_instructor_assignment_lifecycle_states(names: str | list | None = None) -> dict:
    """Return permission-scoped effective/lifecycle state for assignment register rows."""
    assignment_names = _assignment_names(names)
    if not assignment_names:
        return {"states": {}}

    rows = frappe.get_list(
        "EduEdge Instructor Assignment",
        filters={"name": ["in", assignment_names]},
        fields=[
            "name",
            "enabled",
            "valid_from",
            "valid_to",
            "ended_on",
            "ended_by",
            "end_reason",
            "replaced_by_assignment",
            "replaces_assignment",
            "replacement_reason",
            "transferred_from_assignment",
            "transferred_to_assignment",
            "transfer_reason",
        ],
        limit_page_length=len(assignment_names),
    )

    # Relationship labels are useful display enrichment, but must never take down
    # authoritative lifecycle status or action capability for otherwise readable rows.
    relation_enrichment_available = True
    try:
        relations = _relation_summaries(rows)
    except Exception:
        relations = {}
        relation_enrichment_available = False
        frappe.log_error(
            frappe.get_traceback(),
            "EduEdge Instructor Assignment relationship enrichment failed",
        )

    today = getdate(nowdate())
    can_manage = _can_manage_assignments()
    states = {}
    for row in rows:
        status = _lifecycle_status(row, today)
        has_successor_period = not row.valid_to or getdate(row.valid_to) > today
        can_end = bool(
            can_manage
            and status == "Current"
            and not row.ended_on
            and not row.replaced_by_assignment
            and not row.transferred_to_assignment
        )
        can_successor_action = bool(can_end and has_successor_period)
        states[row.name] = {
            "lifecycle_status": status,
            "can_end": can_end,
            "can_replace": can_successor_action,
            "can_transfer": can_successor_action,
            "ended_on": str(row.ended_on or ""),
            "ended_by": row.ended_by or "",
            "end_reason": row.end_reason or "",
            "replaced_by_assignment": row.replaced_by_assignment or "",
            "replaced_by": relations.get(row.replaced_by_assignment or ""),
            "replaces_assignment": row.replaces_assignment or "",
            "replaces": relations.get(row.replaces_assignment or ""),
            "replacement_reason": row.replacement_reason or "",
            "transferred_to_assignment": row.transferred_to_assignment or "",
            "transferred_to": relations.get(row.transferred_to_assignment or ""),
            "transferred_from_assignment": row.transferred_from_assignment or "",
            "transferred_from": relations.get(row.transferred_from_assignment or ""),
            "transfer_reason": row.transfer_reason or "",
            "relation_enrichment_available": relation_enrichment_available,
        }
    return {"states": states}


@frappe.whitelist(methods=["POST"])
def end_instructor_assignment(
    name: str,
    end_date: str | None = None,
    reason: str | None = None,
) -> dict:
    """End one exact academic responsibility without deleting or disabling its history.

    End Date is the final day on which the responsibility remains valid. Branch
    eligibility is intentionally not changed here because it is an independent
    employment/access layer and may support other responsibilities.
    """
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="end_instructor_assignment")

    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment to end."), frappe.ValidationError)

    doc = frappe.get_doc("EduEdge Instructor Assignment", assignment_name)
    doc.check_permission("write")
    assert_branch_access(doc.school_branch)

    resolved_reason = _clean_reason(reason)
    resolved_end = _end_date(end_date)
    today = getdate(nowdate())

    if not doc.enabled:
        frappe.throw(
            _("Disabled Instructor Assignments cannot be ended. Re-enable or manage the disabled assignment separately."),
            frappe.ValidationError,
        )
    if doc.valid_from and getdate(doc.valid_from) > today:
        frappe.throw(
            _("This Instructor Assignment has not started yet. Scheduled assignments should be disabled or replaced rather than ended."),
            frappe.ValidationError,
        )
    if doc.valid_from and resolved_end < getdate(doc.valid_from):
        frappe.throw(
            _("End Date cannot be earlier than Valid From."),
            frappe.ValidationError,
        )
    if doc.valid_to and getdate(doc.valid_to) < today:
        frappe.throw(
            _("This Instructor Assignment has already ended by its validity period and will not be rewritten."),
            frappe.ValidationError,
        )
    if doc.valid_to and resolved_end > getdate(doc.valid_to):
        frappe.throw(
            _("End Assignment can shorten an existing validity period but cannot extend it."),
            frappe.ValidationError,
        )

    if doc.ended_on:
        same_date = getdate(doc.ended_on) == resolved_end
        same_reason = str(doc.end_reason or "").strip() == resolved_reason
        if same_date and same_reason:
            return {
                "name": doc.name,
                "action": "already-ended",
                "ended_on": str(doc.ended_on),
                "ended_by": doc.ended_by,
                "end_reason": doc.end_reason,
                "branch_eligibility_changed": False,
            }
        frappe.throw(
            _("This Instructor Assignment already has an End lifecycle action. Use a later lifecycle action instead of rewriting its history."),
            frappe.ValidationError,
        )

    previous_valid_to = doc.valid_to
    doc.valid_to = resolved_end
    doc.ended_on = resolved_end
    doc.ended_by = frappe.session.user
    doc.end_reason = resolved_reason

    frappe.flags.in_eduedge_assignment_lifecycle = True
    try:
        doc.save()
    finally:
        frappe.flags.in_eduedge_assignment_lifecycle = False

    doc.add_comment(
        "Info",
        _("Instructor Assignment ended. Final responsibility date: {0}. Reason: {1}").format(
            resolved_end,
            resolved_reason,
        ),
    )

    return {
        "name": doc.name,
        "action": "ended",
        "previous_valid_to": str(previous_valid_to or ""),
        "ended_on": str(doc.ended_on),
        "ended_by": doc.ended_by,
        "end_reason": doc.end_reason,
        "enabled": doc.enabled,
        "branch_eligibility_changed": False,
    }