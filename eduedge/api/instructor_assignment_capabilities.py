from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from eduedge.api.instructor_assignments import _can_manage_assignments, _require_assignment_manager
from eduedge.education.instructor_assignment_capabilities import (
    ASSIGNMENT_DOCTYPE,
    CAPABILITY_FIELDS,
    CAPABILITY_LABELS,
    get_instructor_assignment_capability_state,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access

CAPABILITY_AUDIT_FIELDS = (
    "capabilities_updated_on",
    "capabilities_updated_by",
    "capabilities_update_reason",
)


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
        frappe.throw(_("Request capability state for at most 500 Instructor Assignments at a time."), frappe.ValidationError)
    return values


def _clean_reason(reason: str | None) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(_("Give a short reason of at least 3 characters for changing assignment capabilities."), frappe.ValidationError)
    return value


def _parse_capabilities(value: str | dict | None) -> dict[str, int]:
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            value = None
    if not isinstance(value, dict):
        frappe.throw(_("Provide the assignment capabilities as a JSON object."), frappe.ValidationError)
    unknown = sorted(set(value) - set(CAPABILITY_FIELDS))
    if unknown:
        frappe.throw(
            _("Unsupported Instructor Assignment capability: {0}").format(", ".join(unknown)),
            frappe.ValidationError,
        )
    resolved = {fieldname: cint(value.get(fieldname)) for fieldname in CAPABILITY_FIELDS}
    if any(resolved[fieldname] for fieldname in CAPABILITY_FIELDS if fieldname != "can_view_subject_content") and not resolved["can_view_subject_content"]:
        frappe.throw(
            _("View Subject Content must be enabled before operational Subject capabilities can be granted."),
            frappe.ValidationError,
        )
    return resolved


def _can_manage_record(row, today) -> tuple[bool, str]:
    if not _can_manage_assignments():
        return False, ""
    if not cint(row.enabled):
        return False, _("Disabled assignments cannot grant operational capabilities.")
    if row.assignment_type not in COURSE_REQUIRED_TYPES or not row.course:
        return False, _("Only Subject-bearing Instructor Assignments can grant operational capabilities.")
    if row.ended_on or row.replaced_by_assignment or row.transferred_to_assignment:
        return False, _("Historical End, Replace or Transfer assignments cannot have capabilities changed.")
    if row.valid_to and getdate(row.valid_to) < today:
        return False, _("Expired Instructor Assignments cannot have capabilities changed.")
    return True, ""


def _admin_rows(names: list[str]) -> list:
    if not names:
        return []
    return frappe.get_list(
        ASSIGNMENT_DOCTYPE,
        filters={"name": ["in", names]},
        fields=[
            "name",
            "assignment_title",
            "assignment_type",
            "assignment_scope",
            "course",
            "school_branch",
            "program_offering",
            "student_group",
            "enabled",
            "valid_from",
            "valid_to",
            "ended_on",
            "replaced_by_assignment",
            "transferred_to_assignment",
            *CAPABILITY_FIELDS,
            *CAPABILITY_AUDIT_FIELDS,
        ],
        limit_page_length=len(names),
    )


@frappe.whitelist()
def get_instructor_assignment_capability_admin_states(names: str | list | None = None) -> dict:
    assignment_names = _assignment_names(names)
    if not assignment_names:
        return {"states": {}}
    rows = _admin_rows(assignment_names)
    today = getdate(nowdate())
    states = {}
    for row in rows:
        can_manage, block_reason = _can_manage_record(row, today)
        states[row.name] = {
            "can_manage_capabilities": can_manage,
            "capability_block_reason": block_reason,
            "capabilities": {fieldname: cint(row.get(fieldname)) for fieldname in CAPABILITY_FIELDS},
            "capabilities_updated_on": str(row.capabilities_updated_on or ""),
            "capabilities_updated_by": row.capabilities_updated_by or "",
            "capabilities_update_reason": row.capabilities_update_reason or "",
        }
    return {"states": states}


@frappe.whitelist()
def get_my_instructor_assignment_capabilities(
    school_branch: str,
    program_offering: str,
    course: str,
    student_group: str | None = None,
    on_date: str | None = None,
) -> dict:
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentication required."), frappe.PermissionError)
    require_eduedge_access(feature_key="academics", action="view_my_instructor_assignment_capabilities")
    return get_instructor_assignment_capability_state(
        user=frappe.session.user,
        school_branch=str(school_branch or "").strip(),
        program_offering=str(program_offering or "").strip(),
        course=str(course or "").strip(),
        student_group=str(student_group or "").strip(),
        on_date=on_date,
    )


@frappe.whitelist(methods=["POST"])
def update_instructor_assignment_capabilities(
    name: str,
    capabilities: str | dict,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="update_instructor_assignment_capabilities")
    resolved_reason = _clean_reason(reason)
    resolved_capabilities = _parse_capabilities(capabilities)
    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment."), frappe.ValidationError)

    savepoint = "eduedge_instructor_assignment_capabilities"
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (assignment_name,),
        )
        doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, assignment_name)
        doc.check_permission("write")
        assert_branch_access(doc.school_branch)
        allowed, block_reason = _can_manage_record(doc, getdate(nowdate()))
        if not allowed:
            frappe.throw(block_reason, frappe.ValidationError)

        before = {fieldname: cint(doc.get(fieldname)) for fieldname in CAPABILITY_FIELDS}
        if before == resolved_capabilities:
            return {
                "name": doc.name,
                "action": "already-configured",
                "capabilities": before,
                "branch_eligibility_changed": False,
            }

        for fieldname, value in resolved_capabilities.items():
            doc.set(fieldname, value)
        doc.capabilities_updated_on = now_datetime()
        doc.capabilities_updated_by = frappe.session.user
        doc.capabilities_update_reason = resolved_reason

        frappe.flags.in_eduedge_assignment_capability_update = True
        try:
            doc.save()
        finally:
            frappe.flags.in_eduedge_assignment_capability_update = False

        changed = [
            CAPABILITY_LABELS[fieldname]
            for fieldname in CAPABILITY_FIELDS
            if before.get(fieldname) != resolved_capabilities.get(fieldname)
        ]
        doc.add_comment(
            "Info",
            _("Instructor Assignment capabilities updated: {0}. Reason: {1}").format(
                ", ".join(changed) or _("No capability changes"),
                resolved_reason,
            ),
        )
        return {
            "name": doc.name,
            "assignment_title": doc.assignment_title,
            "action": "capabilities-updated",
            "capabilities": resolved_capabilities,
            "capabilities_updated_on": str(doc.capabilities_updated_on or ""),
            "capabilities_updated_by": doc.capabilities_updated_by or "",
            "capabilities_update_reason": doc.capabilities_update_reason or "",
            "branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
