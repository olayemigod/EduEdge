from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from eduedge.cbt.result_readiness import get_result_readiness
from eduedge.services.branch_context import get_allowed_school_branches

STALE_HEARTBEAT_SECONDS = 90
MONITORED_SCHEDULE_STATUSES = {"Ready", "Active", "Suspended", "Completed"}
TERMINAL_ATTEMPT_STATUSES = {"Submitted", "Auto Submitted", "Under Review", "Scored", "Cancelled"}


def _seconds_since(value) -> int | None:
	if not value:
		return None
	return max(0, int((now_datetime() - get_datetime(value)).total_seconds()))


def _remaining_seconds(attempt) -> int:
	if not attempt or not attempt.expires_at or attempt.attempt_status != "In Progress":
		return 0
	return max(0, int((get_datetime(attempt.expires_at) - now_datetime()).total_seconds()))


def _connection_state(attempt) -> dict:
	if not attempt:
		return {"code": "NO_ATTEMPT", "label": "No Attempt", "tone": "neutral"}
	if attempt.attempt_status == "Prepared":
		return {"code": "NOT_STARTED", "label": "Not Started", "tone": "neutral"}
	if attempt.attempt_status == "Pending Sync" or cint(attempt.reported_pending_sync_count):
		return {"code": "PENDING_SYNC", "label": "Pending Sync", "tone": "warning"}
	if attempt.attempt_status in TERMINAL_ATTEMPT_STATUSES:
		return {"code": "CLOSED", "label": attempt.attempt_status, "tone": "success"}
	if attempt.attempt_status == "Timed Out":
		return {"code": "TIMED_OUT", "label": "Timed Out", "tone": "danger"}
	if attempt.attempt_status != "In Progress":
		return {"code": "OTHER", "label": attempt.attempt_status, "tone": "neutral"}

	heartbeat_age = _seconds_since(attempt.last_heartbeat_at)
	if heartbeat_age is None:
		return {"code": "NO_HEARTBEAT", "label": "No Heartbeat", "tone": "danger"}
	if heartbeat_age > STALE_HEARTBEAT_SECONDS:
		return {"code": "STALE", "label": "Connection Stale", "tone": "warning"}
	return {"code": "ONLINE", "label": "Online", "tone": "success"}


def _require_schedule_read(exam_schedule: str):
	if not exam_schedule:
		frappe.throw(_("Examination Schedule is required."), frappe.ValidationError)
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read", doc=schedule):
		frappe.throw(_("You are not permitted to monitor this Examination Schedule."), frappe.PermissionError)
	return schedule


def _schedule_rows(school_branch: str | None = None) -> list[dict]:
	filters = {"status": ["in", sorted(MONITORED_SCHEDULE_STATUSES)]}
	if school_branch:
		filters["school_branch"] = school_branch
	return frappe.get_list(
		"EduEdge CBT Exam Schedule",
		filters=filters,
		fields=[
			"name",
			"schedule_title",
			"schedule_code",
			"exam_scope",
			"school_branch",
			"course",
			"examination_centre",
			"scheduled_start",
			"scheduled_end",
			"status",
		],
		order_by="scheduled_start desc",
		limit_page_length=100,
	)


@frappe.whitelist()
def get_invigilation_schedules(school_branch: str | None = None) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Login is required."), frappe.PermissionError)
	branches = get_allowed_school_branches(user=frappe.session.user)
	allowed_names = {row.get("name") for row in branches}
	if school_branch and allowed_names and school_branch not in allowed_names:
		frappe.throw(_("You are not permitted to monitor the selected Branch / Campus."), frappe.PermissionError)
	return {
		"server_time": now_datetime(),
		"stale_heartbeat_seconds": STALE_HEARTBEAT_SECONDS,
		"allowed_branches": branches,
		"schedules": _schedule_rows(school_branch),
	}


@frappe.whitelist()
def get_invigilation_context(exam_schedule: str) -> dict:
	"""Return permission-safe live candidate status without answer content."""
	schedule = _require_schedule_read(exam_schedule)
	assignments = frappe.get_all(
		"EduEdge CBT Candidate Assignment",
		filters={"exam_schedule": schedule.name},
		fields=[
			"name",
			"candidate_name",
			"student",
			"public_candidate_reference",
			"assignment_status",
			"checked_in_on",
			"approved_extra_time_minutes",
		],
		order_by="candidate_name asc",
	)
	attempts = frappe.get_all(
		"EduEdge CBT Attempt",
		filters={"exam_schedule": schedule.name, "attempt_status": ["!=", "Cancelled"]},
		fields=[
			"name",
			"candidate_assignment",
			"attempt_number",
			"attempt_status",
			"started_at",
			"expires_at",
			"submitted_at",
			"last_heartbeat_at",
			"last_sync_at",
			"reported_pending_sync_count",
			"answered_count",
			"question_count",
			"requires_review",
			"review_reasons",
		],
		order_by="candidate_assignment asc, attempt_number desc",
	)
	latest_by_assignment = {}
	for attempt in attempts:
		latest_by_assignment.setdefault(attempt.candidate_assignment, attempt)

	candidate_rows = []
	for assignment in assignments:
		attempt = latest_by_assignment.get(assignment.name)
		connection = _connection_state(attempt)
		candidate_rows.append(
			{
				"candidate_assignment": assignment.name,
				"candidate_name": assignment.candidate_name,
				"student": assignment.student,
				"public_candidate_reference": assignment.public_candidate_reference,
				"assignment_status": assignment.assignment_status,
				"checked_in_on": assignment.checked_in_on,
				"approved_extra_time_minutes": cint(assignment.approved_extra_time_minutes),
				"attempt": attempt.name if attempt else None,
				"attempt_number": cint(attempt.attempt_number) if attempt else 0,
				"attempt_status": attempt.attempt_status if attempt else "No Attempt",
				"answered_count": cint(attempt.answered_count) if attempt else 0,
				"question_count": cint(attempt.question_count) if attempt else 0,
				"reported_pending_sync_count": cint(attempt.reported_pending_sync_count) if attempt else 0,
				"last_heartbeat_at": attempt.last_heartbeat_at if attempt else None,
				"heartbeat_age_seconds": _seconds_since(attempt.last_heartbeat_at) if attempt else None,
				"last_sync_at": attempt.last_sync_at if attempt else None,
				"seconds_remaining": _remaining_seconds(attempt),
				"requires_review": cint(attempt.requires_review) if attempt else 0,
				"review_reasons": attempt.review_reasons if attempt else "",
				"connection": connection,
			}
		)

	attempt_status_counts = Counter(row["attempt_status"] for row in candidate_rows)
	connection_counts = Counter(row["connection"]["code"] for row in candidate_rows)
	readiness = get_result_readiness(schedule.name, check_permission=False)
	return {
		"server_time": now_datetime(),
		"stale_heartbeat_seconds": STALE_HEARTBEAT_SECONDS,
		"schedule": {
			"name": schedule.name,
			"schedule_title": schedule.schedule_title,
			"schedule_code": schedule.schedule_code,
			"exam_scope": schedule.exam_scope,
			"school_branch": schedule.school_branch,
			"course": schedule.course,
			"examination_centre": schedule.examination_centre,
			"scheduled_start": schedule.scheduled_start,
			"scheduled_end": schedule.scheduled_end,
			"status": schedule.status,
		},
		"summary": {
			"candidate_count": len(candidate_rows),
			"in_progress_count": attempt_status_counts.get("In Progress", 0),
			"pending_sync_count": sum(
				1 for row in candidate_rows if row["reported_pending_sync_count"] or row["attempt_status"] == "Pending Sync"
			),
			"stale_connection_count": connection_counts.get("STALE", 0) + connection_counts.get("NO_HEARTBEAT", 0),
			"submitted_count": attempt_status_counts.get("Submitted", 0) + attempt_status_counts.get("Auto Submitted", 0),
			"review_required_count": sum(1 for row in candidate_rows if row["requires_review"]),
		},
		"result_readiness": readiness,
		"candidates": candidate_rows,
	}
