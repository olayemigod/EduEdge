from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api.instructor_assignments import _require_assignment_manager
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
