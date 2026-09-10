from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, nowdate

from eduedge.api.scheme_of_work import _context_authorized, _is_manager
from eduedge.education.instructor_assignment_capabilities import assignment_capability_enforcement_enabled
from eduedge.education.instructor_scope import (
	get_active_instructor_names_for_user,
	is_limited_instructor_user,
)
from eduedge.education.offerings import assert_branch_access
from eduedge.education.teaching_assignments import CLASS_ARM_SCOPE, CLASS_SCOPE, COURSE_REQUIRED_TYPES
from eduedge.eduedge.doctype.eduedge_scheme_delivery_log.eduedge_scheme_delivery_log import (
	DELIVERY_ACTION_FLAG,
	DELIVERY_STATUSES,
)
from eduedge.platform.access import require_eduedge_access

LOG_DOCTYPE = "EduEdge Scheme Delivery Log"
SCHEME_DOCTYPE = "EduEdge Scheme of Work"
LESSON_DOCTYPE = "EduEdge Lesson Plan"
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
ALLOWED_EVIDENCE_EXTENSIONS = {
	".jpg", ".jpeg", ".png", ".webp", ".pdf",
	".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
}
STATUS_TRANSITIONS = {
	"": {"Started", "Completed", "Deferred"},
	"Started": {"Progress Update", "Completed", "Deferred"},
	"Progress Update": {"Progress Update", "Completed", "Deferred"},
	"Deferred": {"Resumed"},
	"Resumed": {"Progress Update", "Completed", "Deferred"},
	"Completed": set(),
}


def _scheme_item(scheme, item_reference: str):
	item = next((row for row in scheme.get("items") or [] if row.name == item_reference), None)
	if not item:
		frappe.throw(_("Select a valid Scheme item."), frappe.ValidationError)
	return item


def _assignment_matches_scope(row, student_group: str) -> bool:
	scope = row.get("assignment_scope") or CLASS_ARM_SCOPE
	if scope == CLASS_SCOPE:
		return True
	return bool(student_group and scope == CLASS_ARM_SCOPE and row.get("student_group") == student_group)


def _eligible_assignment_rows(scheme, delivered_on, *, instructor: str | None = None) -> list[dict]:
	date = getdate(delivered_on or nowdate())
	filters = {
		"school_branch": scheme.school_branch,
		"program_offering": scheme.program_offering,
		"course": scheme.course,
		"assignment_type": ["in", sorted(COURSE_REQUIRED_TYPES)],
		"enabled": 1,
	}
	if instructor:
		filters["instructor"] = instructor
	rows = frappe.get_all(
		"EduEdge Instructor Assignment",
		filters=filters,
		fields=[
			"name", "assignment_title", "instructor", "instructor_name", "assignment_scope",
			"student_group", "valid_from", "valid_to", "can_view_subject_content",
		],
		order_by="valid_from desc, modified desc",
		limit_page_length=100,
	)
	return [
		dict(row)
		for row in rows
		if _assignment_matches_scope(row, scheme.student_group or "")
		and (not row.valid_from or getdate(row.valid_from) <= date)
		and (not row.valid_to or getdate(row.valid_to) >= date)
		and frappe.db.get_value("Instructor", row.instructor, "status") == "Active"
	]


def _exact_limited_instructor() -> str:
	instructors = get_active_instructor_names_for_user()
	if len(instructors) != 1:
		frappe.throw(
			_("Your User account must resolve to exactly one active Instructor before Scheme delivery can be used."),
			frappe.PermissionError,
		)
	return instructors[0]


def _resolve_delivery_assignment(scheme, delivered_on, instructor: str | None = None) -> dict:
	assert_branch_access(scheme.school_branch)
	requested_instructor = str(instructor or "").strip()
	limited = is_limited_instructor_user()
	if limited:
		exact_instructor = _exact_limited_instructor()
		if requested_instructor and requested_instructor != exact_instructor:
			frappe.throw(_("You cannot log Scheme delivery for another Instructor."), frappe.PermissionError)
		requested_instructor = exact_instructor
	elif _is_manager():
		if not requested_instructor:
			frappe.throw(_("Select the Instructor who delivered this Scheme item."), frappe.ValidationError)
	else:
		frappe.throw(_("You are not permitted to log Scheme delivery."), frappe.PermissionError)

	rows = _eligible_assignment_rows(scheme, delivered_on, instructor=requested_instructor)
	if not rows:
		frappe.throw(
			_("The selected Instructor has no effective Subject Instructor Assignment for this Scheme's Branch, Class, Class Arm, Subject and Delivery Date."),
			frappe.PermissionError,
		)
	row = rows[0]
	if limited and assignment_capability_enforcement_enabled() and not cint(row.get("can_view_subject_content")):
		frappe.throw(
			_("Your exact Instructor Assignment does not grant View Subject Content for this Scheme delivery context."),
			frappe.PermissionError,
		)
	return row


def _lesson_plan_matches_scheme(lesson, scheme, item_reference: str, delivered_on, instructor: str) -> bool:
	if lesson.status != "Approved":
		return False
	if lesson.scheme_of_work != scheme.name or lesson.scheme_item_reference != item_reference:
		return False
	if lesson.school_branch != scheme.school_branch or lesson.program_offering != scheme.program_offering:
		return False
	if (lesson.student_group or "") != (scheme.student_group or ""):
		return False
	if lesson.course != scheme.course or lesson.instructor != instructor:
		return False
	return getdate(lesson.lesson_date) == getdate(delivered_on)


def _lesson_plan_options(scheme, item_reference: str, delivered_on, instructor: str) -> list[dict]:
	if not item_reference or not delivered_on or not instructor:
		return []
	rows = frappe.get_all(
		LESSON_DOCTYPE,
		filters={
			"scheme_of_work": scheme.name,
			"scheme_item_reference": item_reference,
			"school_branch": scheme.school_branch,
			"program_offering": scheme.program_offering,
			"course": scheme.course,
			"instructor": instructor,
			"lesson_date": getdate(delivered_on),
			"status": "Approved",
		},
		fields=["name", "lesson_plan_title", "student_group", "period_label", "lesson_date"],
		order_by="period_label asc, modified desc",
		limit_page_length=50,
	)
	return [
		{
			"value": row.name,
			"label": row.lesson_plan_title or row.name,
			"period_label": row.period_label or "",
			"lesson_date": row.lesson_date,
		}
		for row in rows
		if (row.student_group or "") == (scheme.student_group or "")
	]


def _validate_delivery_lesson_plan(lesson_plan: str | None, scheme, item_reference: str, delivered_on, instructor: str) -> str | None:
	name = str(lesson_plan or "").strip()
	if not name:
		return None
	lesson = frappe.get_doc(LESSON_DOCTYPE, name)
	if not _lesson_plan_matches_scheme(lesson, scheme, item_reference, delivered_on, instructor):
		frappe.throw(
			_("The selected Lesson Plan must be Approved and match this exact Scheme item, Branch, Class, Class Arm, Subject, Instructor and Delivery Date."),
			frappe.ValidationError,
		)
	return lesson.name


def _validated_evidence_file(evidence: str | None):
	"""Resolve an uploaded private File owned by the current user.

	The delivery API never accepts external URLs or another user's attachment as
	classroom evidence. Generic FileUploader uploads remain unattached until the
	append-only delivery log has been successfully created, then the File is bound to
	that exact log row.
	"""
	file_url = str(evidence or "").strip()
	if not file_url:
		return None
	if not file_url.startswith("/private/files/"):
		frappe.throw(_("Teaching Evidence must be uploaded as a private EduEdge file."), frappe.ValidationError)
	rows = frappe.get_all(
		"File",
		filters={"file_url": file_url},
		fields=[
			"name", "file_name", "file_url", "file_size", "is_private", "owner",
			"attached_to_doctype", "attached_to_name", "attached_to_field",
		],
		limit_page_length=2,
	)
	if len(rows) != 1:
		frappe.throw(_("Teaching Evidence upload could not be resolved safely."), frappe.ValidationError)
	row = rows[0]
	if not cint(row.is_private):
		frappe.throw(_("Teaching Evidence must remain private."), frappe.ValidationError)
	if row.owner != frappe.session.user:
		frappe.throw(_("You can attach only Teaching Evidence uploaded by your current user."), frappe.PermissionError)
	if row.attached_to_doctype or row.attached_to_name:
		frappe.throw(_("This Teaching Evidence file is already attached to another record."), frappe.ValidationError)
	if cint(row.file_size or 0) > MAX_EVIDENCE_BYTES:
		frappe.throw(_("Teaching Evidence must not exceed 10 MB."), frappe.ValidationError)
	extension = Path(str(row.file_name or "")).suffix.lower()
	if extension not in ALLOWED_EVIDENCE_EXTENSIONS:
		frappe.throw(
			_("Teaching Evidence supports images, PDF, Office documents and plain text only."),
			frappe.ValidationError,
		)
	return frappe.get_doc("File", row.name)


def _bind_evidence_file(file_doc, log_name: str) -> None:
	if not file_doc:
		return
	file_doc.attached_to_doctype = LOG_DOCTYPE
	file_doc.attached_to_name = log_name
	file_doc.attached_to_field = "evidence"
	file_doc.save(ignore_permissions=True)


def _latest_item_log(scheme_name: str, item_reference: str) -> dict | None:
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"scheme_of_work": scheme_name, "scheme_item_reference": item_reference},
		fields=["name", "delivery_status", "delivered_on", "logged_on"],
		order_by="logged_on desc, creation desc",
		limit_page_length=1,
	)
	return dict(rows[0]) if rows else None


def _validate_transition(scheme, item, status: str) -> dict | None:
	if status not in DELIVERY_STATUSES:
		frappe.throw(_("Select a valid Scheme delivery update."), frappe.ValidationError)
	latest = _latest_item_log(scheme.name, item.name)
	previous = (latest or {}).get("delivery_status") or ""
	if status not in STATUS_TRANSITIONS.get(previous, set()):
		if previous == "Completed":
			frappe.throw(
				_("This Scheme item is already Completed. Delivery history is append-only; use a governed correction process instead of rewriting completion."),
				frappe.ValidationError,
			)
		frappe.throw(
			_("Scheme delivery cannot change from {0} to {1}.").format(previous or _("Not Started"), status),
			frappe.ValidationError,
		)
	return latest


@contextmanager
def _delivery_action():
	previous = getattr(frappe.flags, DELIVERY_ACTION_FLAG, False)
	setattr(frappe.flags, DELIVERY_ACTION_FLAG, True)
	try:
		yield
	finally:
		setattr(frappe.flags, DELIVERY_ACTION_FLAG, previous)


def _item_state(scheme, item, logs: list[dict]) -> dict:
	item_logs = [row for row in logs if row.get("scheme_item_reference") == item.name]
	item_logs.sort(key=lambda row: (str(row.get("logged_on") or ""), str(row.get("creation") or "")))
	latest = item_logs[-1] if item_logs else None
	total_periods = sum(flt(row.get("periods_delivered")) for row in item_logs)
	estimated = max(cint(item.estimated_periods), 1)
	return {
		"scheme_item_reference": item.name,
		"sequence": cint(item.sequence),
		"week_no": cint(item.week_no),
		"topic": item.topic,
		"topic_name": item.topic_name_snapshot or item.topic,
		"learning_objective": item.learning_objective or "",
		"estimated_periods": estimated,
		"periods_delivered": total_periods,
		"progress_percent": min(round((total_periods / estimated) * 100, 1), 100.0),
		"latest_status": (latest or {}).get("delivery_status") or "Not Started",
		"latest_delivery_date": (latest or {}).get("delivered_on"),
		"log_count": len(item_logs),
		"available_updates": sorted(STATUS_TRANSITIONS.get((latest or {}).get("delivery_status") or "", set())),
	}


def _enrich_log_instructor_names(logs: list[dict]) -> list[dict]:
	names = {str(row.get("instructor") or "") for row in logs if row.get("instructor")}
	labels = {}
	if names:
		labels = {
			row.name: row.instructor_name or row.name
			for row in frappe.get_all(
				"Instructor",
				filters={"name": ["in", sorted(names)]},
				fields=["name", "instructor_name"],
				limit_page_length=len(names),
			)
		}
	for row in logs:
		row["instructor_name"] = labels.get(row.get("instructor")) or row.get("instructor") or ""
	return logs


@frappe.whitelist()
def get_scheme_delivery_state(name: str) -> dict:
	require_eduedge_access(feature_key="academics", action="view_scheme_delivery")
	scheme = frappe.get_doc(SCHEME_DOCTYPE, name)
	_context_authorized(scheme, write=False)
	logs = [
		dict(row)
		for row in frappe.get_all(
			LOG_DOCTYPE,
			filters={"scheme_of_work": scheme.name},
			fields=[
				"name", "scheme_item_reference", "scheme_item_sequence", "delivery_status", "delivered_on",
				"periods_delivered", "instructor", "instructor_assignment", "lesson_plan", "topic_name_snapshot",
				"logged_by", "logged_on", "notes", "evidence", "creation",
			],
			order_by="logged_on asc, creation asc",
			limit_page_length=0,
		)
	]
	logs = _enrich_log_instructor_names(logs)
	items = [_item_state(scheme, item, logs) for item in scheme.get("items") or []]
	total_estimated = sum(row["estimated_periods"] for row in items)
	total_delivered = sum(row["periods_delivered"] for row in items)
	completed = sum(1 for row in items if row["latest_status"] == "Completed")
	return {
		"scheme": scheme.name,
		"status": scheme.status,
		"items": items,
		"logs": list(reversed(logs)),
		"summary": {
			"item_count": len(items),
			"completed_items": completed,
			"pending_items": max(len(items) - completed, 0),
			"estimated_periods": total_estimated,
			"periods_delivered": total_delivered,
			"coverage_percent": round((completed / len(items)) * 100, 1) if items else 0,
		},
	}


@frappe.whitelist()
def get_delivery_instructor_options(name: str, delivered_on: str | None = None) -> list[dict]:
	require_eduedge_access(feature_key="academics", action="view_scheme_delivery")
	scheme = frappe.get_doc(SCHEME_DOCTYPE, name)
	_context_authorized(scheme, write=False)
	date = delivered_on or nowdate()
	if is_limited_instructor_user():
		rows = _eligible_assignment_rows(
			scheme,
			date,
			instructor=_exact_limited_instructor(),
		)
	else:
		rows = _eligible_assignment_rows(scheme, date)
	seen = set()
	result = []
	for row in rows:
		if row["instructor"] in seen:
			continue
		seen.add(row["instructor"])
		result.append(
			{
				"value": row["instructor"],
				"label": row.get("instructor_name") or frappe.db.get_value("Instructor", row["instructor"], "instructor_name") or row["instructor"],
				"assignment": row["name"],
				"assignment_title": row.get("assignment_title") or "",
			}
		)
	return result


@frappe.whitelist()
def get_delivery_lesson_plan_options(
	name: str,
	item_reference: str,
	delivered_on: str | None = None,
	instructor: str | None = None,
) -> list[dict]:
	require_eduedge_access(feature_key="academics", action="view_scheme_delivery")
	scheme = frappe.get_doc(SCHEME_DOCTYPE, name)
	_context_authorized(scheme, write=False)
	date = delivered_on or nowdate()
	assignment = _resolve_delivery_assignment(scheme, date, instructor=instructor)
	_scheme_item(scheme, str(item_reference or "").strip())
	return _lesson_plan_options(scheme, str(item_reference or "").strip(), date, assignment["instructor"])


@frappe.whitelist(methods=["POST"])
def log_scheme_delivery(
	name: str,
	item_reference: str,
	delivery_status: str,
	delivered_on: str | None = None,
	periods_delivered: float | int | str = 0,
	instructor: str | None = None,
	lesson_plan: str | None = None,
	notes: str | None = None,
	evidence: str | None = None,
) -> dict:
	require_eduedge_access(feature_key="academics", action="log_scheme_delivery")
	scheme = frappe.get_doc(SCHEME_DOCTYPE, name)
	if scheme.status != "Approved":
		frappe.throw(_("Scheme delivery can be logged only while the Scheme of Work is Approved."), frappe.ValidationError)
	_context_authorized(scheme, write=False)
	item = _scheme_item(scheme, str(item_reference or "").strip())
	date = getdate(delivered_on or nowdate())
	if scheme.period_start_date and date < getdate(scheme.period_start_date):
		frappe.throw(_("Delivery Date cannot precede the Scheme academic period."), frappe.ValidationError)
	if scheme.period_end_date and date > getdate(scheme.period_end_date):
		frappe.throw(_("Delivery Date cannot extend beyond the Scheme academic period."), frappe.ValidationError)
	assignment = _resolve_delivery_assignment(scheme, date, instructor=instructor)
	_validate_transition(scheme, item, delivery_status)
	lesson_plan_name = _validate_delivery_lesson_plan(
		lesson_plan,
		scheme,
		item.name,
		date,
		assignment["instructor"],
	)
	evidence_file = _validated_evidence_file(evidence)

	log = frappe.new_doc(LOG_DOCTYPE)
	log.scheme_of_work = scheme.name
	log.scheme_version = cint(scheme.version_no)
	log.scheme_item_reference = item.name
	log.scheme_item_sequence = cint(item.sequence)
	log.delivery_status = delivery_status
	log.delivered_on = date
	log.periods_delivered = flt(periods_delivered)
	log.institution = scheme.institution
	log.school_branch = scheme.school_branch
	log.program_offering = scheme.program_offering
	log.student_group = scheme.student_group or None
	log.course = scheme.course
	log.topic = item.topic
	log.instructor = assignment["instructor"]
	log.instructor_assignment = assignment["name"]
	log.lesson_plan = lesson_plan_name
	log.scheme_title_snapshot = scheme.scheme_title
	log.course_name_snapshot = scheme.course_name_snapshot or frappe.db.get_value("Course", scheme.course, "course_name") or scheme.course
	log.offering_title_snapshot = scheme.offering_title_snapshot or frappe.db.get_value("EduEdge Program Offering", scheme.program_offering, "offering_title") or scheme.program_offering
	log.student_group_name_snapshot = scheme.student_group_name_snapshot or ""
	log.topic_name_snapshot = item.topic_name_snapshot or frappe.db.get_value("Topic", item.topic, "topic_name") or item.topic
	log.learning_objective_snapshot = item.learning_objective or ""
	log.logged_by = frappe.session.user
	log.logged_on = now_datetime()
	log.notes = str(notes or "").strip()
	log.evidence = evidence_file.file_url if evidence_file else None
	with _delivery_action():
		log.insert(ignore_permissions=True)
	_bind_evidence_file(evidence_file, log.name)
	return {
		"log": log.name,
		"delivery_status": log.delivery_status,
		"instructor": log.instructor,
		"instructor_assignment": log.instructor_assignment,
		"lesson_plan": log.lesson_plan,
		"evidence": log.evidence,
		"state": get_scheme_delivery_state(scheme.name),
	}