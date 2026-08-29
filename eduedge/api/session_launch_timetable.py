from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, get_time

from eduedge.api import teaching_schedule as teaching
from eduedge.api.session_launch_delivery import _context, _launch, _validate_offering
from eduedge.education import academic_operations
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.instructor_assignments import assert_schedule_instructor_assignment
from eduedge.education.schedule_conflicts import validate_course_schedule_conflicts

MAX_TIMETABLE_ROWS = 250
RESOURCE_LOCK_ORDER = ("Student Group", "Instructor", "Room")
RESOURCE_LABELS = (
    ("student_group", "Class Arm / Student Group"),
    ("instructor", "Instructor"),
    ("room", "Room"),
)


def _normalise(value: Any) -> str:
    return " ".join(str(value or "").split())


def _planner_launch(launch: str, action: str):
    doc = _launch(launch, action)
    if not frappe.has_permission("Course Schedule", "create"):
        frappe.throw(_("You are not permitted to create Teaching Schedules."), frappe.PermissionError)
    return doc


def _parse_rows(rows) -> list[dict]:
    parsed = frappe.parse_json(rows) if isinstance(rows, str) else rows
    if not isinstance(parsed, list) or not parsed:
        frappe.throw(_("Prepare at least one timetable row before continuing."), frappe.ValidationError)
    if len(parsed) > MAX_TIMETABLE_ROWS:
        frappe.throw(
            _("A timetable batch may contain at most {0} rows. Split this plan into smaller batches.").format(
                MAX_TIMETABLE_ROWS
            ),
            frappe.ValidationError,
        )
    result = []
    for index, source in enumerate(parsed, 1):
        if not isinstance(source, dict):
            frappe.throw(_("Timetable row {0} is invalid.").format(index), frappe.ValidationError)
        result.append(
            {
                "row_no": index,
                "branch": _normalise(source.get("branch")),
                "program_offering": _normalise(source.get("program_offering")),
                "student_group": _normalise(source.get("student_group")),
                "course": _normalise(source.get("course")),
                "instructor": _normalise(source.get("instructor")),
                "room": _normalise(source.get("room")),
                "schedule_date": _normalise(source.get("schedule_date")),
                "from_time": _normalise(source.get("from_time")),
                "to_time": _normalise(source.get("to_time")),
            }
        )
    return result


def _validate_required(row: dict) -> None:
    labels = {
        "program_offering": _("Class Intake"),
        "student_group": _("Class Arm / Student Group"),
        "course": _("Subject / Course"),
        "instructor": _("Instructor"),
        "room": _("Room"),
        "schedule_date": _("Schedule Date"),
        "from_time": _("From Time"),
        "to_time": _("To Time"),
    }
    missing = [label for field, label in labels.items() if not row.get(field)]
    if missing:
        frappe.throw(
            _("Timetable row {0} is missing: {1}.").format(row["row_no"], ", ".join(missing)),
            frappe.ValidationError,
        )


def _validate_time_window(row: dict) -> None:
    try:
        start = get_time(row["from_time"])
        end = get_time(row["to_time"])
    except Exception:
        frappe.throw(_("Enter valid From Time and To Time values."), frappe.ValidationError)
    if start >= end:
        frappe.throw(_("To Time must be later than From Time."), frappe.ValidationError)


def _candidate_doc(launch_doc, row: dict):
    _validate_required(row)
    _validate_time_window(row)
    offering = _validate_offering(launch_doc, row["program_offering"])
    branch = row.get("branch") or offering["school_branch"]
    if branch != offering["school_branch"]:
        frappe.throw(_("Timetable Branch must match the selected Class Intake Branch."), frappe.ValidationError)

    teaching._validate_offering_date(branch, row["program_offering"], row["schedule_date"])
    teaching._schedule_group(branch, row["program_offering"], row["student_group"])

    room_branch = frappe.db.get_value("Room", row["room"], BRANCH_FIELD)
    if not room_branch or room_branch != branch:
        frappe.throw(_("Select a Room belonging to this Branch / Campus."), frappe.ValidationError)

    candidate = frappe.get_doc(
        {
            "doctype": "Course Schedule",
            "student_group": row["student_group"],
            "instructor": row["instructor"],
            "course": row["course"],
            "room": row["room"],
            "schedule_date": str(getdate(row["schedule_date"])),
            "from_time": row["from_time"],
            "to_time": row["to_time"],
            BRANCH_FIELD: branch,
        }
    )

    # Preview uses the same EduEdge academic, assignment and native Course Schedule
    # validation that insertion uses, but does not write a document.
    academic_operations.before_validate_course_schedule(candidate)
    assert_schedule_instructor_assignment(candidate)
    return candidate


def _exact_existing(candidate) -> str | None:
    filters = {
        "student_group": candidate.student_group,
        "instructor": candidate.instructor,
        "course": candidate.course,
        "room": candidate.room,
        "schedule_date": candidate.schedule_date,
        "from_time": candidate.from_time,
        "to_time": candidate.to_time,
        BRANCH_FIELD: candidate.get(BRANCH_FIELD),
        "docstatus": ["!=", 2],
    }
    return frappe.db.exists("Course Schedule", filters)


def _candidate_payload(candidate, row_no: int) -> dict:
    return {
        "row_no": row_no,
        "branch": candidate.get(BRANCH_FIELD),
        "student_group": candidate.student_group,
        "course": candidate.course,
        "instructor": candidate.instructor,
        "room": candidate.room,
        "schedule_date": str(getdate(candidate.schedule_date)),
        "from_time": str(candidate.from_time or ""),
        "to_time": str(candidate.to_time or ""),
    }


def _signature(candidate) -> tuple:
    return (
        candidate.get(BRANCH_FIELD),
        candidate.student_group,
        candidate.course,
        candidate.instructor,
        candidate.room,
        str(getdate(candidate.schedule_date)),
        str(candidate.from_time or ""),
        str(candidate.to_time or ""),
    )


def _overlaps(left, right) -> bool:
    return get_time(left.from_time) < get_time(right.to_time) and get_time(left.to_time) > get_time(right.from_time)


def _batch_conflict(candidate, accepted: list) -> str | None:
    candidate_date = getdate(candidate.schedule_date)
    for other in accepted:
        if getdate(other.schedule_date) != candidate_date or not _overlaps(candidate, other):
            continue
        for fieldname, label in RESOURCE_LABELS:
            value = candidate.get(fieldname)
            if value and value == other.get(fieldname):
                return _("Conflicts inside this batch for {0} {1} ({2}–{3}).").format(
                    _(label),
                    value,
                    other.from_time,
                    other.to_time,
                )
    return None


def _validate_candidate(candidate) -> None:
    # Native Frappe Education validation remains authoritative. EduEdge then closes
    # the known exact-start overlap gap and checks Assessment Plan conflicts.
    candidate.run_method("validate")
    validate_course_schedule_conflicts(candidate)


def _preview(launch_doc, rows: list[dict]) -> dict:
    results = []
    accepted = []
    seen_signatures = set()

    for row in rows:
        try:
            candidate = _candidate_doc(launch_doc, row)
            payload = _candidate_payload(candidate, row["row_no"])
            signature = _signature(candidate)
            if signature in seen_signatures:
                results.append(
                    {
                        **payload,
                        "status": "Blocked",
                        "reason": _("Duplicate timetable row inside this batch."),
                        "existing_name": "",
                    }
                )
                continue
            seen_signatures.add(signature)

            existing_name = _exact_existing(candidate)
            if existing_name:
                results.append(
                    {
                        **payload,
                        "status": "Existing",
                        "reason": _("This exact Teaching Schedule already exists; retry will not duplicate it."),
                        "existing_name": existing_name,
                    }
                )
                continue

            batch_reason = _batch_conflict(candidate, accepted)
            if batch_reason:
                results.append(
                    {
                        **payload,
                        "status": "Blocked",
                        "reason": batch_reason,
                        "existing_name": "",
                    }
                )
                continue

            _validate_candidate(candidate)
            accepted.append(candidate)
            results.append(
                {
                    **payload,
                    "status": "Ready",
                    "reason": _("Validated and ready to create."),
                    "existing_name": "",
                }
            )
        except frappe.PermissionError:
            raise
        except (frappe.ValidationError, frappe.DoesNotExistError) as exc:
            results.append(
                {
                    **row,
                    "status": "Blocked",
                    "reason": _normalise(exc),
                    "existing_name": "",
                }
            )

    summary = {
        "total": len(results),
        "ready": sum(1 for row in results if row["status"] == "Ready"),
        "existing": sum(1 for row in results if row["status"] == "Existing"),
        "blocked": sum(1 for row in results if row["status"] == "Blocked"),
    }
    return {
        "rows": results,
        "summary": summary,
        "can_create": bool(summary["ready"] and not summary["blocked"]),
        "idempotent": bool(not summary["blocked"]),
    }


def _lock_planner_resources(rows: list[dict]) -> None:
    values_by_doctype = {
        "Student Group": {row.get("student_group") for row in rows if row.get("student_group")},
        "Instructor": {row.get("instructor") for row in rows if row.get("instructor")},
        "Room": {row.get("room") for row in rows if row.get("room")},
    }
    # Every planner request locks the same resource categories in the same order.
    # This serialises overlapping Class/Instructor/Room plans without a shadow ledger.
    for doctype in RESOURCE_LOCK_ORDER:
        for name in sorted(values_by_doctype[doctype]):
            frappe.db.sql(f"select name from `tab{doctype}` where name = %s for update", (name,))


@frappe.whitelist(methods=["POST"])
def preview_session_timetable(launch: str, rows) -> dict:
    launch_doc = _planner_launch(launch, "preview_session_timetable")
    parsed = _parse_rows(rows)
    return _preview(launch_doc, parsed)


@frappe.whitelist(methods=["POST"])
def create_session_timetable(launch: str, rows) -> dict:
    launch_doc = _planner_launch(launch, "create_session_timetable")
    parsed = _parse_rows(rows)
    _lock_planner_resources(parsed)

    preview = _preview(launch_doc, parsed)
    if preview["summary"]["blocked"]:
        return {
            "status": "Blocked",
            "created": [],
            "preview": preview,
            "context": _context(launch_doc),
        }

    created = []
    for row in preview["rows"]:
        if row["status"] != "Ready":
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Course Schedule",
                "student_group": row["student_group"],
                "instructor": row["instructor"],
                "course": row["course"],
                "room": row["room"],
                "schedule_date": row["schedule_date"],
                "from_time": row["from_time"],
                "to_time": row["to_time"],
                BRANCH_FIELD: row["branch"],
            }
        )
        # No permission bypass and no manual commit. Normal Frappe hooks revalidate
        # the exact academic context and conflicts inside the request transaction.
        doc.insert()
        created.append(doc.name)

    return {
        "status": "Created" if created else "No Change",
        "created": created,
        "created_count": len(created),
        "existing_count": preview["summary"]["existing"],
        "preview": preview,
        "context": _context(launch_doc),
    }
