from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from eduedge.api.instructor_assignment_replacement import (
    _branch_access_preview,
    _ensure_incoming_branch_access,
    _overlap,
    _type_variants,
)
from eduedge.api.instructor_assignments import _period_dates, _require_assignment_manager
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
    CLASS_ARM_SCOPE,
    CLASS_RESPONSIBILITY_TYPES,
    COURSE_REQUIRED_TYPES,
    LEGACY_SUBJECT_TEACHER,
    SUBJECT_INSTRUCTOR,
    UNIQUE_PRIMARY_ASSIGNMENT_TYPES,
)
from eduedge.platform.access import require_eduedge_access


def _clean_reason(reason: str | None) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(
            _("Give a short reason for transferring this Instructor Assignment."),
            frappe.ValidationError,
        )
    return value


def _transfer_date(value: str | None):
    resolved = getdate(value or nowdate())
    today = getdate(nowdate())
    if resolved < today:
        frappe.throw(
            _("Transfer Date cannot be earlier than today. Historical responsibility is not backdated through this action."),
            frappe.ValidationError,
        )
    return resolved


def _source_assignment(name: str):
    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment to transfer."), frappe.ValidationError)
    doc = frappe.get_doc("EduEdge Instructor Assignment", assignment_name)
    doc.check_permission("write")
    assert_branch_access(doc.school_branch)
    return doc


def _normalise_type(value: str | None) -> str:
    return SUBJECT_INSTRUCTOR if str(value or "") == LEGACY_SUBJECT_TEACHER else str(value or "")


def _source_transfer_window(source, transfer):
    today = getdate(nowdate())
    if not cint(source.enabled):
        frappe.throw(
            _("Disabled Instructor Assignments cannot be transferred through the active Transfer action."),
            frappe.ValidationError,
        )
    if source.replaced_by_assignment:
        frappe.throw(
            _("This Instructor Assignment was already replaced and cannot also be transferred."),
            frappe.ValidationError,
        )
    if source.ended_on:
        frappe.throw(
            _("This Instructor Assignment already has an End lifecycle action."),
            frappe.ValidationError,
        )
    if source.valid_from and getdate(source.valid_from) > today:
        frappe.throw(
            _("This Instructor Assignment has not started yet. Scheduled responsibilities need a separate planned move action."),
            frappe.ValidationError,
        )
    if source.valid_to and getdate(source.valid_to) < today:
        frappe.throw(
            _("This Instructor Assignment has already ended by its validity period and will not be rewritten."),
            frappe.ValidationError,
        )
    if source.valid_from and transfer < getdate(source.valid_from):
        frappe.throw(_("Transfer Date cannot be earlier than Valid From."), frappe.ValidationError)
    if source.valid_to and transfer > getdate(source.valid_to):
        frappe.throw(
            _("Transfer Date cannot be later than the outgoing assignment Valid To date."),
            frappe.ValidationError,
        )

    source_period_start, source_period_end = _period_dates(source.academic_year, source.academic_term)
    if source_period_start and source.valid_from and getdate(source.valid_from) < getdate(source_period_start):
        frappe.throw(
            _("The outgoing assignment starts before its academic period. Correct that record before transferring it."),
            frappe.ValidationError,
        )
    if source_period_end and source.valid_to and getdate(source.valid_to) > getdate(source_period_end):
        frappe.throw(
            _("The outgoing assignment extends beyond its academic period. Correct that record before transferring it."),
            frappe.ValidationError,
        )
    return getdate(add_days(transfer, 1))


def _destination_context(
    source,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None,
    destination_course: str | None,
    successor_start,
) -> dict:
    branch_name = str(destination_branch or "").strip()
    offering_name = str(destination_program_offering or "").strip()
    group_name = str(destination_student_group or "").strip() or None
    course_name = str(destination_course or "").strip() or None

    if not branch_name:
        frappe.throw(_("Select the destination Branch / Campus."), frappe.ValidationError)
    if not offering_name:
        frappe.throw(_("Select the destination Class / Programme Offering."), frappe.ValidationError)

    assert_branch_access(branch_name)
    branch = frappe.get_doc("EduEdge School Branch", branch_name)
    branch.check_permission("read")
    if not cint(branch.enabled):
        frappe.throw(_("Select an active destination Branch / Campus."), frappe.ValidationError)

    offering = frappe.get_doc("EduEdge Program Offering", offering_name)
    offering.check_permission("read")
    if not cint(offering.is_active):
        frappe.throw(_("Select an active destination Class / Programme Offering."), frappe.ValidationError)
    if offering.school_branch != branch_name:
        frappe.throw(
            _("Destination Class / Programme Offering must belong to the selected Branch."),
            frappe.ValidationError,
        )
    if branch.institution and offering.institution != branch.institution:
        frappe.throw(
            _("Destination Class / Programme Offering must belong to the selected Institution."),
            frappe.ValidationError,
        )

    period_start, period_end = _period_dates(offering.academic_year, offering.academic_term)
    if period_start and successor_start < getdate(period_start):
        frappe.throw(
            _("Transferred responsibility cannot start before the destination Class academic period."),
            frappe.ValidationError,
        )
    if period_end and successor_start > getdate(period_end):
        frappe.throw(
            _("Transferred responsibility would start after the destination Class academic period."),
            frappe.ValidationError,
        )

    assignment_type = _normalise_type(source.assignment_type)
    if source.assignment_scope == CLASS_ARM_SCOPE:
        if not group_name:
            frappe.throw(
                _("Select the destination Class Arm / Student Group."),
                frappe.ValidationError,
            )
        group = frappe.get_doc("Student Group", group_name)
        group.check_permission("read")
        if cint(group.disabled):
            frappe.throw(_("Select an active destination Class Arm / Student Group."), frappe.ValidationError)
        if group.get(BRANCH_FIELD) != branch_name:
            frappe.throw(
                _("Destination Class Arm / Student Group must belong to the selected Branch."),
                frappe.ValidationError,
            )
        if group.program and group.program != offering.program:
            frappe.throw(
                _("Destination Class Arm / Student Group Programme must match the selected Class."),
                frappe.ValidationError,
            )
        if group.academic_year and group.academic_year != offering.academic_year:
            frappe.throw(
                _("Destination Class Arm Academic Session must match the selected Class."),
                frappe.ValidationError,
            )
        if group.academic_term and group.academic_term != offering.academic_term:
            frappe.throw(
                _("Destination Class Arm Term must match the selected Class."),
                frappe.ValidationError,
            )
        group_meta = frappe.get_meta("Student Group")
        if group_meta.has_field(OFFERING_FIELD) and group.get(OFFERING_FIELD) and group.get(OFFERING_FIELD) != offering.name:
            frappe.throw(
                _("Destination Class Arm / Student Group must belong to the selected Class / Programme Offering."),
                frappe.ValidationError,
            )
    else:
        if group_name:
            frappe.throw(
                _("Class / Programme Offering scope cannot carry a destination Class Arm."),
                frappe.ValidationError,
            )
        group = None
        group_name = None

    if assignment_type in COURSE_REQUIRED_TYPES:
        if not course_name:
            frappe.throw(_("Select the destination Subject / Course."), frappe.ValidationError)
        course = frappe.get_doc("Course", course_name)
        course.check_permission("read")
        course_meta = frappe.get_meta("Course")
        course_institution = course.get(INSTITUTION_FIELD) if course_meta.has_field(INSTITUTION_FIELD) else None
        if course_institution and course_institution != offering.institution:
            frappe.throw(
                _("Destination Subject / Course must belong to the selected Institution."),
                frappe.ValidationError,
            )
        if not frappe.db.exists(
            "Program Course",
            {"parent": offering.program, "parenttype": "Program", "course": course_name},
        ):
            frappe.throw(
                _("Destination Subject / Course is not configured for the selected Class / Programme Offering."),
                frappe.ValidationError,
            )
    else:
        if course_name or assignment_type in CLASS_RESPONSIBILITY_TYPES and course_name:
            frappe.throw(
                _("This class responsibility cannot carry a destination Subject / Course."),
                frappe.ValidationError,
            )
        course = None
        course_name = None

    source_identity = (
        source.school_branch or "",
        source.program_offering or "",
        source.student_group or "",
        source.course or "",
    )
    destination_identity = (branch_name, offering.name, group_name or "", course_name or "")
    if destination_identity == source_identity:
        frappe.throw(
            _("Transfer destination must differ from the current academic responsibility."),
            frappe.ValidationError,
        )

    end_candidates = []
    if source.valid_to:
        end_candidates.append(getdate(source.valid_to))
    if period_end:
        end_candidates.append(getdate(period_end))
    successor_end = min(end_candidates) if end_candidates else None
    if successor_end and successor_start > successor_end:
        frappe.throw(
            _("No responsibility period remains in the destination after the Transfer Date."),
            frappe.ValidationError,
        )

    instructor = frappe.get_doc("Instructor", source.instructor)
    instructor.check_permission("read")
    if str(instructor.status or "") != "Active":
        frappe.throw(_("The Instructor must remain active to transfer this responsibility."), frappe.ValidationError)

    return {
        "instructor": source.instructor,
        "instructor_name": instructor.instructor_name or source.instructor,
        "assignment_type": assignment_type,
        "assignment_scope": source.assignment_scope,
        "institution": offering.institution,
        "school_branch": branch_name,
        "branch_name": branch.branch_name or branch_name,
        "program_offering": offering.name,
        "offering_title": offering.offering_title or offering.name,
        "academic_year": offering.academic_year,
        "academic_term": offering.academic_term,
        "student_group": group_name,
        "student_group_name": (
            (group.get("eduedge_display_name") if frappe.get_meta("Student Group").has_field("eduedge_display_name") else None)
            or (group.student_group_name if group else None)
            or ""
        ),
        "course": course_name,
        "course_name": (course.course_name if course else None) or "",
        "valid_from": str(successor_start),
        "valid_to": str(successor_end or ""),
    }


def _destination_conflicts(source, destination: dict, successor_start, successor_end) -> list[dict]:
    conflicts: list[dict] = []
    records = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "instructor": source.instructor,
            "school_branch": destination["school_branch"],
            "program_offering": destination["program_offering"],
            "assignment_scope": source.assignment_scope,
            "assignment_type": ["in", _type_variants(_normalise_type(source.assignment_type))],
            "enabled": 1,
            "name": ["!=", source.name],
        },
        fields=["name", "assignment_title", "student_group", "course", "valid_from", "valid_to"],
        limit_page_length=0,
    )
    for row in records:
        if (row.student_group or "") != (destination.get("student_group") or ""):
            continue
        if (row.course or "") != (destination.get("course") or ""):
            continue
        if _overlap(successor_start, successor_end, row.valid_from, row.valid_to):
            conflicts.append(
                {
                    "name": row.name,
                    "assignment_title": row.assignment_title or "",
                    "type": "transferring-instructor-overlap",
                    "reason": _("Instructor already has an overlapping exact responsibility in the destination context."),
                }
            )

    assignment_type = _normalise_type(source.assignment_type)
    if assignment_type in UNIQUE_PRIMARY_ASSIGNMENT_TYPES:
        filters = {
            "school_branch": destination["school_branch"],
            "program_offering": destination["program_offering"],
            "assignment_scope": source.assignment_scope,
            "assignment_type": assignment_type,
            "enabled": 1,
            "name": ["!=", source.name],
        }
        if source.assignment_scope == CLASS_ARM_SCOPE:
            filters["student_group"] = destination.get("student_group")
        records = frappe.get_all(
            "EduEdge Instructor Assignment",
            filters=filters,
            fields=["name", "assignment_title", "instructor", "valid_from", "valid_to"],
            limit_page_length=0,
        )
        for row in records:
            if _overlap(successor_start, successor_end, row.valid_from, row.valid_to):
                conflicts.append(
                    {
                        "name": row.name,
                        "assignment_title": row.assignment_title or "",
                        "type": "primary-responsibility-overlap",
                        "other_instructor": row.instructor,
                        "reason": _("Another Instructor already owns this primary responsibility in the destination period."),
                    }
                )
    return conflicts


def _transfer_plan(
    source,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None,
    destination_course: str | None,
    transfer_date: str | None,
    reason: str | None,
) -> dict:
    resolved_reason = _clean_reason(reason)
    transfer = _transfer_date(transfer_date)
    successor_start = _source_transfer_window(source, transfer)
    destination = _destination_context(
        source,
        destination_branch,
        destination_program_offering,
        destination_student_group,
        destination_course,
        successor_start,
    )
    successor_end = getdate(destination["valid_to"]) if destination["valid_to"] else None
    conflicts = _destination_conflicts(source, destination, successor_start, successor_end)
    branch_access = _branch_access_preview(
        source.instructor,
        destination["school_branch"],
        successor_start,
        successor_end,
    )
    branch_access.update(
        {
            "instructor": source.instructor,
            "instructor_name": destination["instructor_name"],
            "branch_name": destination["branch_name"],
        }
    )
    return {
        "source": {
            "name": source.name,
            "assignment_title": source.assignment_title,
            "instructor": source.instructor,
            "instructor_name": source.instructor_name or source.instructor,
            "assignment_type": source.assignment_type,
            "assignment_scope": source.assignment_scope,
            "school_branch": source.school_branch,
            "program_offering": source.program_offering,
            "student_group": source.student_group,
            "course": source.course,
            "valid_from": str(source.valid_from or ""),
            "previous_valid_to": str(source.valid_to or ""),
            "final_valid_to": str(transfer),
        },
        "destination": destination,
        "transfer_date": str(transfer),
        "reason": resolved_reason,
        "destination_branch_eligibility": branch_access,
        "source_branch_eligibility_changed": False,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


def _already_transferred(
    source,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None,
    destination_course: str | None,
    transfer_date: str | None,
    reason: str | None,
) -> dict | None:
    if not source.transferred_to_assignment:
        return None
    resolved_reason = _clean_reason(reason)
    transfer = getdate(transfer_date or source.ended_on or nowdate())
    successor = frappe.get_doc("EduEdge Instructor Assignment", source.transferred_to_assignment)
    successor.check_permission("read")
    expected_start = getdate(add_days(transfer, 1))
    if (
        source.ended_on
        and getdate(source.ended_on) == transfer
        and str(source.end_reason or "").strip() == resolved_reason
        and successor.instructor == source.instructor
        and successor.transferred_from_assignment == source.name
        and str(successor.transfer_reason or "").strip() == resolved_reason
        and successor.school_branch == str(destination_branch or "").strip()
        and successor.program_offering == str(destination_program_offering or "").strip()
        and (successor.student_group or "") == (str(destination_student_group or "").strip())
        and (successor.course or "") == (str(destination_course or "").strip())
        and successor.valid_from
        and getdate(successor.valid_from) == expected_start
    ):
        return {
            "action": "already-transferred",
            "source_name": source.name,
            "source_title": source.assignment_title,
            "successor_name": successor.name,
            "successor_title": successor.assignment_title,
            "transfer_date": str(source.ended_on),
            "successor_valid_from": str(successor.valid_from),
            "successor_valid_to": str(successor.valid_to or ""),
            "source_branch_eligibility_changed": False,
        }
    frappe.throw(
        _("This Instructor Assignment was already transferred. Its transfer history will not be rewritten."),
        frappe.ValidationError,
    )


@frappe.whitelist(methods=["POST"])
def preview_instructor_assignment_transfer(
    name: str,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None = None,
    destination_course: str | None = None,
    transfer_date: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_transfer")
    source = _source_assignment(name)
    if source.transferred_to_assignment:
        return {
            "already_transferred": True,
            "source_name": source.name,
            "successor_name": source.transferred_to_assignment,
        }
    if source.replaced_by_assignment:
        frappe.throw(_("This Instructor Assignment was already replaced and cannot be transferred."), frappe.ValidationError)
    if source.ended_on:
        frappe.throw(_("This Instructor Assignment has already ended and cannot be transferred."), frappe.ValidationError)
    return _transfer_plan(
        source,
        destination_branch,
        destination_program_offering,
        destination_student_group,
        destination_course,
        transfer_date,
        reason,
    )


@frappe.whitelist(methods=["POST"])
def transfer_instructor_assignment(
    name: str,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None = None,
    destination_course: str | None = None,
    transfer_date: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="transfer_instructor_assignment")
    if not frappe.has_permission("EduEdge Instructor Assignment", "create"):
        frappe.throw(_("You are not permitted to create the transferred Instructor Assignment."), frappe.PermissionError)

    savepoint = "eduedge_instructor_assignment_transfer"
    frappe.db.savepoint(savepoint)
    try:
        assignment_name = str(name or "").strip()
        if not assignment_name:
            frappe.throw(_("Select an Instructor Assignment to transfer."), frappe.ValidationError)
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (assignment_name,),
        )
        source = _source_assignment(assignment_name)
        existing = _already_transferred(
            source,
            destination_branch,
            destination_program_offering,
            destination_student_group,
            destination_course,
            transfer_date,
            reason,
        )
        if existing:
            return existing
        if source.replaced_by_assignment:
            frappe.throw(_("This Instructor Assignment was already replaced and cannot be transferred."), frappe.ValidationError)
        if source.ended_on:
            frappe.throw(_("This Instructor Assignment has already ended and cannot be transferred."), frappe.ValidationError)

        plan = _transfer_plan(
            source,
            destination_branch,
            destination_program_offering,
            destination_student_group,
            destination_course,
            transfer_date,
            reason,
        )
        if plan["conflict_count"]:
            frappe.throw(
                _("Transfer plan has {0} conflict(s). Resolve them before saving.").format(plan["conflict_count"]),
                frappe.ValidationError,
            )

        transfer = getdate(plan["transfer_date"])
        destination = plan["destination"]
        successor_start = getdate(destination["valid_from"])
        successor_end = getdate(destination["valid_to"]) if destination["valid_to"] else None
        resolved_reason = plan["reason"]

        source.valid_to = transfer
        source.ended_on = transfer
        source.ended_by = frappe.session.user
        source.end_reason = resolved_reason
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            source.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        branch_result = _ensure_incoming_branch_access(
            source.instructor,
            destination["school_branch"],
            successor_start,
            successor_end,
        )

        successor = frappe.new_doc("EduEdge Instructor Assignment")
        successor.instructor = source.instructor
        successor.assignment_type = _normalise_type(source.assignment_type)
        successor.assignment_scope = source.assignment_scope
        successor.enabled = 1
        successor.school_branch = destination["school_branch"]
        successor.program_offering = destination["program_offering"]
        successor.student_group = destination.get("student_group")
        successor.course = destination.get("course")
        successor.valid_from = successor_start
        successor.valid_to = successor_end
        successor.transferred_from_assignment = source.name
        successor.transfer_reason = resolved_reason
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            successor.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        source.transferred_to_assignment = successor.name
        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            source.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        source.add_comment(
            "Info",
            _("Instructor Assignment transferred. Final responsibility date: {0}. Destination: {1}. Reason: {2}").format(
                transfer,
                successor.assignment_title,
                resolved_reason,
            ),
        )
        successor.add_comment(
            "Info",
            _("Created by Instructor Assignment transfer. Previous responsibility: {0}. Responsibility starts: {1}. Reason: {2}").format(
                source.assignment_title,
                successor_start,
                resolved_reason,
            ),
        )

        return {
            "action": "transferred",
            "source_name": source.name,
            "source_title": source.assignment_title,
            "successor_name": successor.name,
            "successor_title": successor.assignment_title,
            "transfer_date": str(transfer),
            "source_final_valid_to": str(source.valid_to),
            "successor_valid_from": str(successor.valid_from),
            "successor_valid_to": str(successor.valid_to or ""),
            "instructor": successor.instructor,
            "reason": resolved_reason,
            "destination_branch_eligibility": branch_result,
            "source_branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
