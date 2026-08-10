from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, getdate

from eduedge.api.instructor_assignment_replacement import (
    _branch_access_preview,
    _ensure_incoming_branch_access,
    _same_date,
    _type_variants,
)
from eduedge.api.instructor_assignment_transfer import _destination_conflicts, _normalise_type
from eduedge.api.instructor_assignments import _period_dates, _require_assignment_manager
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import (
    CLASS_ARM_SCOPE,
    CLASS_RESPONSIBILITY_TYPES,
    COURSE_REQUIRED_TYPES,
)
from eduedge.platform.access import require_eduedge_access


def _clean_reason(reason: str | None) -> str:
    value = str(reason or "").strip()
    if len(value) < 3:
        frappe.throw(
            _("Give a short reason for preparing this Instructor Assignment for the next academic period."),
            frappe.ValidationError,
        )
    return value


def _source_assignment(name: str):
    assignment_name = str(name or "").strip()
    if not assignment_name:
        frappe.throw(_("Select an Instructor Assignment to prepare for the next academic period."), frappe.ValidationError)

    doc = frappe.get_doc("EduEdge Instructor Assignment", assignment_name)
    doc.check_permission("read")
    assert_branch_access(doc.school_branch)

    if not cint(doc.enabled):
        frappe.throw(
            _("Disabled Instructor Assignments cannot be used as a next-period preparation source."),
            frappe.ValidationError,
        )

    instructor = frappe.get_doc("Instructor", doc.instructor)
    instructor.check_permission("read")
    if str(instructor.status or "") != "Active":
        frappe.throw(
            _("The Instructor must be active before a future responsibility can be prepared."),
            frappe.ValidationError,
        )

    period_start, period_end = _period_dates(doc.academic_year, doc.academic_term)
    source_end = period_end or doc.valid_to
    if not source_end:
        frappe.throw(
            _("The source assignment has no bounded academic period. Complete its Academic Session / Term dates before preparing the next period."),
            frappe.ValidationError,
        )
    if period_start and doc.valid_from and getdate(doc.valid_from) < getdate(period_start):
        frappe.throw(
            _("The source assignment starts before its academic period. Correct that record before preparing the next period."),
            frappe.ValidationError,
        )
    if period_end and doc.valid_to and getdate(doc.valid_to) > getdate(period_end):
        frappe.throw(
            _("The source assignment extends beyond its academic period. Correct that record before preparing the next period."),
            frappe.ValidationError,
        )
    return doc, instructor, getdate(source_end)


def _destination_context(
    source,
    instructor,
    source_period_end,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None,
    destination_course: str | None,
    valid_from: str | None,
    valid_to: str | None,
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
    if offering.name == source.program_offering:
        frappe.throw(
            _("Next-period preparation must use a different Class / Programme Offering from the source assignment."),
            frappe.ValidationError,
        )

    period_start, period_end = _period_dates(offering.academic_year, offering.academic_term)
    if not period_start or not period_end:
        frappe.throw(
            _("Destination Academic Session / Term must have both start and end dates before assignments can be prepared."),
            frappe.ValidationError,
        )
    period_start = getdate(period_start)
    period_end = getdate(period_end)
    if period_start <= source_period_end:
        frappe.throw(
            _("Destination Class must belong to a later academic period than the source assignment."),
            frappe.ValidationError,
        )

    prepared_start = getdate(valid_from) if str(valid_from or "").strip() else period_start
    prepared_end = getdate(valid_to) if str(valid_to or "").strip() else period_end
    if prepared_end < prepared_start:
        frappe.throw(_("Destination Valid To cannot be earlier than Valid From."), frappe.ValidationError)
    if prepared_start < period_start or prepared_start > period_end:
        frappe.throw(
            _("Destination Valid From must fall inside the selected Class academic period."),
            frappe.ValidationError,
        )
    if prepared_end < period_start or prepared_end > period_end:
        frappe.throw(
            _("Destination Valid To must fall inside the selected Class academic period."),
            frappe.ValidationError,
        )

    assignment_type = _normalise_type(source.assignment_type)
    if source.assignment_scope == CLASS_ARM_SCOPE:
        if not group_name:
            frappe.throw(_("Select the destination Class Arm / Student Group."), frappe.ValidationError)
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
            (group.get("eduedge_display_name") if group and frappe.get_meta("Student Group").has_field("eduedge_display_name") else None)
            or (group.student_group_name if group else None)
            or ""
        ),
        "course": course_name,
        "course_name": (course.course_name if course else None) or "",
        "valid_from": str(prepared_start),
        "valid_to": str(prepared_end),
        "period_start_date": str(period_start),
        "period_end_date": str(period_end),
    }


def _existing_preparation(source, destination: dict, reason: str) -> dict | None:
    rows = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "prepared_from_assignment": source.name,
            "instructor": source.instructor,
            "school_branch": destination["school_branch"],
            "program_offering": destination["program_offering"],
            "assignment_scope": source.assignment_scope,
            "assignment_type": ["in", _type_variants(_normalise_type(source.assignment_type))],
        },
        fields=[
            "name",
            "assignment_title",
            "student_group",
            "course",
            "valid_from",
            "valid_to",
            "preparation_reason",
        ],
        limit_page_length=0,
    )
    for row in rows:
        if (row.student_group or "") != (destination.get("student_group") or ""):
            continue
        if (row.course or "") != (destination.get("course") or ""):
            continue
        same_dates = _same_date(row.valid_from, destination["valid_from"]) and _same_date(row.valid_to, destination["valid_to"])
        same_reason = str(row.preparation_reason or "").strip() == reason
        if same_dates and same_reason:
            return {
                "action": "already-prepared",
                "source_name": source.name,
                "source_title": source.assignment_title,
                "prepared_name": row.name,
                "prepared_title": row.assignment_title or "",
                "prepared_valid_from": str(row.valid_from or ""),
                "prepared_valid_to": str(row.valid_to or ""),
                "source_changed": False,
                "source_branch_eligibility_changed": False,
            }
        frappe.throw(
            _("This source assignment already has a prepared responsibility for the selected destination. Use lifecycle actions on that prepared assignment instead of duplicating or rewriting preparation history."),
            frappe.ValidationError,
        )
    return None


def _preparation_plan(
    source,
    instructor,
    source_period_end,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None,
    destination_course: str | None,
    valid_from: str | None,
    valid_to: str | None,
    reason: str | None,
) -> dict:
    resolved_reason = _clean_reason(reason)
    destination = _destination_context(
        source,
        instructor,
        source_period_end,
        destination_branch,
        destination_program_offering,
        destination_student_group,
        destination_course,
        valid_from,
        valid_to,
    )
    existing = _existing_preparation(source, destination, resolved_reason)
    if existing:
        return {"already_prepared": True, **existing}

    start = getdate(destination["valid_from"])
    end = getdate(destination["valid_to"])
    conflicts = _destination_conflicts(source, destination, start, end)
    branch_access = _branch_access_preview(source.instructor, destination["school_branch"], start, end)
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
            "valid_to": str(source.valid_to or ""),
        },
        "destination": destination,
        "reason": resolved_reason,
        "destination_branch_eligibility": branch_access,
        "source_changed": False,
        "source_branch_eligibility_changed": False,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


@frappe.whitelist(methods=["POST"])
def preview_instructor_assignment_preparation(
    name: str,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None = None,
    destination_course: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="preview_instructor_assignment_preparation")
    source, instructor, source_period_end = _source_assignment(name)
    return _preparation_plan(
        source,
        instructor,
        source_period_end,
        destination_branch,
        destination_program_offering,
        destination_student_group,
        destination_course,
        valid_from,
        valid_to,
        reason,
    )


@frappe.whitelist(methods=["POST"])
def prepare_instructor_assignment_for_next_period(
    name: str,
    destination_branch: str,
    destination_program_offering: str,
    destination_student_group: str | None = None,
    destination_course: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    reason: str | None = None,
) -> dict:
    _require_assignment_manager()
    require_eduedge_access(feature_key="academics", action="prepare_instructor_assignment_for_next_period")
    if not frappe.has_permission("EduEdge Instructor Assignment", "create"):
        frappe.throw(_("You are not permitted to create the prepared Instructor Assignment."), frappe.PermissionError)

    savepoint = "eduedge_instructor_assignment_prepare"
    frappe.db.savepoint(savepoint)
    try:
        assignment_name = str(name or "").strip()
        if not assignment_name:
            frappe.throw(_("Select an Instructor Assignment to prepare for the next academic period."), frappe.ValidationError)
        frappe.db.sql(
            "select name from `tabEduEdge Instructor Assignment` where name = %s for update",
            (assignment_name,),
        )
        source, instructor, source_period_end = _source_assignment(assignment_name)
        plan = _preparation_plan(
            source,
            instructor,
            source_period_end,
            destination_branch,
            destination_program_offering,
            destination_student_group,
            destination_course,
            valid_from,
            valid_to,
            reason,
        )
        if plan.get("already_prepared"):
            return plan
        if plan["conflict_count"]:
            frappe.throw(
                _("Next-period preparation has {0} conflict(s). Resolve them before saving.").format(plan["conflict_count"]),
                frappe.ValidationError,
            )

        destination = plan["destination"]
        start = getdate(destination["valid_from"])
        end = getdate(destination["valid_to"])
        branch_result = _ensure_incoming_branch_access(
            source.instructor,
            destination["school_branch"],
            start,
            end,
        )

        prepared = frappe.new_doc("EduEdge Instructor Assignment")
        prepared.instructor = source.instructor
        prepared.assignment_type = _normalise_type(source.assignment_type)
        prepared.assignment_scope = source.assignment_scope
        prepared.enabled = 1
        prepared.school_branch = destination["school_branch"]
        prepared.program_offering = destination["program_offering"]
        prepared.student_group = destination.get("student_group")
        prepared.course = destination.get("course")
        prepared.valid_from = start
        prepared.valid_to = end
        prepared.prepared_from_assignment = source.name
        prepared.preparation_reason = plan["reason"]

        frappe.flags.in_eduedge_assignment_lifecycle = True
        try:
            prepared.save()
        finally:
            frappe.flags.in_eduedge_assignment_lifecycle = False

        prepared.add_comment(
            "Info",
            _("Prepared from previous Instructor Assignment: {0}. Future responsibility period: {1} to {2}. Reason: {3}").format(
                source.assignment_title,
                prepared.valid_from,
                prepared.valid_to,
                plan["reason"],
            ),
        )

        return {
            "action": "prepared",
            "source_name": source.name,
            "source_title": source.assignment_title,
            "prepared_name": prepared.name,
            "prepared_title": prepared.assignment_title,
            "prepared_valid_from": str(prepared.valid_from),
            "prepared_valid_to": str(prepared.valid_to),
            "instructor": prepared.instructor,
            "reason": plan["reason"],
            "destination_branch_eligibility": branch_result,
            "source_changed": False,
            "source_branch_eligibility_changed": False,
        }
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise
