from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api.admission_resource import save_admission
from eduedge.api.session_launch import _allowed_branches, _get_launch_by_name, _require_manager
from eduedge.api.student_enrollments import save_student_enrollment
from eduedge.api.student_progression import (
    finalize_progression_batch,
    get_progression_destination_options,
    get_student_progression_page,
    prepare_progression_batch,
)
from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.enrollment_progression_fields import (
    PROGRESSION_OUTCOME_FIELD,
    PROGRESSION_SOURCE_FIELD,
)

MAX_RETURNING_STUDENTS = 1000
MAX_APPLICANTS = 1000
MAX_ENROLLMENTS = 2000
MAX_ADMISSIONS = 500
MAX_LINK_RESULTS = 30
TARGET_OUTCOMES = {"Promote", "Repeat", "Transfer"}
DECIDED_STATUSES = {
    "Promoted",
    "Repeated",
    "Transferred",
    "Completed",
    "Graduated",
    "Withdrawn",
    "Deferred",
    "Suspended",
    "Cancelled",
}


def _parse_json(value: Any) -> dict:
    if isinstance(value, str):
        value = frappe.parse_json(value)
    return value if isinstance(value, dict) else {}


def _launch(launch: str):
    _require_manager("session_launch_learners")
    return _get_launch_by_name(str(launch or "").strip())


def _branch_scope(doc) -> tuple[list[dict], dict[str, dict]]:
    branches, _total = _allowed_branches(doc.institution)
    return branches, {row["name"]: row for row in branches}


def _assert_branch(doc, branch: str) -> dict:
    _branches, by_name = _branch_scope(doc)
    row = by_name.get(str(branch or "").strip())
    if not row:
        frappe.throw(_("Select a Branch / Campus inside this Session Launch scope."), frappe.PermissionError)
    return row


def _assert_source_in_launch(doc, source_enrollment: str):
    source = frappe.get_doc("Program Enrollment", str(source_enrollment or "").strip())
    source.check_permission("read")
    if source.docstatus != 1:
        frappe.throw(_("Student Progression requires a submitted source Enrollment."), frappe.ValidationError)
    if not doc.source_academic_year or source.academic_year != doc.source_academic_year:
        frappe.throw(_("The selected source Enrollment does not belong to the Session Launch source Academic Session."), frappe.ValidationError)
    if source.meta.has_field(INSTITUTION_FIELD) and source.get(INSTITUTION_FIELD) != doc.institution:
        frappe.throw(_("The selected source Enrollment belongs to another Institution."), frappe.PermissionError)
    if source.meta.has_field(BRANCH_FIELD):
        _assert_branch(doc, source.get(BRANCH_FIELD))
    return source


def _progression_state(row: dict) -> str:
    status = str(row.get("current_status") or "Active")
    if status in DECIDED_STATUSES:
        return "finalized"
    planned = row.get("planned_target") or {}
    if planned:
        return "target_submitted" if cint(planned.get("docstatus")) == 1 else "draft_prepared"
    return "decision_required"


def _progression_rows(doc, branches: list[dict]) -> tuple[list[dict], dict]:
    summary = {
        "source_enrollments": 0,
        "decision_required": 0,
        "draft_prepared": 0,
        "target_submitted": 0,
        "finalized": 0,
        "review_required": 0,
    }
    if not doc.source_academic_year:
        return [], summary

    rows: list[dict] = []
    for branch in branches:
        start = 0
        while len(rows) < MAX_RETURNING_STUDENTS:
            page = get_student_progression_page(
                branch=branch["name"],
                source_academic_year=doc.source_academic_year,
                start=start,
                page_length=100,
            )
            page_rows = page.get("rows") or []
            for source in page_rows:
                row = dict(source)
                row["branch"] = branch["name"]
                row["branch_name"] = branch.get("branch_name") or branch["name"]
                row["launch_state"] = _progression_state(row)
                rows.append(row)
                summary[row["launch_state"]] += 1
                if (row.get("recommendation") or {}).get("label") in {"Review Required", "Manual Decision Required"}:
                    summary["review_required"] += 1
                if len(rows) >= MAX_RETURNING_STUDENTS:
                    break
            if len(rows) >= MAX_RETURNING_STUDENTS or not (page.get("paging") or {}).get("has_more"):
                break
            start = cint((page.get("paging") or {}).get("next_start"))
    summary["source_enrollments"] = len(rows)
    return rows, summary


def _target_offerings(doc, branches: list[dict]) -> list[dict]:
    branch_names = [row["name"] for row in branches]
    if not branch_names:
        return []
    return [
        dict(row)
        for row in frappe.get_list(
            "EduEdge Program Offering",
            filters={
                "school_branch": ["in", branch_names],
                "academic_year": doc.academic_year,
                "academic_term": ["is", "not set"],
                "is_active": 1,
            },
            fields=[
                "name",
                "offering_title",
                "school_branch",
                "institution",
                "program",
                "academic_year",
                "capacity",
                "admission_enabled",
                "enrollment_enabled",
            ],
            order_by="school_branch asc, program asc",
            page_length=2000,
        )
    ]


def _admission_rows(doc, branches: list[dict], offerings: list[dict]) -> tuple[list[dict], list[dict], dict]:
    branch_names = [row["name"] for row in branches]
    admission_meta = frappe.get_meta("Student Admission")
    fields = ["name", "title", "academic_year", "docstatus", "admission_start_date", "admission_end_date", "enable_admission_application"]
    if admission_meta.has_field(BRANCH_FIELD):
        fields.append(BRANCH_FIELD)
    filters: dict[str, Any] = {"academic_year": doc.academic_year, "docstatus": ["<", 2]}
    if admission_meta.has_field(BRANCH_FIELD):
        filters[BRANCH_FIELD] = ["in", branch_names]
    admissions = frappe.get_list(
        "Student Admission",
        filters=filters,
        fields=fields,
        order_by="creation desc",
        page_length=MAX_ADMISSIONS,
    ) if branch_names else []

    admission_rows: list[dict] = []
    by_branch: dict[str, list[dict]] = defaultdict(list)
    for row in admissions:
        doc_row = frappe.get_doc("Student Admission", row.name)
        programs = [child.program for child in (doc_row.get("program_details") or []) if child.program]
        data = {**dict(row), "programs": programs, "status_label": "Submitted" if cint(row.docstatus) == 1 else "Draft"}
        branch = data.get(BRANCH_FIELD) or ""
        admission_rows.append(data)
        if branch:
            by_branch[branch].append(data)

    admission_programs: dict[str, list[dict]] = defaultdict(list)
    for offering in offerings:
        if cint(offering.get("admission_enabled")):
            admission_programs[offering["school_branch"]].append(offering)

    branch_rows: list[dict] = []
    for branch in branches:
        programs = admission_programs.get(branch["name"], [])
        cycles = by_branch.get(branch["name"], [])
        required = bool(programs)
        branch_rows.append(
            {
                "branch": branch["name"],
                "branch_name": branch.get("branch_name") or branch["name"],
                "programs": programs,
                "program_count": len(programs),
                "admissions": cycles,
                "admission_count": len(cycles),
                "required": required,
                "status": "ready" if cycles else "missing" if required else "not_required",
            }
        )

    summary = {
        "admission_branches_required": sum(1 for row in branch_rows if row["required"]),
        "admission_branches_ready": sum(1 for row in branch_rows if row["required"] and row["admission_count"]),
        "admission_cycles": len(admission_rows),
    }
    return admission_rows, branch_rows, summary


def _applicant_payload(doc, branches: list[dict]) -> tuple[list[dict], dict]:
    if not frappe.db.exists("DocType", "Student Applicant"):
        return [], {"total": 0, "applied": 0, "approved": 0, "admitted": 0, "rejected": 0}
    meta = frappe.get_meta("Student Applicant")
    branch_names = [row["name"] for row in branches]
    fields = ["name", "title", "program", "application_status", "application_date"]
    for fieldname in (BRANCH_FIELD, "academic_year", "student"):
        if meta.has_field(fieldname):
            fields.append(fieldname)
    filters: dict[str, Any] = {}
    if meta.has_field(BRANCH_FIELD):
        filters[BRANCH_FIELD] = ["in", branch_names]
    if meta.has_field("academic_year"):
        filters["academic_year"] = doc.academic_year
    rows = frappe.get_list(
        "Student Applicant",
        filters=filters,
        fields=fields,
        order_by="creation desc",
        page_length=MAX_APPLICANTS,
    ) if branch_names else []
    counts = Counter(str(row.get("application_status") or "Applied") for row in rows)
    return [dict(row) for row in rows], {
        "total": len(rows),
        "applied": counts.get("Applied", 0),
        "approved": counts.get("Approved", 0),
        "admitted": counts.get("Admitted", 0),
        "rejected": counts.get("Rejected", 0),
    }


def _assignment_map(doc, branches: list[dict]) -> dict[tuple[str, str, str], list[str]]:
    branch_names = [row["name"] for row in branches]
    group_meta = frappe.get_meta("Student Group")
    if not branch_names or not group_meta.has_field(BRANCH_FIELD):
        return {}
    fields = ["name", "program", BRANCH_FIELD]
    if group_meta.has_field(OFFERING_FIELD):
        fields.append(OFFERING_FIELD)
    groups = frappe.get_list(
        "Student Group",
        filters={BRANCH_FIELD: ["in", branch_names], "academic_year": doc.academic_year, "disabled": 0},
        fields=fields,
        page_length=2000,
    )
    if not groups:
        return {}
    by_name = {row.name: row for row in groups}
    memberships = frappe.get_all(
        "Student Group Student",
        filters={"parent": ["in", list(by_name)]},
        fields=["parent", "student", "active"],
        page_length=0,
    )
    result: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for membership in memberships:
        if "active" in membership and not cint(membership.active):
            continue
        group = by_name.get(membership.parent)
        if not group or not membership.student:
            continue
        key = (membership.student, group.get(BRANCH_FIELD), group.get("program"))
        result[key].append(group.name)
    return result


def _enrollment_payload(doc, branches: list[dict]) -> tuple[list[dict], dict]:
    branch_names = [row["name"] for row in branches]
    meta = frappe.get_meta("Program Enrollment")
    fields = ["name", "student", "student_name", "program", "academic_year", "docstatus"]
    for fieldname in (BRANCH_FIELD, OFFERING_FIELD, PROGRESSION_SOURCE_FIELD, PROGRESSION_OUTCOME_FIELD):
        if meta.has_field(fieldname):
            fields.append(fieldname)
    filters: dict[str, Any] = {"academic_year": doc.academic_year, "docstatus": ["<", 2]}
    if meta.has_field(BRANCH_FIELD):
        filters[BRANCH_FIELD] = ["in", branch_names]
    rows = frappe.get_list(
        "Program Enrollment",
        filters=filters,
        fields=fields,
        order_by="creation desc",
        page_length=MAX_ENROLLMENTS,
    ) if branch_names else []
    assignments = _assignment_map(doc, branches)
    result: list[dict] = []
    for source in rows:
        row = dict(source)
        key = (row.get("student"), row.get(BRANCH_FIELD), row.get("program"))
        groups = assignments.get(key) or []
        row["assigned_groups"] = groups
        row["assigned"] = bool(groups)
        row["status_label"] = "Submitted" if cint(row.get("docstatus")) == 1 else "Draft"
        row["source_type"] = "Returning / Progression" if row.get(PROGRESSION_SOURCE_FIELD) else "New / Direct"
        result.append(row)
    summary = {
        "target_enrollments": len(result),
        "draft_enrollments": sum(1 for row in result if cint(row.get("docstatus")) == 0),
        "submitted_enrollments": sum(1 for row in result if cint(row.get("docstatus")) == 1),
        "submitted_unassigned": sum(1 for row in result if cint(row.get("docstatus")) == 1 and not row.get("assigned")),
        "progression_enrollments": sum(1 for row in result if row.get(PROGRESSION_SOURCE_FIELD)),
        "direct_enrollments": sum(1 for row in result if not row.get(PROGRESSION_SOURCE_FIELD)),
    }
    return result, summary


def _context(doc) -> dict:
    branches, by_name = _branch_scope(doc)
    offerings = _target_offerings(doc, branches)
    progression_rows, progression_summary = _progression_rows(doc, branches)
    admissions, admission_branches, admission_summary = _admission_rows(doc, branches, offerings)
    applicants, applicant_summary = _applicant_payload(doc, branches)
    enrollments, enrollment_summary = _enrollment_payload(doc, branches)
    return {
        "launch": {
            "name": doc.name,
            "institution": doc.institution,
            "academic_year": doc.academic_year,
            "source_academic_year": doc.source_academic_year or "",
        },
        "branches": branches,
        "branch_map": by_name,
        "target_offerings": offerings,
        "progression": progression_rows,
        "admission_cycles": admissions,
        "admission_branches": admission_branches,
        "applicants": applicants,
        "enrollments": enrollments,
        "summary": {
            **progression_summary,
            **admission_summary,
            **{f"applicants_{key}": value for key, value in applicant_summary.items()},
            **enrollment_summary,
            "progression_ready": bool(
                not progression_rows
                or (
                    progression_summary["decision_required"] == 0
                    and progression_summary["draft_prepared"] == 0
                    and progression_summary["target_submitted"] == 0
                )
            ),
            "admissions_ready": bool(
                admission_summary["admission_branches_required"] == admission_summary["admission_branches_ready"]
            ),
        },
        "permissions": {
            "can_prepare_progression": bool(frappe.has_permission("Program Enrollment", "create")),
            "can_finalize_progression": bool(frappe.has_permission("EduEdge Enrollment Status Log", "create")),
            "can_create_admission": bool(frappe.has_permission("Student Admission", "create")),
            "can_create_enrollment": bool(frappe.has_permission("Program Enrollment", "create")),
        },
    }


@frappe.whitelist()
def get_session_learner_context(launch: str) -> dict:
    return _context(_launch(launch))


@frappe.whitelist()
def get_guided_progression_options(
    launch: str,
    source_enrollment: str,
    outcome: str,
    target_branch: str | None = None,
) -> dict:
    doc = _launch(launch)
    _assert_source_in_launch(doc, source_enrollment)
    outcome = str(outcome or "").strip()
    if outcome not in TARGET_OUTCOMES:
        frappe.throw(_("Guided destination preparation supports Promote, Repeat or Transfer."), frappe.ValidationError)
    return get_progression_destination_options(
        source_enrollment=source_enrollment,
        outcome=outcome,
        destination_academic_year=doc.academic_year,
        target_branch=str(target_branch or "").strip() or None,
    )


@frappe.whitelist(methods=["POST"])
def prepare_guided_progression(
    launch: str,
    source_enrollment: str,
    outcome: str,
    reason: str,
    target_branch: str | None = None,
    target_student_group: str | None = None,
) -> dict:
    doc = _launch(launch)
    _assert_source_in_launch(doc, source_enrollment)
    outcome = str(outcome or "").strip()
    if outcome not in TARGET_OUTCOMES:
        frappe.throw(_("Guided Session Launch prepares destination drafts only for Promote, Repeat or Transfer."), frappe.ValidationError)
    result = prepare_progression_batch(
        {
            "source_enrollments": [source_enrollment],
            "outcome": outcome,
            "destination_academic_year": doc.academic_year,
            "target_branch": str(target_branch or "").strip() or None,
            "target_student_group": str(target_student_group or "").strip() or None,
            "reason": str(reason or "").strip(),
        }
    )
    # Deliberately no submit: Program Enrollment remains Draft until normal approval/submission.
    return {"result": result, "context": _context(doc)}


@frappe.whitelist(methods=["POST"])
def finalize_guided_progression(
    launch: str,
    source_enrollment: str,
    outcome: str,
    reason: str,
    effective_date: str | None = None,
) -> dict:
    doc = _launch(launch)
    _assert_source_in_launch(doc, source_enrollment)
    result = finalize_progression_batch(
        {
            "source_enrollments": [source_enrollment],
            "outcome": str(outcome or "").strip(),
            "reason": str(reason or "").strip(),
            "effective_date": str(effective_date or "").strip() or None,
        }
    )
    return {"result": result, "context": _context(doc)}


def _admission_enabled_programs(doc, branch: str) -> set[str]:
    return {
        row.program
        for row in frappe.get_list(
            "EduEdge Program Offering",
            filters={
                "school_branch": branch,
                "academic_year": doc.academic_year,
                "academic_term": ["is", "not set"],
                "is_active": 1,
                "admission_enabled": 1,
            },
            fields=["program"],
            page_length=1000,
        )
        if row.program
    }


@frappe.whitelist(methods=["POST"])
def create_guided_admission_cycle(
    launch: str,
    branch: str,
    title: str,
    programs: Any,
    admission_start_date: str | None = None,
    admission_end_date: str | None = None,
    enable_admission_application: int = 0,
    published: int = 0,
) -> dict:
    doc = _launch(launch)
    _assert_branch(doc, branch)
    if isinstance(programs, str):
        programs = frappe.parse_json(programs)
    selected = list(dict.fromkeys(str(value or "").strip() for value in (programs or []) if str(value or "").strip()))
    allowed = _admission_enabled_programs(doc, branch)
    if not selected:
        frappe.throw(_("Select at least one admission-enabled Class / Programme."), frappe.ValidationError)
    if any(program not in allowed for program in selected):
        frappe.throw(_("One selected Class / Programme is not admission-enabled for this Branch and Academic Session."), frappe.ValidationError)
    result = save_admission(
        {
            "title": str(title or "").strip(),
            "academic_year": doc.academic_year,
            BRANCH_FIELD: branch,
            "admission_start_date": admission_start_date,
            "admission_end_date": admission_end_date,
            "published": cint(published),
            "enable_admission_application": cint(enable_admission_application),
            "admission_programs": selected,
        }
    )
    return {"result": result, "context": _context(doc)}


def _assert_target_offering(doc, branch: str, offering: str) -> None:
    row = frappe.db.get_value(
        "EduEdge Program Offering",
        offering,
        ["school_branch", "institution", "academic_year", "academic_term", "is_active", "enrollment_enabled"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Selected Class Intake / Programme Offering does not exist."), frappe.DoesNotExistError)
    if (
        row.school_branch != branch
        or row.institution != doc.institution
        or row.academic_year != doc.academic_year
        or row.academic_term
        or not cint(row.is_active)
        or not cint(row.enrollment_enabled)
    ):
        frappe.throw(_("Select an active destination-session Class Intake for this Branch."), frappe.ValidationError)


def _assert_not_returning_student(doc, student: str) -> None:
    if not doc.source_academic_year:
        return
    filters: dict[str, Any] = {
        "student": student,
        "academic_year": doc.source_academic_year,
        "docstatus": 1,
    }
    meta = frappe.get_meta("Program Enrollment")
    if meta.has_field(INSTITUTION_FIELD):
        filters[INSTITUTION_FIELD] = doc.institution
    if frappe.db.exists("Program Enrollment", filters):
        frappe.throw(
            _("This is a returning Student with a submitted source-session Enrollment. Use Student Progression instead of creating a direct destination Enrollment."),
            frappe.ValidationError,
        )


@frappe.whitelist(methods=["POST"])
def create_guided_enrollment_draft(
    launch: str,
    branch: str,
    student: str,
    offering: str,
) -> dict:
    doc = _launch(launch)
    _assert_branch(doc, branch)
    _assert_target_offering(doc, branch, offering)
    _assert_not_returning_student(doc, student)
    result = save_student_enrollment(
        {
            "student": str(student or "").strip(),
            "branch": branch,
            "offering": offering,
        },
        submit=0,
    )
    # Deliberately draft-first: Session Launch never submits Program Enrollment here.
    return {"result": result, "context": _context(doc)}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def search_launch_students(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: Any,
) -> list[list[str]]:
    filters = _parse_json(filters)
    doc = _launch(str(filters.get("launch") or ""))
    branch = str(filters.get("branch") or "").strip()
    if branch:
        _assert_branch(doc, branch)
    branches, _by_name = _branch_scope(doc)
    branch_names = [row["name"] for row in branches]
    if not branch_names:
        return []
    needle = f"%{str(txt or '').strip()}%"
    rows = frappe.get_list(
        "Student",
        filters={BRANCH_FIELD: ["in", branch_names], "enabled": 1},
        or_filters={"name": ["like", needle], "student_name": ["like", needle]},
        fields=["name", "student_name", BRANCH_FIELD],
        order_by="student_name asc, name asc",
        start=max(cint(start), 0),
        page_length=min(max(cint(page_len), 1), MAX_LINK_RESULTS),
    )
    return [[row.name, row.student_name or row.name, row.get(BRANCH_FIELD) or ""] for row in rows]
