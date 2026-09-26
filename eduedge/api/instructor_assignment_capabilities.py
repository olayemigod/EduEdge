from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from eduedge.api.instructor_assignments import _can_manage_assignments, _require_assignment_manager
from eduedge.education.instructor_assignment_capabilities import (
    ASSIGNMENT_DOCTYPE,
    CAPABILITY_FIELDS,
    CAPABILITY_LABELS,
    assignment_capability_enforcement_enabled,
    get_instructor_assignment_capability_state,
)
from eduedge.education.instructor_scope import (
    INSTRUCTOR_SCOPE_BYPASS_ROLES,
    LIMITED_INSTRUCTOR_ROLES,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import COURSE_REQUIRED_TYPES
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches
from eduedge.services.instructor_branch_governance import eligibility_covers_period

CAPABILITY_AUDIT_FIELDS = (
    "capabilities_updated_on",
    "capabilities_updated_by",
    "capabilities_update_reason",
)


GLOBAL_CAPABILITY_ADMIN_ROLES = {
    "System Manager",
    "EduEdge Super Administrator",
    "EduEdge Administrator",
}
READINESS_DETAIL_LIMIT = 100


def _capability_enforcement_has_full_scope(user: str | None = None) -> bool:
    resolved_user = user or frappe.session.user
    roles = set(frappe.get_roles(resolved_user))
    if roles.intersection(GLOBAL_CAPABILITY_ADMIN_ROLES):
        return True
    all_branches = set(
        frappe.get_all(
            "EduEdge School Branch",
            filters={"enabled": 1},
            pluck="name",
            limit_page_length=0,
        )
    )
    if not all_branches:
        return False
    allowed = {
        str(row.get("name") or "").strip()
        for row in get_allowed_school_branches(user=resolved_user)
        if str(row.get("name") or "").strip()
    }
    return all_branches == allowed


def _can_manage_capability_enforcement(user: str | None = None) -> bool:
    resolved_user = user or frappe.session.user
    if not resolved_user or resolved_user == "Guest":
        return False
    if not frappe.has_permission("EduEdge Settings", "write", user=resolved_user):
        return False
    return _capability_enforcement_has_full_scope(resolved_user)


def _require_capability_enforcement_admin() -> None:
    if not _can_manage_capability_enforcement():
        frappe.throw(
            _(
                "Changing Instructor Assignment Capability Enforcement requires EduEdge Settings write access and visibility across every enabled Branch / Campus."
            ),
            frappe.PermissionError,
        )


def _limited_instructor_user_rows() -> list[dict]:
    relevant_roles = sorted(set(LIMITED_INSTRUCTOR_ROLES).union(INSTRUCTOR_SCOPE_BYPASS_ROLES))
    role_rows = frappe.get_all(
        "Has Role",
        filters={"parenttype": "User", "role": ["in", relevant_roles]},
        fields=["parent", "role"],
        limit_page_length=0,
    )
    roles_by_user: dict[str, set[str]] = {}
    for row in role_rows:
        roles_by_user.setdefault(str(row.parent), set()).add(str(row.role))
    candidate_names = sorted(
        user
        for user, roles in roles_by_user.items()
        if roles.intersection(LIMITED_INSTRUCTOR_ROLES)
        and not roles.intersection(INSTRUCTOR_SCOPE_BYPASS_ROLES)
    )
    if not candidate_names:
        return []
    return [
        dict(row)
        for row in frappe.get_all(
            "User",
            filters={"name": ["in", candidate_names], "enabled": 1},
            fields=["name", "full_name"],
            order_by="full_name asc, name asc",
            limit_page_length=0,
        )
    ]


def _identity_readiness(users: list[dict]) -> tuple[dict[str, str], list[dict]]:
    user_names = [row["name"] for row in users if row.get("name")]
    if not user_names:
        return {}, []
    employees = frappe.get_all(
        "Employee",
        filters={"user_id": ["in", user_names], "status": "Active"},
        fields=["name", "employee_name", "user_id"],
        limit_page_length=0,
    )
    employees_by_user: dict[str, list] = {}
    for row in employees:
        employees_by_user.setdefault(str(row.user_id), []).append(row)

    employee_names = [row.name for row in employees if row.name]
    instructors = (
        frappe.get_all(
            "Instructor",
            filters={"employee": ["in", employee_names], "status": "Active"},
            fields=["name", "instructor_name", "employee"],
            limit_page_length=0,
        )
        if employee_names
        else []
    )
    employee_to_user = {row.name: str(row.user_id) for row in employees if row.name and row.user_id}
    instructors_by_user: dict[str, list] = {}
    for row in instructors:
        user = employee_to_user.get(row.employee)
        if user:
            instructors_by_user.setdefault(user, []).append(row)

    ready: dict[str, str] = {}
    blockers: list[dict] = []
    for user in users:
        name = str(user.get("name") or "")
        active_employees = employees_by_user.get(name, [])
        active_instructors = instructors_by_user.get(name, [])
        reason = ""
        if len(active_employees) == 0:
            reason = _("No active Employee is linked to this User.")
        elif len(active_employees) > 1:
            reason = _("More than one active Employee is linked to this User.")
        elif len(active_instructors) == 0:
            reason = _("No active Instructor is linked through this User's active Employee.")
        elif len(active_instructors) > 1:
            reason = _("More than one active Instructor resolves from this User.")
        if reason:
            blockers.append(
                {
                    "type": "identity",
                    "user": name,
                    "label": user.get("full_name") or name,
                    "reason": reason,
                    "active_employee_count": len(active_employees),
                    "active_instructor_count": len(active_instructors),
                }
            )
            continue
        ready[name] = active_instructors[0].name
    return ready, blockers


def _assignment_is_effective(row, today) -> bool:
    if row.get("valid_from") and getdate(row.get("valid_from")) > today:
        return False
    if row.get("valid_to") and getdate(row.get("valid_to")) < today:
        return False
    return True


def _capability_enforcement_readiness() -> dict:
    users = _limited_instructor_user_rows()
    ready_identity, identity_blockers = _identity_readiness(users)
    instructor_names = sorted(set(ready_identity.values()))
    assignments = (
        frappe.get_all(
            ASSIGNMENT_DOCTYPE,
            filters={
                "instructor": ["in", instructor_names],
                "assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
                "enabled": 1,
            },
            fields=[
                "name",
                "assignment_title",
                "instructor",
                "school_branch",
                "program_offering",
                "student_group",
                "course",
                "valid_from",
                "valid_to",
                *CAPABILITY_AUDIT_FIELDS,
                *CAPABILITY_FIELDS,
            ],
            order_by="school_branch asc, instructor asc, valid_from asc",
            limit_page_length=0,
        )
        if instructor_names
        else []
    )
    today = getdate(nowdate())
    current_rows = []
    scheduled_rows = []
    governance_blockers = []
    unreviewed_blockers = []
    future_unreviewed = []
    eligibility_cache: dict[tuple[str, str], bool] = {}

    for source in assignments:
        row = dict(source)
        if row.get("valid_to") and getdate(row.get("valid_to")) < today:
            continue
        if row.get("valid_from") and getdate(row.get("valid_from")) > today:
            scheduled_rows.append(row)
            if not row.get("capabilities_updated_on"):
                future_unreviewed.append(
                    {
                        "type": "future-unreviewed",
                        "assignment": row.get("name"),
                        "label": row.get("assignment_title") or row.get("name"),
                        "school_branch": row.get("school_branch"),
                        "valid_from": str(row.get("valid_from") or ""),
                        "reason": _("Future Subject responsibility has not had its capabilities explicitly reviewed."),
                    }
                )
            continue
        if not _assignment_is_effective(row, today):
            continue
        current_rows.append(row)
        eligibility_key = (str(row.get("instructor") or ""), str(row.get("school_branch") or ""))
        if eligibility_key not in eligibility_cache:
            eligibility_cache[eligibility_key] = eligibility_covers_period(
                eligibility_key[0],
                eligibility_key[1],
                today,
                today,
            )
        if not eligibility_cache[eligibility_key]:
            governance_blockers.append(
                {
                    "type": "branch-eligibility",
                    "assignment": row.get("name"),
                    "label": row.get("assignment_title") or row.get("name"),
                    "instructor": row.get("instructor"),
                    "school_branch": row.get("school_branch"),
                    "reason": _("Current Subject responsibility is not covered by effective Instructor Branch Eligibility."),
                }
            )
        if not row.get("capabilities_updated_on"):
            unreviewed_blockers.append(
                {
                    "type": "capability-review",
                    "assignment": row.get("name"),
                    "label": row.get("assignment_title") or row.get("name"),
                    "instructor": row.get("instructor"),
                    "school_branch": row.get("school_branch"),
                    "course": row.get("course"),
                    "reason": _("Current Subject responsibility has not had its capabilities explicitly reviewed."),
                }
            )

    blockers = [*identity_blockers, *governance_blockers, *unreviewed_blockers]
    warnings = future_unreviewed
    return {
        "enabled": assignment_capability_enforcement_enabled(),
        "ready": not blockers,
        "can_manage": _can_manage_capability_enforcement(),
        "counts": {
            "limited_instructor_users": len(users),
            "identity_ready_users": len(ready_identity),
            "identity_blockers": len(identity_blockers),
            "current_subject_assignments": len(current_rows),
            "current_unreviewed_assignments": len(unreviewed_blockers),
            "current_branch_eligibility_blockers": len(governance_blockers),
            "future_subject_assignments": len(scheduled_rows),
            "future_unreviewed_assignments": len(future_unreviewed),
        },
        "blockers": blockers[:READINESS_DETAIL_LIMIT],
        "warnings": warnings[:READINESS_DETAIL_LIMIT],
        "details_truncated": len(blockers) > READINESS_DETAIL_LIMIT or len(warnings) > READINESS_DETAIL_LIMIT,
        "manage_route": "/app/eduedge-instructor-assignments",
    }


def get_capability_enforcement_settings_summary() -> dict:
    """Return Settings Center-safe status without leaking global readiness details."""
    enabled = assignment_capability_enforcement_enabled()
    if not _can_manage_capability_enforcement():
        return {
            "enabled": enabled,
            "ready": False,
            "can_manage": False,
            "counts": {},
            "blockers": [],
            "warnings": [],
            "details_truncated": False,
            "manage_route": "/app/eduedge-instructor-assignments",
        }
    return _capability_enforcement_readiness()


@frappe.whitelist()
def get_instructor_assignment_capability_enforcement_readiness() -> dict:
    _require_capability_enforcement_admin()
    require_eduedge_access(
        feature_key="academics",
        action="view_instructor_assignment_capability_enforcement_readiness",
    )
    return _capability_enforcement_readiness()


@frappe.whitelist(methods=["POST"])
def set_instructor_assignment_capability_enforcement(
    enabled: int | str,
    confirmed: int | str = 0,
) -> dict:
    _require_capability_enforcement_admin()
    require_eduedge_access(
        feature_key="academics",
        action="set_instructor_assignment_capability_enforcement",
    )
    if not cint(confirmed):
        frappe.throw(
            _("Confirm the Instructor Assignment capability enforcement change before continuing."),
            frappe.ValidationError,
        )
    target = bool(cint(enabled))
    current = assignment_capability_enforcement_enabled()
    readiness = _capability_enforcement_readiness()
    if target and not readiness.get("ready"):
        counts = readiness.get("counts") or {}
        frappe.throw(
            _(
                "Capability enforcement cannot be enabled until readiness blockers are resolved. Identity blockers: {0}; unreviewed current Subject assignments: {1}; Branch Eligibility blockers: {2}."
            ).format(
                counts.get("identity_blockers", 0),
                counts.get("current_unreviewed_assignments", 0),
                counts.get("current_branch_eligibility_blockers", 0),
            ),
            frappe.ValidationError,
        )
    if current == target:
        return readiness

    settings = frappe.get_single("EduEdge Settings")
    settings.check_permission("write")
    settings.enforce_instructor_assignment_capabilities = int(target)
    frappe.flags.in_eduedge_capability_enforcement_change = True
    try:
        settings.save()
    finally:
        frappe.flags.in_eduedge_capability_enforcement_change = False
    return _capability_enforcement_readiness()


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
            "modified",
            *CAPABILITY_FIELDS,
            *CAPABILITY_AUDIT_FIELDS,
        ],
        limit_page_length=len(names),
    )


@frappe.whitelist()
def get_instructor_assignment_capability_admin_states(names: str | list | None = None) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="view_instructor_assignment_capability_admin_states")
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
            "capability_version": str(row.modified or ""),
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
    expected_modified: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="update_instructor_assignment_capabilities")
    resolved_reason = _clean_reason(reason)
    resolved_capabilities = _parse_capabilities(capabilities)
    assignment_name = str(name or "").strip()
    expected_version = str(expected_modified or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment."), frappe.ValidationError)
    if not expected_version:
        frappe.throw(_("Refresh the Instructor Assignment before changing capabilities."), frappe.ValidationError)

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
        if str(doc.modified or "") != expected_version:
            frappe.throw(
                _("This Instructor Assignment changed after its capabilities were loaded. Refresh the register and review the latest values before saving."),
                frappe.ValidationError,
            )
        allowed, block_reason = _can_manage_record(doc, getdate(nowdate()))
        if not allowed:
            frappe.throw(block_reason, frappe.ValidationError)

        before = {fieldname: cint(doc.get(fieldname)) for fieldname in CAPABILITY_FIELDS}
        if before == resolved_capabilities and doc.capabilities_updated_on:
            return {
                "name": doc.name,
                "action": "already-configured",
                "capabilities": before,
                "capability_version": str(doc.modified or ""),
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
        reviewed_without_value_change = not changed
        if reviewed_without_value_change:
            audit_message = _(
                "Instructor Assignment capabilities reviewed: explicitly reviewed with no capability grants. Reason: {0}"
            ).format(resolved_reason)
        else:
            audit_message = _(
                "Instructor Assignment capabilities updated: {0}. Reason: {1}"
            ).format(", ".join(changed), resolved_reason)
        doc.add_comment("Info", audit_message)
        return {
            "name": doc.name,
            "assignment_title": doc.assignment_title,
            "action": "capabilities-reviewed" if reviewed_without_value_change else "capabilities-updated",
            "capabilities": resolved_capabilities,
            "capability_version": str(doc.modified or ""),
            "capabilities_updated_on": str(doc.capabilities_updated_on or ""),
            "capabilities_updated_by": doc.capabilities_updated_by or "",
            "capabilities_update_reason": doc.capabilities_update_reason or "",
            "branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
