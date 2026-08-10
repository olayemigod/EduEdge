from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from eduedge.api.instructor_assignments import _can_manage_assignments, _require_assignment_manager
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access

ASSIGNMENT_DOCTYPE = "EduEdge Instructor Assignment"
GOVERNANCE_LOG_DOCTYPE = "EduEdge Instructor Assignment Governance Log"

OUTGOING_HISTORY_FIELDS = (
    "ended_on",
    "replaced_by_assignment",
    "transferred_to_assignment",
)
ANY_LIFECYCLE_FIELDS = (
    "ended_on",
    "ended_by",
    "end_reason",
    "replaces_assignment",
    "replaced_by_assignment",
    "replacement_reason",
    "transferred_from_assignment",
    "transferred_to_assignment",
    "transfer_reason",
    "prepared_from_assignment",
    "preparation_reason",
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
        frappe.throw(_("Request governance state for at most 500 Instructor Assignments at a time."), frappe.ValidationError)
    return values


def _clean_reason(reason: str | None, action: str) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(
            _("Give a short reason of at least 3 characters for {0}.").format(action),
            frappe.ValidationError,
        )
    return value


def _has_any(row, fields) -> bool:
    return any(row.get(fieldname) for fieldname in fields)


def _active_instructors(rows: list) -> set[str]:
    names = sorted({str(row.instructor or "").strip() for row in rows if str(row.instructor or "").strip()})
    if not names:
        return set()
    records = frappe.get_list(
        "Instructor",
        filters={"name": ["in", names], "status": "Active"},
        fields=["name"],
        limit_page_length=len(names),
    )
    return {row.name for row in records}


def _link_fields_to_assignment() -> list[tuple[str, str]]:
    fields = set()
    for field_doctype in ("DocField", "Custom Field"):
        try:
            rows = frappe.get_all(
                field_doctype,
                filters={"fieldtype": "Link", "options": ASSIGNMENT_DOCTYPE},
                fields=["parent", "fieldname"],
                limit_page_length=0,
            )
        except Exception:
            rows = []
        for row in rows:
            parent = str(row.parent or "").strip()
            fieldname = str(row.fieldname or "").strip()
            if parent and fieldname:
                fields.add((parent, fieldname))
    return sorted(fields)


def _incoming_references(names: list[str]) -> tuple[set[str], bool]:
    """Return assignment names referenced by any installed Link field.

    Delete is deliberately fail-closed: an unexpected metadata/table failure means
    no candidate is considered safe to delete until reference integrity can be proven.
    """
    candidates = set(names)
    if not candidates:
        return set(), True
    referenced = set()
    try:
        for parent, fieldname in _link_fields_to_assignment():
            meta = frappe.get_meta(parent)
            if meta.issingle:
                value = frappe.db.get_single_value(parent, fieldname)
                if value in candidates:
                    referenced.add(value)
                continue
            rows = frappe.get_all(
                parent,
                filters={fieldname: ["in", sorted(candidates)]},
                fields=["name", fieldname],
                limit_page_length=0,
            )
            for row in rows:
                value = row.get(fieldname)
                if value in candidates:
                    # A pathological self-link must still block deletion; normal
                    # lifecycle self-links are already rejected by the controller.
                    referenced.add(value)
        return referenced, True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "EduEdge Instructor Assignment delete reference scan failed")
        return set(candidates), False


def _disable_capability(row, today) -> tuple[bool, str]:
    if not cint(row.enabled):
        return False, _("Assignment is already disabled.")
    if _has_any(row, OUTGOING_HISTORY_FIELDS):
        return False, _("Historical End, Replace or Transfer records cannot be disabled.")
    if not row.valid_from or getdate(row.valid_from) <= today:
        return False, _("Started responsibilities must use End Assignment so academic history is preserved.")
    return True, ""


def _reenable_capability(row, today, active_instructors: set[str]) -> tuple[bool, str]:
    if cint(row.enabled):
        return False, _("Assignment is already enabled.")
    if _has_any(row, OUTGOING_HISTORY_FIELDS):
        return False, _("Historical End, Replace or Transfer records cannot be re-enabled.")
    if not row.valid_from or getdate(row.valid_from) <= today:
        return False, _("Only a future responsibility that has never started can be re-enabled.")
    if row.valid_to and getdate(row.valid_to) < today:
        return False, _("An expired assignment cannot be re-enabled.")
    if row.instructor not in active_instructors:
        return False, _("The Instructor must be active before this future responsibility can be re-enabled.")
    return True, ""


def _delete_capability(row, today, referenced: set[str], reference_scan_ok: bool) -> tuple[bool, str]:
    if cint(row.enabled):
        return False, _("Disable the unused future assignment before deleting it.")
    if not row.valid_from or getdate(row.valid_from) <= today:
        return False, _("Started or historical Instructor Assignments cannot be deleted.")
    if _has_any(row, ANY_LIFECYCLE_FIELDS):
        return False, _("Assignments with lifecycle or preparation history cannot be deleted.")
    if not reference_scan_ok:
        return False, _("EduEdge could not prove that this assignment is unreferenced, so deletion is blocked.")
    if row.name in referenced:
        return False, _("This assignment is referenced by another record and cannot be deleted.")
    return True, ""


def _governance_rows(names: list[str]) -> list:
    if not names:
        return []
    return frappe.get_list(
        ASSIGNMENT_DOCTYPE,
        filters={"name": ["in", names]},
        fields=[
            "name",
            "assignment_title",
            "instructor",
            "school_branch",
            "enabled",
            "valid_from",
            "valid_to",
            *ANY_LIFECYCLE_FIELDS,
        ],
        limit_page_length=len(names),
    )


def _state_payload(rows: list) -> dict:
    today = getdate(nowdate())
    can_manage = _can_manage_assignments()
    active_instructors = _active_instructors(rows) if can_manage else set()
    candidates = [row.name for row in rows if not cint(row.enabled) and row.valid_from and getdate(row.valid_from) > today]
    referenced, reference_scan_ok = _incoming_references(candidates) if can_manage else (set(), True)
    states = {}
    for row in rows:
        can_disable, disable_reason = _disable_capability(row, today) if can_manage else (False, "")
        can_reenable, reenable_reason = _reenable_capability(row, today, active_instructors) if can_manage else (False, "")
        can_delete, delete_reason = _delete_capability(row, today, referenced, reference_scan_ok) if can_manage else (False, "")
        states[row.name] = {
            "can_disable": can_disable,
            "disable_block_reason": disable_reason,
            "can_reenable": can_reenable,
            "reenable_block_reason": reenable_reason,
            "can_delete_unused": can_delete,
            "delete_block_reason": delete_reason,
            "delete_reference_scan_ok": reference_scan_ok,
        }
    return {"states": states}


@frappe.whitelist()
def get_instructor_assignment_governance_states(names: str | list | None = None) -> dict:
    assignment_names = _assignment_names(names)
    if not assignment_names:
        return {"states": {}}
    return _state_payload(_governance_rows(assignment_names))


def _source_doc(name: str, permission_type: str = "write"):
    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment."), frappe.ValidationError)
    doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, assignment_name)
    doc.check_permission(permission_type)
    assert_branch_access(doc.school_branch)
    return doc


def _record_governance_log(doc, action: str, reason: str) -> str:
    log = frappe.new_doc(GOVERNANCE_LOG_DOCTYPE)
    log.assignment_name = doc.name
    log.assignment_title = doc.assignment_title or doc.name
    log.instructor = doc.instructor
    log.school_branch = doc.school_branch
    log.action = action
    log.reason = reason
    log.acted_by = frappe.session.user
    log.acted_on = now_datetime()
    log.insert(ignore_permissions=True)
    return log.name


def _save_enabled(doc, enabled: int) -> None:
    doc.enabled = enabled
    frappe.flags.in_eduedge_assignment_lifecycle = True
    try:
        doc.save()
    finally:
        frappe.flags.in_eduedge_assignment_lifecycle = False


@frappe.whitelist(methods=["POST"])
def disable_instructor_assignment(name: str, reason: str | None = None) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="disable_instructor_assignment")
    resolved_reason = _clean_reason(reason, _("disabling this future assignment"))
    savepoint = "eduedge_instructor_assignment_disable"
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (str(name or "").strip(),),
        )
        doc = _source_doc(name, "write")
        if not cint(doc.enabled):
            return {"name": doc.name, "action": "already-disabled", "enabled": 0, "branch_eligibility_changed": False}
        allowed, block_reason = _disable_capability(doc, getdate(nowdate()))
        if not allowed:
            frappe.throw(block_reason, frappe.ValidationError)
        _save_enabled(doc, 0)
        log_name = _record_governance_log(doc, "Disable", resolved_reason)
        doc.add_comment(
            "Info",
            _("Future Instructor Assignment disabled. Reason: {0}").format(resolved_reason),
        )
        return {
            "name": doc.name,
            "action": "disabled",
            "enabled": 0,
            "reason": resolved_reason,
            "governance_log": log_name,
            "branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise


@frappe.whitelist(methods=["POST"])
def reenable_instructor_assignment(name: str, reason: str | None = None) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="reenable_instructor_assignment")
    resolved_reason = _clean_reason(reason, _("re-enabling this future assignment"))
    savepoint = "eduedge_instructor_assignment_reenable"
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (str(name or "").strip(),),
        )
        doc = _source_doc(name, "write")
        if cint(doc.enabled):
            return {"name": doc.name, "action": "already-enabled", "enabled": 1, "branch_eligibility_changed": False}
        active = frappe.db.get_value("Instructor", doc.instructor, "status") == "Active"
        allowed, block_reason = _reenable_capability(doc, getdate(nowdate()), {doc.instructor} if active else set())
        if not allowed:
            frappe.throw(block_reason, frappe.ValidationError)
        # Normal DocType validation is deliberately re-run here. Duplicate/primary
        # conflicts, active Instructor state, curriculum and Branch Eligibility must
        # all still be valid before a disabled future responsibility becomes active.
        _save_enabled(doc, 1)
        log_name = _record_governance_log(doc, "Re-enable", resolved_reason)
        doc.add_comment(
            "Info",
            _("Future Instructor Assignment re-enabled. Reason: {0}").format(resolved_reason),
        )
        return {
            "name": doc.name,
            "action": "re-enabled",
            "enabled": 1,
            "reason": resolved_reason,
            "governance_log": log_name,
            "branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise


@frappe.whitelist(methods=["POST"])
def delete_unused_instructor_assignment(name: str, reason: str | None = None) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="delete_unused_instructor_assignment")
    resolved_reason = _clean_reason(reason, _("deleting this unused future assignment"))
    savepoint = "eduedge_instructor_assignment_delete_unused"
    frappe.db.savepoint(savepoint)
    try:
        assignment_name = str(name or "").strip()
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (assignment_name,),
        )
        doc = _source_doc(assignment_name, "delete")
        referenced, scan_ok = _incoming_references([doc.name])
        allowed, block_reason = _delete_capability(doc, getdate(nowdate()), referenced, scan_ok)
        if not allowed:
            frappe.throw(block_reason, frappe.ValidationError)
        log_name = _record_governance_log(doc, "Delete", resolved_reason)
        title = doc.assignment_title or doc.name
        frappe.flags.in_eduedge_assignment_delete = True
        try:
            frappe.delete_doc(ASSIGNMENT_DOCTYPE, doc.name)
        finally:
            frappe.flags.in_eduedge_assignment_delete = False
        return {
            "name": assignment_name,
            "assignment_title": title,
            "action": "deleted-unused",
            "reason": resolved_reason,
            "governance_log": log_name,
            "branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
