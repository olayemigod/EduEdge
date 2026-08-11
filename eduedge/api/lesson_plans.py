from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, nowdate

from eduedge.education.academic_fields import OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignment_capabilities import (
    assignment_capability_enforcement_enabled,
    require_instructor_assignment_capability,
)
from eduedge.education.instructor_scope import (
    get_active_instructor_names_for_user,
    is_limited_instructor_user,
    resolve_exact_instructor_for_user,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.eduedge.doctype.eduedge_lesson_plan.eduedge_lesson_plan import (
    LESSON_PLAN_ACTION_FLAG,
    resolve_lesson_instructor_assignment,
    snapshot_lesson_plan_context,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

LESSON_DOCTYPE = "EduEdge Lesson Plan"
SCHEME_DOCTYPE = "EduEdge Scheme of Work"
MANAGER_ROLES = {
    "Administrator",
    "System Manager",
    "EduEdge Super Administrator",
    "EduEdge Administrator",
    "School Administrator",
    "Academic Administrator",
    "Education Manager",
}
EDITABLE_FIELDS = (
    "scheme_of_work",
    "scheme_item_reference",
    "student_group",
    "lesson_date",
    "period_label",
    "duration_minutes",
    "instructor",
    "lesson_objectives",
    "prior_knowledge",
    "introduction",
    "teaching_methods",
    "teacher_activities",
    "learner_activities",
    "learning_resources",
    "formative_assessment",
    "differentiation_notes",
    "homework",
    "notes",
)
SUBMISSION_REQUIRED_FIELDS = {
    "lesson_objectives": "Lesson Objectives",
    "teaching_methods": "Teaching Methods",
    "learner_activities": "Learner Activities",
    "formative_assessment": "Assessment / Evaluation",
}


def _is_manager() -> bool:
    if frappe.session.user == "Administrator":
        return True
    return bool(MANAGER_ROLES.intersection(set(frappe.get_roles(frappe.session.user)) | {frappe.session.user}))


def _parse_payload(payload) -> dict:
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("A valid Lesson Plan payload is required."), frappe.ValidationError)
    return payload


@contextmanager
def _lesson_action():
    previous = getattr(frappe.flags, LESSON_PLAN_ACTION_FLAG, False)
    setattr(frappe.flags, LESSON_PLAN_ACTION_FLAG, True)
    try:
        yield
    finally:
        setattr(frappe.flags, LESSON_PLAN_ACTION_FLAG, previous)


def _context_authorized(doc, *, write: bool) -> bool:
    assert_branch_access(doc.school_branch)
    if _is_manager():
        permission = "write" if write and not doc.is_new() else "create" if write else "read"
        if not frappe.has_permission(LESSON_DOCTYPE, permission):
            frappe.throw(_("You are not permitted to manage Lesson Plans."), frappe.PermissionError)
        return True
    if not is_limited_instructor_user():
        frappe.throw(_("You are not permitted to access Lesson Plans."), frappe.PermissionError)
    instructor = resolve_exact_instructor_for_user(required=True)
    if doc.instructor != instructor:
        frappe.throw(_("You can access only Lesson Plans assigned to your Instructor identity."), frappe.PermissionError)
    assignment = resolve_lesson_instructor_assignment(
        instructor=instructor,
        school_branch=doc.school_branch,
        program_offering=doc.program_offering,
        student_group=doc.student_group,
        course=doc.course,
        lesson_date=doc.lesson_date,
    )
    if doc.instructor_assignment and doc.instructor_assignment != assignment.get("name"):
        frappe.throw(_("The Lesson Plan teaching assignment no longer matches its academic context."), frappe.PermissionError)
    if assignment_capability_enforcement_enabled():
        require_instructor_assignment_capability(
            "can_view_subject_content",
            user=frappe.session.user,
            school_branch=doc.school_branch,
            program_offering=doc.program_offering,
            student_group=doc.student_group,
            course=doc.course,
            on_date=doc.lesson_date,
        )
    return True


def _serialize(doc) -> dict:
    state = {
        "can_edit": False,
        "can_submit": False,
        "can_approve": False,
        "can_return": False,
    }
    try:
        can_write = _context_authorized(doc, write=True)
    except frappe.PermissionError:
        can_write = False
    if can_write and doc.status in {"Draft", "Returned"}:
        state["can_edit"] = True
        state["can_submit"] = True
    if _is_manager() and doc.status == "Submitted":
        state["can_approve"] = True
        state["can_return"] = True
    return {
        "name": doc.name,
        "lesson_plan_title": doc.lesson_plan_title,
        "status": doc.status,
        "scheme_of_work": doc.scheme_of_work,
        "scheme_item_reference": doc.scheme_item_reference,
        "scheme_version": cint(doc.scheme_version),
        "institution": doc.institution,
        "school_branch": doc.school_branch,
        "program_offering": doc.program_offering,
        "student_group": doc.student_group or "",
        "course": doc.course,
        "academic_year": doc.academic_year,
        "academic_term": doc.academic_term or "",
        "lesson_date": doc.lesson_date,
        "period_label": doc.period_label or "",
        "duration_minutes": cint(doc.duration_minutes),
        "instructor": doc.instructor,
        "instructor_assignment": doc.instructor_assignment,
        "lesson_objectives": doc.lesson_objectives or "",
        "prior_knowledge": doc.prior_knowledge or "",
        "introduction": doc.introduction or "",
        "teaching_methods": doc.teaching_methods or "",
        "teacher_activities": doc.teacher_activities or "",
        "learner_activities": doc.learner_activities or "",
        "learning_resources": doc.learning_resources or "",
        "formative_assessment": doc.formative_assessment or "",
        "differentiation_notes": doc.differentiation_notes or "",
        "homework": doc.homework or "",
        "prepared_by": doc.prepared_by or "",
        "submitted_by": doc.submitted_by or "",
        "submitted_on": doc.submitted_on,
        "reviewed_by": doc.reviewed_by or "",
        "reviewed_on": doc.reviewed_on,
        "review_comment": doc.review_comment or "",
        "return_reason": doc.return_reason or "",
        "scheme_title_snapshot": doc.scheme_title_snapshot or "",
        "offering_title_snapshot": doc.offering_title_snapshot or "",
        "student_group_name_snapshot": doc.student_group_name_snapshot or "",
        "course_name_snapshot": doc.course_name_snapshot or "",
        "topic_name_snapshot": doc.topic_name_snapshot or "",
        "learning_objective_snapshot": doc.learning_objective_snapshot or "",
        "notes": doc.notes or "",
        **state,
    }


def _assignment_rows(branch: str) -> list[dict]:
    if not is_limited_instructor_user():
        return []
    instructors = get_active_instructor_names_for_user()
    if len(instructors) != 1:
        return []
    rows = frappe.get_all(
        "EduEdge Instructor Assignment",
        filters={
            "instructor": instructors[0],
            "school_branch": branch,
            "assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
            "enabled": 1,
        },
        fields=[
            "name",
            "program_offering",
            "assignment_scope",
            "student_group",
            "course",
            "valid_from",
            "valid_to",
            "can_view_subject_content",
        ],
        order_by="valid_from desc, modified desc",
        limit_page_length=0,
    )
    if assignment_capability_enforcement_enabled():
        rows = [row for row in rows if cint(row.can_view_subject_content)]
    return [dict(row) for row in rows]


def _offering_options(branch: str, assignments: list[dict]) -> list[dict]:
    filters: dict = {"school_branch": branch}
    if is_limited_instructor_user():
        names = sorted({row.get("program_offering") for row in assignments if row.get("program_offering")})
        filters["name"] = ["in", names or ["__none__"]]
    rows = frappe.get_list(
        "EduEdge Program Offering",
        filters=filters,
        fields=[
            "name",
            "offering_title",
            "program",
            "academic_year",
            "academic_term",
            "school_branch",
            "period_start_date",
            "period_end_date",
            "is_active",
        ],
        order_by="period_start_date desc, offering_title asc",
        limit_page_length=500,
    )
    return [
        {
            "value": row.name,
            "label": row.offering_title or row.name,
            "program": row.program,
            "academic_year": row.academic_year,
            "academic_term": row.academic_term or "",
            "period_start_date": row.period_start_date,
            "period_end_date": row.period_end_date,
            "is_active": bool(cint(row.is_active)),
        }
        for row in rows
    ]


def _group_options(branch: str, offering: str, assignments: list[dict]) -> list[dict]:
    if not offering:
        return []
    meta = frappe.get_meta("Student Group")
    filters: dict = {BRANCH_FIELD: branch}
    if meta.has_field(OFFERING_FIELD):
        filters[OFFERING_FIELD] = offering
    if is_limited_instructor_user():
        relevant = [row for row in assignments if row.get("program_offering") == offering]
        class_wide = any((row.get("assignment_scope") or CLASS_ARM_SCOPE) == CLASS_SCOPE for row in relevant)
        if not class_wide:
            names = sorted({row.get("student_group") for row in relevant if row.get("student_group")})
            filters["name"] = ["in", names or ["__none__"]]
    fields = ["name", "student_group_name", "disabled"]
    if meta.has_field("eduedge_display_name"):
        fields.append("eduedge_display_name")
    rows = frappe.get_list("Student Group", filters=filters, fields=fields, order_by="student_group_name asc", limit_page_length=500)
    return [
        {
            "value": row.name,
            "label": row.get("eduedge_display_name") or row.student_group_name or row.name,
        }
        for row in rows
        if not cint(row.disabled)
    ]


def _course_options(offering: str, group: str, assignments: list[dict]) -> list[dict]:
    if not offering:
        return []
    program = frappe.db.get_value("EduEdge Program Offering", offering, "program")
    curriculum = frappe.get_all(
        "Program Course",
        filters={"parent": program, "parenttype": "Program"},
        pluck="course",
        order_by="idx asc",
        limit_page_length=0,
    )
    allowed = set(curriculum)
    if is_limited_instructor_user():
        relevant = []
        for row in assignments:
            if row.get("program_offering") != offering or row.get("course") not in allowed:
                continue
            scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
            if group and scope == CLASS_ARM_SCOPE and row.get("student_group") != group:
                continue
            if not group and scope == CLASS_ARM_SCOPE:
                continue
            relevant.append(row)
        allowed = {row.get("course") for row in relevant if row.get("course")}
    rows = frappe.get_list(
        "Course",
        filters={"name": ["in", sorted(allowed) or ["__none__"]]},
        fields=["name", "course_name"],
        order_by="course_name asc",
        limit_page_length=500,
    )
    return [{"value": row.name, "label": row.course_name or row.name} for row in rows]


def _scheme_options(branch: str, offering: str, group: str, course: str) -> list[dict]:
    if not offering or not course:
        return []
    filters: dict = {
        "school_branch": branch,
        "program_offering": offering,
        "course": course,
        "status": "Approved",
    }
    rows = frappe.get_all(
        SCHEME_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "scheme_title",
            "version_no",
            "student_group",
            "period_start_date",
            "period_end_date",
            "academic_year",
            "academic_term",
        ],
        order_by="version_no desc, modified desc",
        limit_page_length=100,
    )
    visible = []
    for row in rows:
        if row.student_group and row.student_group != group:
            continue
        visible.append(
            {
                "value": row.name,
                "label": row.scheme_title or row.name,
                "version_no": cint(row.version_no),
                "student_group": row.student_group or "",
                "period_start_date": row.period_start_date,
                "period_end_date": row.period_end_date,
                "academic_year": row.academic_year,
                "academic_term": row.academic_term or "",
            }
        )
    return visible


def _scheme_items(scheme_name: str) -> list[dict]:
    if not scheme_name:
        return []
    scheme = frappe.get_doc(SCHEME_DOCTYPE, scheme_name)
    if scheme.status != "Approved":
        return []
    return [
        {
            "value": row.name,
            "label": row.topic_name_snapshot or frappe.db.get_value("Topic", row.topic, "topic_name") or row.topic,
            "sequence": cint(row.sequence),
            "week_no": cint(row.week_no),
            "learning_objective": row.learning_objective or "",
            "planned_start_date": row.planned_start_date,
            "planned_end_date": row.planned_end_date,
            "estimated_periods": cint(row.estimated_periods),
        }
        for row in scheme.get("items") or []
    ]


def _instructor_options(branch: str, offering: str, group: str, course: str, lesson_date: str) -> list[dict]:
    if not offering or not course or not lesson_date:
        return []
    if is_limited_instructor_user():
        names = get_active_instructor_names_for_user()
        if len(names) != 1:
            return []
        candidates = names
    else:
        candidates = frappe.get_all("Instructor", filters={"status": "Active"}, pluck="name", limit_page_length=0)
    visible = []
    for instructor in candidates:
        try:
            assignment = resolve_lesson_instructor_assignment(
                instructor=instructor,
                school_branch=branch,
                program_offering=offering,
                student_group=group,
                course=course,
                lesson_date=lesson_date,
            )
        except frappe.ValidationError:
            continue
        visible.append(
            {
                "value": instructor,
                "label": frappe.db.get_value("Instructor", instructor, "instructor_name") or instructor,
                "assignment": assignment.get("name"),
                "assignment_title": assignment.get("assignment_title") or assignment.get("name"),
            }
        )
    return visible


def _list_plans(filters: dict, *, start: int, page_length: int) -> dict:
    db_filters = {key: value for key, value in filters.items() if value not in (None, "")}
    date_from = db_filters.pop("date_from", None)
    date_to = db_filters.pop("date_to", None)
    if date_from and date_to:
        db_filters["lesson_date"] = ["between", [date_from, date_to]]
    elif date_from:
        db_filters["lesson_date"] = [">=", date_from]
    elif date_to:
        db_filters["lesson_date"] = ["<=", date_to]
    limit = min(max(cint(page_length) or 25, 1), 50)
    rows = frappe.get_all(
        LESSON_DOCTYPE,
        filters=db_filters,
        fields=["name"],
        order_by="lesson_date desc, modified desc",
        start=max(cint(start), 0),
        page_length=min(limit * 3 + 1, 151),
    )
    visible = []
    for row in rows:
        doc = frappe.get_doc(LESSON_DOCTYPE, row.name)
        try:
            _context_authorized(doc, write=False)
        except frappe.PermissionError:
            continue
        visible.append(_serialize(doc))
        if len(visible) > limit:
            break
    return {"rows": visible[:limit], "has_more": len(visible) > limit, "page_length": limit}


@frappe.whitelist()
def get_lesson_plan(name: str) -> dict:
    require_eduedge_access(feature_key="academics", action="view_lesson_plan")
    doc = frappe.get_doc(LESSON_DOCTYPE, name)
    _context_authorized(doc, write=False)
    return _serialize(doc)


@frappe.whitelist()
def get_lesson_plan_workbench(
    school_branch: str | None = None,
    program_offering: str | None = None,
    student_group: str | None = None,
    course: str | None = None,
    scheme_of_work: str | None = None,
    lesson_date: str | None = None,
    instructor: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    start: int = 0,
    page_length: int = 25,
) -> dict:
    require_eduedge_access(feature_key="academics", action="view_lesson_plans")
    branches = get_allowed_school_branches() or []
    branch_names = {row.get("name") for row in branches if row.get("name")}
    current = get_current_school_branch() or {}
    branch = str(school_branch or current.get("name") or "").strip()
    if not branch and len(branch_names) == 1:
        branch = next(iter(branch_names))
    if not branch or branch not in branch_names:
        frappe.throw(_("Select a permitted Branch / Campus."), frappe.PermissionError)
    assert_branch_access(branch)
    assignments = _assignment_rows(branch)
    offering = str(program_offering or "").strip()
    group = str(student_group or "").strip()
    subject = str(course or "").strip()
    scheme = str(scheme_of_work or "").strip()
    reference_date = str(lesson_date or "").strip()

    offerings = _offering_options(branch, assignments)
    offering_names = {row["value"] for row in offerings}
    if offering and offering not in offering_names:
        frappe.throw(_("Select a permitted Class / Programme Offering."), frappe.PermissionError)
    groups = _group_options(branch, offering, assignments)
    group_names = {row["value"] for row in groups}
    if group and group not in group_names:
        frappe.throw(_("Select a permitted Class Arm / Student Group."), frappe.PermissionError)
    courses = _course_options(offering, group, assignments)
    course_names = {row["value"] for row in courses}
    if subject and subject not in course_names:
        frappe.throw(_("Select a permitted Subject / Course."), frappe.PermissionError)
    schemes = _scheme_options(branch, offering, group, subject)
    scheme_names = {row["value"] for row in schemes}
    if scheme and scheme not in scheme_names:
        frappe.throw(_("Select an Approved Scheme of Work for this exact academic context."), frappe.PermissionError)
    scheme_items = _scheme_items(scheme)
    instructors = _instructor_options(branch, offering, group, subject, reference_date)
    instructor_names = {row["value"] for row in instructors}
    selected_instructor = str(instructor or "").strip()
    if selected_instructor and reference_date and selected_instructor not in instructor_names:
        frappe.throw(_("Select an Instructor with an effective Subject Assignment for the Lesson Date."), frappe.PermissionError)

    list_filters = {
        "school_branch": branch,
        "program_offering": offering,
        "student_group": group,
        "course": subject,
        "instructor": selected_instructor,
        "status": status or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
    }
    plans = _list_plans(list_filters, start=cint(start), page_length=cint(page_length) or 25)
    exact_instructor = ""
    if is_limited_instructor_user():
        exact_instructor = resolve_exact_instructor_for_user(required=False)
    return {
        "filters": {
            **list_filters,
            "scheme_of_work": scheme,
            "lesson_date": reference_date,
        },
        "allowed_branches": branches,
        "offerings": offerings,
        "groups": groups,
        "courses": courses,
        "schemes": schemes,
        "scheme_items": scheme_items,
        "instructors": instructors,
        "plans": plans["rows"],
        "paging": {
            "start": max(cint(start), 0),
            "page_length": plans["page_length"],
            "has_more": plans["has_more"],
        },
        "permissions": {
            "is_manager": _is_manager(),
            "is_limited_instructor": is_limited_instructor_user(),
            "exact_instructor": exact_instructor,
            "can_create": bool(offering and subject and scheme and reference_date and instructors),
        },
    }


@frappe.whitelist(methods=["POST"])
def save_lesson_plan(payload) -> dict:
    require_eduedge_access(feature_key="academics", action="save_lesson_plan")
    data = _parse_payload(payload)
    name = str(data.get("name") or "").strip()
    if name:
        doc = frappe.get_doc(LESSON_DOCTYPE, name)
        if doc.status not in {"Draft", "Returned"}:
            frappe.throw(_("Only Draft or Returned Lesson Plans can be edited."), frappe.ValidationError)
    else:
        doc = frappe.new_doc(LESSON_DOCTYPE)
        doc.status = "Draft"
    for fieldname in EDITABLE_FIELDS:
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))
    if is_limited_instructor_user():
        resolved = resolve_exact_instructor_for_user(required=True)
        if doc.instructor and doc.instructor != resolved:
            frappe.throw(_("You can prepare Lesson Plans only for your Instructor identity."), frappe.PermissionError)
        doc.instructor = resolved
    doc.run_method("validate")
    _context_authorized(doc, write=True)
    if doc.is_new():
        doc.insert(ignore_permissions=not _is_manager())
    else:
        doc.save(ignore_permissions=not _is_manager())
    return _serialize(doc)


def _validate_submission_content(doc) -> None:
    missing = [label for fieldname, label in SUBMISSION_REQUIRED_FIELDS.items() if not str(doc.get(fieldname) or "").strip()]
    if missing:
        frappe.throw(
            _("Complete these Lesson Plan sections before submission: {0}.").format(", ".join(missing)),
            frappe.ValidationError,
        )


@frappe.whitelist(methods=["POST"])
def submit_lesson_plan(name: str) -> dict:
    require_eduedge_access(feature_key="academics", action="submit_lesson_plan")
    doc = frappe.get_doc(LESSON_DOCTYPE, name)
    _context_authorized(doc, write=True)
    if doc.status == "Submitted":
        return _serialize(doc)
    if doc.status not in {"Draft", "Returned"}:
        frappe.throw(_("Only a Draft or Returned Lesson Plan can be submitted."), frappe.ValidationError)
    _validate_submission_content(doc)
    with _lesson_action():
        doc.status = "Submitted"
        doc.submitted_by = frappe.session.user
        doc.submitted_on = now_datetime()
        doc.reviewed_by = None
        doc.reviewed_on = None
        doc.review_comment = None
        doc.return_reason = None
        doc.save(ignore_permissions=not _is_manager())
    doc.add_comment("Info", _("Lesson Plan submitted for Academic Review."))
    return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def approve_lesson_plan(name: str, comment: str | None = None) -> dict:
    require_eduedge_access(feature_key="academics", action="approve_lesson_plan")
    if not _is_manager():
        frappe.throw(_("Only academic management can approve Lesson Plans."), frappe.PermissionError)
    savepoint = "eduedge_lesson_plan_approve"
    frappe.db.savepoint(savepoint)
    try:
        frappe.db.sql("select name from `tabEduEdge Lesson Plan` where name = %s for update", (name,))
        doc = frappe.get_doc(LESSON_DOCTYPE, name)
        doc.check_permission("write")
        assert_branch_access(doc.school_branch)
        if doc.status == "Approved":
            return _serialize(doc)
        if doc.status != "Submitted":
            frappe.throw(_("Only a Submitted Lesson Plan can be approved."), frappe.ValidationError)
        _validate_submission_content(doc)
        with _lesson_action():
            doc.run_method("validate")
            snapshot_lesson_plan_context(doc)
            doc.status = "Approved"
            doc.reviewed_by = frappe.session.user
            doc.reviewed_on = now_datetime()
            doc.review_comment = str(comment or "").strip()
            doc.return_reason = None
            doc.save()
        doc.add_comment("Info", _("Lesson Plan approved; academic context and Scheme item labels snapshotted."))
        return _serialize(doc)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise


@frappe.whitelist(methods=["POST"])
def return_lesson_plan(name: str, reason: str) -> dict:
    require_eduedge_access(feature_key="academics", action="return_lesson_plan")
    if not _is_manager():
        frappe.throw(_("Only academic management can return Lesson Plans for correction."), frappe.PermissionError)
    resolved_reason = str(reason or "").strip()
    if len(resolved_reason) < 3:
        frappe.throw(_("Give a clear reason for returning the Lesson Plan."), frappe.ValidationError)
    doc = frappe.get_doc(LESSON_DOCTYPE, name)
    doc.check_permission("write")
    assert_branch_access(doc.school_branch)
    if doc.status != "Submitted":
        frappe.throw(_("Only a Submitted Lesson Plan can be returned for correction."), frappe.ValidationError)
    with _lesson_action():
        doc.status = "Returned"
        doc.reviewed_by = frappe.session.user
        doc.reviewed_on = now_datetime()
        doc.return_reason = resolved_reason
        doc.review_comment = None
        doc.save()
    doc.add_comment("Info", _("Lesson Plan returned for correction. Reason: {0}").format(resolved_reason))
    return _serialize(doc)
