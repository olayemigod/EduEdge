from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.api.class_arm_session_rollover import (
    execute_selected_class_arm_session_rollover,
    preview_class_arm_session_rollover,
)
from eduedge.api.programme_offerings_safe import save_programme_offering
from eduedge.api.session_launch import _allowed_branches, _get_launch_by_name, _require_manager
from eduedge.education.academic_fields import INSTITUTION_FIELD

MAX_CLASSES = 500
MAX_MATRIX_ROWS = 2500
MAX_SELECTION = 500


def _parse_rows(value: Any, *, label: str) -> list[dict]:
    if isinstance(value, str):
        value = frappe.parse_json(value)
    if not isinstance(value, list):
        frappe.throw(_("Select one or more {0}.").format(label), frappe.ValidationError)
    rows = [row for row in value if isinstance(row, dict)]
    if not rows:
        frappe.throw(_("Select at least one {0}.").format(label), frappe.ValidationError)
    if len(rows) > MAX_SELECTION:
        frappe.throw(
            _("A maximum of {0} {1} can be processed in one action.").format(MAX_SELECTION, label),
            frappe.ValidationError,
        )
    return rows


def _program_rows(institution: str) -> list[dict]:
    if not frappe.has_permission("Program", "read"):
        frappe.throw(_("You are not permitted to view Classes / Programmes."), frappe.PermissionError)
    meta = frappe.get_meta("Program")
    filters = {INSTITUTION_FIELD: institution} if meta.has_field(INSTITUTION_FIELD) else {}
    fields = ["name", "program_name", "program_abbreviation", "department"]
    if meta.has_field(INSTITUTION_FIELD):
        fields.append(INSTITUTION_FIELD)
    rows = frappe.get_list(
        "Program",
        filters=filters,
        fields=fields,
        order_by="department asc, program_name asc, name asc",
        page_length=MAX_CLASSES + 1,
    )
    if len(rows) > MAX_CLASSES:
        frappe.throw(
            _("This Institution has more than {0} Classes / Programmes. Narrow the academic structure before using guided Session preparation.").format(MAX_CLASSES),
            frappe.ValidationError,
        )
    return [dict(row) for row in rows]


def _target_offerings(branch_names: list[str], academic_year: str) -> list[dict]:
    if not branch_names:
        return []
    return [
        dict(row)
        for row in frappe.get_list(
            "EduEdge Program Offering",
            filters={
                "school_branch": ["in", branch_names],
                "academic_year": academic_year,
                "academic_term": ["is", "not set"],
            },
            fields=[
                "name",
                "school_branch",
                "program",
                "academic_year",
                "offering_title",
                "study_mode",
                "delivery_mode",
                "capacity",
                "is_active",
                "admission_enabled",
                "enrollment_enabled",
            ],
            page_length=MAX_MATRIX_ROWS,
        )
    ]


def _source_offerings(branch_names: list[str], academic_year: str | None) -> dict[tuple[str, str], dict]:
    if not branch_names or not academic_year:
        return {}
    rows = frappe.get_list(
        "EduEdge Program Offering",
        filters={
            "school_branch": ["in", branch_names],
            "academic_year": academic_year,
            "academic_term": ["is", "not set"],
        },
        fields=[
            "name",
            "school_branch",
            "program",
            "study_mode",
            "delivery_mode",
            "capacity",
            "is_active",
            "admission_enabled",
            "enrollment_enabled",
        ],
        order_by="modified desc",
        page_length=MAX_MATRIX_ROWS,
    )
    result: dict[tuple[str, str], dict] = {}
    for row in rows:
        result.setdefault((row.school_branch, row.program), dict(row))
    return result


def _class_and_intake_payload(doc, branches: list[dict]) -> tuple[list[dict], list[dict], dict]:
    programs = _program_rows(doc.institution)
    branch_names = [row["name"] for row in branches]
    if len(programs) * len(branches) > MAX_MATRIX_ROWS:
        frappe.throw(
            _("Guided Class Intake preparation is limited to {0} Branch × Class rows at a time.").format(MAX_MATRIX_ROWS),
            frappe.ValidationError,
        )
    offerings = _target_offerings(branch_names, doc.academic_year)
    existing_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in offerings:
        existing_by_key[(row["school_branch"], row["program"])].append(row)
    source_by_key = _source_offerings(branch_names, doc.source_academic_year)

    intake_rows: list[dict] = []
    per_program_existing: dict[str, int] = defaultdict(int)
    for branch in branches:
        for program in programs:
            key = (branch["name"], program["name"])
            existing = existing_by_key.get(key) or []
            source = source_by_key.get(key) or {}
            if existing:
                per_program_existing[program["name"]] += 1
            intake_rows.append(
                {
                    "key": f"{branch['name']}::{program['name']}",
                    "branch": branch["name"],
                    "branch_name": branch.get("branch_name") or branch["name"],
                    "program": program["name"],
                    "program_name": program.get("program_name") or program["name"],
                    "department": program.get("department") or "",
                    "status": "existing" if existing else "missing",
                    "existing_offering": existing[0]["name"] if existing else "",
                    "existing_count": len(existing),
                    "source_offering": source.get("name") or "",
                    "source_capacity": cint(source.get("capacity")),
                    "source_study_mode": source.get("study_mode") or "Full-Time",
                    "source_delivery_mode": source.get("delivery_mode") or "Onsite",
                }
            )

    class_rows = []
    expected_per_class = len(branches)
    for program in programs:
        existing_count = per_program_existing.get(program["name"], 0)
        class_rows.append(
            {
                **program,
                "intended": True,
                "expected_intakes": expected_per_class,
                "existing_intakes": existing_count,
                "missing_intakes": max(expected_per_class - existing_count, 0),
                "ready": bool(expected_per_class and existing_count >= expected_per_class),
            }
        )

    summary = {
        "classes": len(class_rows),
        "branches": len(branches),
        "expected_intakes": len(intake_rows),
        "existing_intakes": sum(1 for row in intake_rows if row["status"] == "existing"),
        "missing_intakes": sum(1 for row in intake_rows if row["status"] == "missing"),
    }
    return class_rows, intake_rows, summary


def _arm_payload(doc, branches: list[dict]) -> tuple[list[dict], dict]:
    if not doc.source_academic_year:
        return [], {
            "source_session": "",
            "destination_session": doc.academic_year,
            "total": 0,
            "ready": 0,
            "existing": 0,
            "blocked": 0,
            "source_students": 0,
            "students_to_carry": 0,
        }

    rows: list[dict] = []
    summary = {
        "source_session": doc.source_academic_year,
        "destination_session": doc.academic_year,
        "total": 0,
        "ready": 0,
        "existing": 0,
        "blocked": 0,
        "source_students": 0,
        "students_to_carry": 0,
    }
    for branch in branches:
        plan = preview_class_arm_session_rollover(
            branch=branch["name"],
            source_academic_year=doc.source_academic_year,
            destination_academic_year=doc.academic_year,
        )
        for row in plan.get("rows") or []:
            rows.append(
                {
                    **row,
                    "branch": branch["name"],
                    "branch_name": branch.get("branch_name") or branch["name"],
                    "key": f"{branch['name']}::{row.get('class_arm_identity') or row.get('source') or len(rows)}",
                }
            )
        branch_summary = plan.get("summary") or {}
        for key in ("total", "ready", "existing", "blocked", "source_students", "students_to_carry"):
            summary[key] += cint(branch_summary.get(key))
    return rows, summary


def _context_for_doc(doc) -> dict:
    branches, institution_branch_count = _allowed_branches(doc.institution)
    classes, intake_rows, intake_summary = _class_and_intake_payload(doc, branches)
    arm_rows, arm_summary = _arm_payload(doc, branches)
    return {
        "launch": {
            "name": doc.name,
            "institution": doc.institution,
            "academic_year": doc.academic_year,
            "source_academic_year": doc.source_academic_year or "",
        },
        "branches": branches,
        "institution_branch_count": institution_branch_count,
        "classes": classes,
        "class_intakes": intake_rows,
        "class_arms": arm_rows,
        "summary": {
            **intake_summary,
            "class_structure_ready": bool(classes),
            "intakes_ready": bool(intake_rows and not intake_summary["missing_intakes"]),
            "arms_total": arm_summary["total"],
            "arms_ready_to_create": arm_summary["ready"],
            "arms_existing": arm_summary["existing"],
            "arms_blocked": arm_summary["blocked"],
            "source_students": arm_summary["source_students"],
            "students_to_carry": arm_summary["students_to_carry"],
            "arms_structure_ready": bool(arm_summary["total"] and not arm_summary["ready"] and not arm_summary["blocked"]),
        },
        "arm_summary": arm_summary,
        "permissions": {
            "can_create_intake": bool(frappe.has_permission("EduEdge Program Offering", "create")),
            "can_create_class_arm": bool(frappe.has_permission("Student Group", "create")),
        },
    }


@frappe.whitelist()
def get_session_structure_context(launch: str) -> dict:
    _require_manager("get_session_structure_context")
    doc = _get_launch_by_name(str(launch or "").strip())
    return _context_for_doc(doc)


@frappe.whitelist(methods=["POST"])
def create_selected_class_intakes(launch: str, selections: Any) -> dict:
    _require_manager("create_selected_class_intakes")
    doc = _get_launch_by_name(str(launch or "").strip())
    if not frappe.has_permission("EduEdge Program Offering", "create"):
        frappe.throw(_("You are not permitted to create Class Intakes."), frappe.PermissionError)
    rows = _parse_rows(selections, label=_("Class Intakes"))
    branches, _total = _allowed_branches(doc.institution)
    allowed_branches = {row["name"] for row in branches}
    programs = {row["name"]: row for row in _program_rows(doc.institution)}
    year = frappe.db.get_value(
        "Academic Year", doc.academic_year, ["year_start_date", "year_end_date"], as_dict=True
    ) or {}
    source_by_key = _source_offerings(list(allowed_branches), doc.source_academic_year)

    created: list[dict] = []
    existing: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for selection in rows:
        branch = str(selection.get("branch") or "").strip()
        program = str(selection.get("program") or "").strip()
        key = (branch, program)
        if not branch or branch not in allowed_branches:
            frappe.throw(_("One selected Branch / Campus is outside this Session Launch scope."), frappe.PermissionError)
        if not program or program not in programs:
            frappe.throw(_("One selected Class / Programme is outside this Institution."), frappe.PermissionError)
        if key in seen:
            continue
        seen.add(key)
        current = frappe.db.get_value(
            "EduEdge Program Offering",
            {
                "school_branch": branch,
                "program": program,
                "academic_year": doc.academic_year,
                "academic_term": ["is", "not set"],
            },
            "name",
        )
        if current:
            existing.append({"branch": branch, "program": program, "name": current})
            continue

        source = source_by_key.get(key) or {}
        result = save_programme_offering(
            school_branch=branch,
            institution=doc.institution,
            program=program,
            academic_year=doc.academic_year,
            study_mode=source.get("study_mode") or "Full-Time",
            delivery_mode=source.get("delivery_mode") or "Onsite",
            capacity=cint(source.get("capacity")),
            is_active=1,
            admission_enabled=cint(source.get("admission_enabled")) if source else 1,
            enrollment_enabled=cint(source.get("enrollment_enabled")) if source else 1,
            start_date=year.get("year_start_date"),
            end_date=year.get("year_end_date"),
        )
        created.append({"branch": branch, "program": program, **result})

    return {
        "created": created,
        "existing": existing,
        "created_count": len(created),
        "existing_count": len(existing),
        "context": _context_for_doc(doc),
    }


@frappe.whitelist(methods=["POST"])
def carry_forward_selected_class_arms(launch: str, selections: Any) -> dict:
    _require_manager("carry_forward_selected_class_arms")
    doc = _get_launch_by_name(str(launch or "").strip())
    if not doc.source_academic_year:
        frappe.throw(_("Select a source Academic Session before carrying Class Arms forward."), frappe.ValidationError)
    if not frappe.has_permission("Student Group", "create"):
        frappe.throw(_("You are not permitted to create Class Arms."), frappe.PermissionError)
    rows = _parse_rows(selections, label=_("Class Arms"))
    branches, _total = _allowed_branches(doc.institution)
    allowed_branches = {row["name"] for row in branches}
    by_branch: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        branch = str(row.get("branch") or "").strip()
        identity = str(row.get("class_arm_identity") or "").strip()
        if branch not in allowed_branches:
            frappe.throw(_("One selected Class Arm belongs to a Branch outside this Session Launch scope."), frappe.PermissionError)
        if not identity:
            frappe.throw(_("One selected Class Arm has no reusable identity."), frappe.ValidationError)
        if identity not in by_branch[branch]:
            by_branch[branch].append(identity)

    results: list[dict] = []
    for branch, identities in by_branch.items():
        results.append(
            {
                "branch": branch,
                "result": execute_selected_class_arm_session_rollover(
                    branch=branch,
                    source_academic_year=doc.source_academic_year,
                    destination_academic_year=doc.academic_year,
                    class_arm_identities=identities,
                ),
            }
        )
    return {
        "results": results,
        "created_count": sum(cint(row["result"].get("created_count")) for row in results),
        "existing_count": sum(cint(row["result"].get("existing_count")) for row in results),
        "blocked_count": sum(cint(row["result"].get("blocked_count")) for row in results),
        "context": _context_for_doc(doc),
    }
