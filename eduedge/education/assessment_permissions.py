from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import (
    assignment_capability_enforcement_enabled,
    user_has_instructor_assignment_capability,
)
from eduedge.education.instructor_scope import (
    get_active_instructor_names_for_user,
    is_limited_instructor_user,
)
from eduedge.education.permissions import (
    assessment_plan_query as branch_assessment_plan_query,
    assessment_result_query as branch_assessment_result_query,
    has_education_branch_permission,
)
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE

READ_TYPES = {None, "read", "report", "print", "email"}
PLAN_MUTATION_TYPES = {"create", "write", "submit"}
RESULT_MUTATION_TYPES = {"create", "write", "submit"}
BLOCKED_MUTATION_TYPES = {"delete", "cancel", "amend", "share", "import"}


def _exact_active_instructor(user: str) -> str:
    names = get_active_instructor_names_for_user(user)
    return names[0] if len(names) == 1 else ""


def _assignment_exists_sql(*, table: str, capability: str, user: str, result_mode: bool = False) -> str:
    instructor = _exact_active_instructor(user)
    if not instructor:
        return "1=0"
    if not frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
        return "1=0"

    assignment = "assignment"
    if result_mode:
        plan_table = "`tabAssessment Plan` plan"
        group_table = "`tabStudent Group` student_group"
        plan_join = (
            f"inner join {plan_table} on plan.name = `{table}`.assessment_plan\n"
            f"inner join {group_table} on student_group.name = plan.student_group"
        )
        branch_expr = f"plan.`{BRANCH_FIELD}`"
        course_expr = "plan.course"
        group_expr = "plan.student_group"
        date_expr = "coalesce(plan.schedule_date, current_date())"
    else:
        plan_join = "inner join `tabStudent Group` student_group on student_group.name = `tabAssessment Plan`.student_group"
        branch_expr = f"`tabAssessment Plan`.`{BRANCH_FIELD}`"
        course_expr = "`tabAssessment Plan`.course"
        group_expr = "`tabAssessment Plan`.student_group"
        date_expr = "coalesce(`tabAssessment Plan`.schedule_date, current_date())"

    return f"""
        exists (
            select 1
            from `tabEduEdge Instructor Assignment` {assignment}
            {plan_join}
            where {assignment}.instructor = {frappe.db.escape(instructor)}
                and {assignment}.enabled = 1
                and {assignment}.`{capability}` = 1
                and {assignment}.school_branch = {branch_expr}
                and {assignment}.program_offering = student_group.`{OFFERING_FIELD}`
                and {assignment}.course = {course_expr}
                and ({assignment}.valid_from is null or {assignment}.valid_from <= {date_expr})
                and ({assignment}.valid_to is null or {assignment}.valid_to >= {date_expr})
                and (
                    {assignment}.assignment_scope = {frappe.db.escape(CLASS_SCOPE)}
                    or (
                        {assignment}.assignment_scope = {frappe.db.escape(CLASS_ARM_SCOPE)}
                        and {assignment}.student_group = {group_expr}
                    )
                )
        )
    """


def assessment_plan_query(user: str | None = None) -> str:
    resolved_user = user or frappe.session.user
    branch_condition = branch_assessment_plan_query(resolved_user)
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):
        return branch_condition
    capability_condition = _assignment_exists_sql(
        table="Assessment Plan",
        capability="can_view_subject_content",
        user=resolved_user,
        result_mode=False,
    )
    return _and_conditions(branch_condition, capability_condition)


def assessment_result_query(user: str | None = None) -> str:
    resolved_user = user or frappe.session.user
    branch_condition = branch_assessment_result_query(resolved_user)
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):
        return branch_condition
    capability_condition = _assignment_exists_sql(
        table="Assessment Result",
        capability="can_view_subject_content",
        user=resolved_user,
        result_mode=True,
    )
    return _and_conditions(branch_condition, capability_condition)


def _group_offering(student_group: str | None) -> str:
    if not student_group or not frappe.get_meta("Student Group").has_field(OFFERING_FIELD):
        return ""
    return str(frappe.db.get_value("Student Group", student_group, OFFERING_FIELD) or "")


def _plan_context(doc) -> dict:
    return {
        "school_branch": str(doc.get(BRANCH_FIELD) or ""),
        "program_offering": _group_offering(doc.get("student_group")),
        "student_group": str(doc.get("student_group") or ""),
        "course": str(doc.get("course") or ""),
        "on_date": doc.get("schedule_date") or nowdate(),
    }


def _result_context(doc) -> dict:
    if not doc or not doc.get("assessment_plan"):
        return {}
    plan = frappe.db.get_value(
        "Assessment Plan",
        doc.get("assessment_plan"),
        ["student_group", "course", "schedule_date", BRANCH_FIELD],
        as_dict=True,
    )
    if not plan:
        return {}
    return {
        "school_branch": str(plan.get(BRANCH_FIELD) or doc.get(BRANCH_FIELD) or ""),
        "program_offering": _group_offering(plan.student_group),
        "student_group": str(plan.student_group or ""),
        "course": str(plan.course or ""),
        "plan_date": plan.schedule_date or nowdate(),
    }


def has_assessment_plan_permission(doc, user=None, permission_type=None) -> bool:
    resolved_user = user or frappe.session.user
    if not has_education_branch_permission(doc, resolved_user, permission_type):
        return False
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):
        return True
    if permission_type in BLOCKED_MUTATION_TYPES:
        return False
    if not doc:
        return permission_type in READ_TYPES
    context = _plan_context(doc)
    if not all(context.get(key) for key in ("school_branch", "program_offering", "course")):
        return False
    capability = "can_create_assessment_plans" if permission_type in PLAN_MUTATION_TYPES else "can_view_subject_content"
    return user_has_instructor_assignment_capability(
        capability,
        user=resolved_user,
        school_branch=context["school_branch"],
        program_offering=context["program_offering"],
        student_group=context["student_group"],
        course=context["course"],
        on_date=context["on_date"],
    )


def has_assessment_result_permission(doc, user=None, permission_type=None) -> bool:
    resolved_user = user or frappe.session.user
    if not has_education_branch_permission(doc, resolved_user, permission_type):
        return False
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(resolved_user):
        return True
    if permission_type in BLOCKED_MUTATION_TYPES:
        return False
    if not doc:
        return permission_type in READ_TYPES
    context = _result_context(doc)
    if not all(context.get(key) for key in ("school_branch", "program_offering", "course")):
        return False
    mutation = permission_type in RESULT_MUTATION_TYPES
    capability = "can_enter_marks" if mutation else "can_view_subject_content"
    # Historical result visibility follows the assignment that covered the assessment
    # date. Mark entry remains a current operational permission, matching the server
    # before_validate gate in assessment_operations.py.
    effective_date = nowdate() if mutation else context["plan_date"]
    return user_has_instructor_assignment_capability(
        capability,
        user=resolved_user,
        school_branch=context["school_branch"],
        program_offering=context["program_offering"],
        student_group=context["student_group"],
        course=context["course"],
        on_date=effective_date,
    )


def _and_conditions(*conditions: str) -> str:
    parts = [condition.strip() for condition in conditions if condition and condition.strip()]
    if not parts:
        return ""
    return " and ".join(f"({condition})" for condition in parts)
