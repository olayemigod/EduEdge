from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from eduedge.api.academic_operations import _require_academic_operator, _resolve_branch
from eduedge.api.academic_operations_review import student_group_query
from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.curriculum_permissions import is_teacher_user
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import (
    assignment_capability_enforcement_enabled,
    get_user_capability_assignment_rows,
)
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, assigned_courses


MAX_GROUP_OPTIONS = 500
MAX_PLAN_OPTIONS = 500


def _group_record(name: str):
    if not name:
        return None
    meta = frappe.get_meta("Student Group")
    fields = ["name", "student_group_name", "program", "academic_year", "academic_term", BRANCH_FIELD, "disabled"]
    if meta.has_field(OFFERING_FIELD):
        fields.append(OFFERING_FIELD)
    return frappe.db.get_value("Student Group", name, fields, as_dict=True)


def _resolve_group_offering(group) -> str:
    if not group:
        return ""
    if group.get(OFFERING_FIELD):
        return str(group.get(OFFERING_FIELD) or "")
    filters = {
        "program": group.program,
        "academic_year": group.academic_year,
        "school_branch": group.get(BRANCH_FIELD),
        "is_active": 1,
    }
    if group.academic_term:
        filters["academic_term"] = group.academic_term
    else:
        filters["academic_term"] = ["is", "not set"]
    rows = frappe.get_all("EduEdge Program Offering", filters=filters, pluck="name", limit_page_length=2)
    return rows[0] if len(rows) == 1 else ""


def _row_covers_group(row: dict, group_name: str) -> bool:
    if row.get("assignment_scope") == CLASS_SCOPE:
        return True
    return bool(row.get("assignment_scope") == CLASS_ARM_SCOPE and row.get("student_group") == group_name)


def _session_term_compatible(group_term: str | None, selected_term: str | None) -> bool:
    """Session-wide Class Arms participate in every Term; legacy groups match exactly."""
    return not selected_term or not group_term or str(group_term) == str(selected_term)


def _capability_group_names(branch: str, reference_date) -> set[str]:
    rows = get_user_capability_assignment_rows(
        "can_create_assessment_plans",
        user=frappe.session.user,
        school_branch=branch,
        on_date=reference_date,
    )
    if not rows:
        return set()
    by_offering: dict[str, list[dict]] = {}
    for row in rows:
        offering = str(row.get("program_offering") or "")
        if offering:
            by_offering.setdefault(offering, []).append(row)
    if not by_offering:
        return set()

    meta = frappe.get_meta("Student Group")
    fields = ["name", "program", "academic_year", "academic_term", BRANCH_FIELD]
    if meta.has_field(OFFERING_FIELD):
        fields.append(OFFERING_FIELD)
    # Capability rows already prove exact Instructor identity, Branch Eligibility,
    # effective Subject Assignment and Class/Class Arm scope. Use a metadata read
    # here so creating the first Assessment Plan does not depend on an existing
    # Course Schedule merely to satisfy Student Group list permission.
    groups = frappe.get_all(
        "Student Group",
        filters={BRANCH_FIELD: branch, "disabled": 0},
        fields=fields,
        limit_page_length=MAX_GROUP_OPTIONS,
    )
    allowed = set()
    for group in groups:
        offering = _resolve_group_offering(group)
        capability_rows = by_offering.get(offering, [])
        if any(_row_covers_group(row, group.name) for row in capability_rows):
            allowed.add(group.name)
    return allowed


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def assessment_plan_student_group_query(doctype, txt, searchfield, start, page_len, filters):
    _require_academic_operator()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    if not (is_teacher_user() and assignment_capability_enforcement_enabled()):
        # The reviewed Academic Operations query understands session-wide Student
        # Groups plus exact legacy term groups. Reuse it rather than reintroducing
        # the retired term-bound Class Arm assumption here.
        return student_group_query(doctype, txt, searchfield, start, page_len, filters)

    branch = _resolve_branch(filters.get(BRANCH_FIELD))
    reference_date = getdate(filters.get("schedule_date") or nowdate())
    allowed_groups = _capability_group_names(branch, reference_date)
    if not allowed_groups:
        return []

    group_filters: dict = {"name": ["in", sorted(allowed_groups)], BRANCH_FIELD: branch, "disabled": 0}
    if filters.get("academic_year"):
        group_filters["academic_year"] = filters["academic_year"]
    # allowed_groups is already capability-authorized above. Keep this selector
    # bootstrap-safe instead of re-applying schedule-derived Student Group list scope.
    rows = frappe.get_all(
        "Student Group",
        filters=group_filters,
        or_filters={
            "name": ["like", f"%{txt}%"],
            "student_group_name": ["like", f"%{txt}%"],
            "program": ["like", f"%{txt}%"],
            "course": ["like", f"%{txt}%"],
        },
        fields=["name", "student_group_name", "program", "course", "academic_term"],
        order_by="student_group_name asc",
        limit_page_length=MAX_GROUP_OPTIONS,
    )
    selected_term = filters.get("academic_term")
    compatible = [row for row in rows if _session_term_compatible(row.academic_term, selected_term)]
    offset = max(int(start), 0)
    limit = max(int(page_len), 1)
    return [
        [row.name, row.student_group_name, row.program, row.course]
        for row in compatible[offset : offset + limit]
    ]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def assessment_plan_course_query(doctype, txt, searchfield, start, page_len, filters):
    _require_academic_operator()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    student_group = str(filters.get("student_group") or "").strip()
    if not student_group:
        return []
    group = _group_record(student_group)
    if not group or group.disabled:
        return []
    branch = _resolve_branch(filters.get(BRANCH_FIELD) or group.get(BRANCH_FIELD))
    if group.get(BRANCH_FIELD) != branch:
        frappe.throw(_("The selected Student Group belongs to another Branch / Campus."), frappe.ValidationError)
    if not _session_term_compatible(group.academic_term, filters.get("academic_term")):
        frappe.throw(
            _("The selected historical Student Group belongs to another Academic Term."),
            frappe.ValidationError,
        )
    offering = _resolve_group_offering(group)
    if not offering:
        return []

    curriculum_courses = set(
        frappe.get_all(
            "Program Course",
            filters={"parent": group.program, "parenttype": "Program"},
            pluck="course",
            limit_page_length=0,
        )
    )
    capability_scoped = is_teacher_user() and assignment_capability_enforcement_enabled()
    if is_teacher_user():
        if capability_scoped:
            reference_date = getdate(filters.get("schedule_date") or nowdate())
            capability_rows = get_user_capability_assignment_rows(
                "can_create_assessment_plans",
                user=frappe.session.user,
                school_branch=branch,
                on_date=reference_date,
            )
            allowed_courses = {
                row.get("course")
                for row in capability_rows
                if row.get("program_offering") == offering
                and _row_covers_group(row, student_group)
                and row.get("course")
            }
        else:
            allowed_courses = assigned_courses(
                branch=branch,
                program_offering=offering,
                student_group=student_group,
            )
        curriculum_courses &= set(allowed_courses)

    if not curriculum_courses:
        return []
    pattern = f"%{txt or ''}%"
    # In enforced Instructor mode, curriculum_courses has already been narrowed by
    # the exact can_create_assessment_plans capability, Branch Eligibility, Offering,
    # Class scope and assessment date. Do not re-apply generic Course visibility,
    # which is governed by the independent can_view_subject_content capability.
    course_reader = frappe.get_all if capability_scoped else frappe.get_list
    return course_reader(
        "Course",
        filters={"name": ["in", sorted(curriculum_courses)]},
        or_filters={"name": ["like", pattern], "course_name": ["like", pattern]},
        fields=["name", "course_name"],
        start=int(start),
        page_length=int(page_len),
        order_by="course_name asc",
        as_list=True,
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def assessment_result_plan_query(doctype, txt, searchfield, start, page_len, filters):
    """Return submitted Assessment Plans the current user may use for mark entry."""
    _require_academic_operator()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    branch = _resolve_branch(filters.get(BRANCH_FIELD))
    pattern = f"%{txt or ''}%"
    base_filters = {BRANCH_FIELD: branch, "docstatus": 1}

    capability_scoped = is_teacher_user() and assignment_capability_enforcement_enabled()
    if not capability_scoped:
        return frappe.get_list(
            "Assessment Plan",
            filters=base_filters,
            or_filters={
                "name": ["like", pattern],
                "assessment_name": ["like", pattern],
                "student_group": ["like", pattern],
                "course": ["like", pattern],
            },
            fields=["name", "assessment_name", "student_group", "course", "schedule_date"],
            start=int(start),
            page_length=int(page_len),
            order_by="schedule_date desc, assessment_name asc, name asc",
            as_list=True,
        )

    if not frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
        return []

    capability_rows = get_user_capability_assignment_rows(
        "can_enter_marks",
        user=frappe.session.user,
        school_branch=branch,
        on_date=nowdate(),
    )
    conditions = []
    for row in capability_rows:
        offering = str(row.get("program_offering") or "")
        course = str(row.get("course") or "")
        if not offering or not course:
            continue
        condition = (
            f"(student_group.`{OFFERING_FIELD}` = {frappe.db.escape(offering)} "
            f"and plan.course = {frappe.db.escape(course)}"
        )
        if row.get("assignment_scope") == CLASS_ARM_SCOPE:
            student_group = str(row.get("student_group") or "")
            if not student_group:
                continue
            condition += f" and plan.student_group = {frappe.db.escape(student_group)}"
        elif row.get("assignment_scope") != CLASS_SCOPE:
            continue
        conditions.append(condition + ")")
    if not conditions:
        return []

    return frappe.db.sql(
        f"""
        select
            plan.name,
            plan.assessment_name,
            plan.student_group,
            plan.course,
            plan.schedule_date
        from `tabAssessment Plan` plan
        inner join `tabStudent Group` student_group on student_group.name = plan.student_group
        where plan.`{BRANCH_FIELD}` = %(branch)s
            and plan.docstatus = 1
            and ({" or ".join(conditions)})
            and (
                plan.name like %(txt)s
                or coalesce(plan.assessment_name, '') like %(txt)s
                or coalesce(plan.student_group, '') like %(txt)s
                or coalesce(plan.course, '') like %(txt)s
            )
        order by plan.schedule_date desc, plan.assessment_name asc, plan.name asc
        limit %(start)s, %(page_len)s
        """,
        {
            "branch": branch,
            "txt": pattern,
            "start": max(int(start), 0),
            "page_len": min(max(int(page_len), 1), MAX_PLAN_OPTIONS),
        },
        as_dict=False,
    )

