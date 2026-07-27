from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

ACTIVE_ASSIGNMENT_STATUSES = {"Eligible", "Checked In", "Released", "Completed"}
OPERATIONAL_BLOCKING_ATTEMPT_STATUSES = {
	"Prepared",
	"In Progress",
	"Pending Sync",
	"Timed Out",
}
RESULT_PROCESSING_STATUSES = {"Submitted", "Auto Submitted", "Under Review", "Scored"}
RESULT_APPROVAL_STATUSES = {"Scored"}


def _require_schedule_access(exam_schedule: str):
	if not exam_schedule:
		frappe.throw(_("Examination Schedule is required."), frappe.ValidationError)
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read", doc=schedule):
		frappe.throw(_("You are not permitted to review this Examination Schedule."), frappe.PermissionError)
	return schedule


def _blocker(code: str, label: str, count: int, action: str) -> dict:
	return {
		"code": code,
		"label": label,
		"count": cint(count),
		"action": action,
	}


def get_result_readiness(exam_schedule: str, *, check_permission: bool = True) -> dict:
	"""Return operational and approval readiness without mutating attempt data.

	The result workflow must call :func:`assert_result_approval_ready` before any
	future approval or publication action. This keeps pending browser answers,
	unresolved integrity reviews, and incomplete candidate attempts from being
	silently approved.
	"""
	if check_permission:
		schedule = _require_schedule_access(exam_schedule)
	else:
		schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)

	assignments = frappe.get_all(
		"EduEdge CBT Candidate Assignment",
		filters={
			"exam_schedule": exam_schedule,
			"assignment_status": ["in", sorted(ACTIVE_ASSIGNMENT_STATUSES)],
		},
		fields=["name", "assignment_status", "candidate_name"],
		order_by="candidate_name asc",
	)
	attempts = frappe.get_all(
		"EduEdge CBT Attempt",
		filters={"exam_schedule": exam_schedule, "attempt_status": ["!=", "Cancelled"]},
		fields=[
			"name",
			"candidate_assignment",
			"candidate_name",
			"attempt_number",
			"attempt_status",
			"reported_pending_sync_count",
			"requires_review",
			"review_reasons",
		],
		order_by="candidate_assignment asc, attempt_number desc",
	)

	latest_by_assignment = {}
	for attempt in attempts:
		latest_by_assignment.setdefault(attempt.candidate_assignment, attempt)

	missing_attempts = [
		assignment
		for assignment in assignments
		if assignment.assignment_status != "Completed" and assignment.name not in latest_by_assignment
	]
	latest_attempts = list(latest_by_assignment.values())
	status_counts = Counter(row.attempt_status for row in latest_attempts)
	pending_sync_attempts = [
		row
		for row in latest_attempts
		if cint(row.reported_pending_sync_count) > 0 or row.attempt_status == "Pending Sync"
	]
	review_attempts = [row for row in latest_attempts if cint(row.requires_review)]
	operationally_open = [
		row
		for row in latest_attempts
		if row.attempt_status in OPERATIONAL_BLOCKING_ATTEMPT_STATUSES
	]
	processing_not_ready = [
		row
		for row in latest_attempts
		if row.attempt_status not in RESULT_PROCESSING_STATUSES
	]
	approval_not_ready = [
		row
		for row in latest_attempts
		if row.attempt_status not in RESULT_APPROVAL_STATUSES
	]

	operational_blockers = []
	if not assignments:
		operational_blockers.append(
			_blocker(
				"NO_CANDIDATES",
				"No active candidate assignments",
				0,
				"Assign eligible candidates before starting result processing.",
			)
		)
	elif not latest_attempts:
		operational_blockers.append(
			_blocker(
				"NO_ATTEMPTS",
				"No candidate attempts have been prepared",
				0,
				"Prepare attempts or formally withdraw candidates who will not sit the examination.",
			)
		)
	if missing_attempts:
		operational_blockers.append(
			_blocker(
				"MISSING_ATTEMPTS",
				"Released or eligible candidates without an attempt",
				len(missing_attempts),
				"Prepare or formally withdraw the affected candidate assignments.",
			)
		)
	if operationally_open:
		operational_blockers.append(
			_blocker(
				"OPEN_ATTEMPTS",
				"Attempts still active, pending synchronisation, or timed out",
				len(operationally_open),
				"Complete the attempts and resolve pending browser answers.",
			)
		)
	if pending_sync_attempts:
		operational_blockers.append(
			_blocker(
				"PENDING_SYNC",
				"Attempts with unresolved browser answers",
				len(pending_sync_attempts),
				"Reconnect the candidate browser or complete an audited manual sync resolution.",
			)
		)
	if review_attempts:
		operational_blockers.append(
			_blocker(
				"REVIEW_REQUIRED",
				"Attempts requiring integrity review",
				len(review_attempts),
				"Complete the governed attempt-review workflow before approval.",
			)
		)
	if processing_not_ready:
		operational_blockers.append(
			_blocker(
				"NOT_READY_FOR_PROCESSING",
				"Attempts not ready for result processing",
				len(processing_not_ready),
				"Resolve incomplete, timed-out, or cancelled attempt outcomes.",
			)
		)

	approval_blockers = list(operational_blockers)
	if approval_not_ready:
		approval_blockers.append(
			_blocker(
				"NOT_SCORED",
				"Attempts not yet scored",
				len(approval_not_ready),
				"Complete objective scoring and any required manual marking.",
			)
		)

	return {
		"exam_schedule": schedule.name,
		"schedule_title": schedule.schedule_title,
		"schedule_status": schedule.status,
		"school_branch": schedule.school_branch,
		"candidate_assignment_count": len(assignments),
		"latest_attempt_count": len(latest_attempts),
		"status_counts": dict(sorted(status_counts.items())),
		"pending_sync_count": len(pending_sync_attempts),
		"review_required_count": len(review_attempts),
		"missing_attempt_count": len(missing_attempts),
		"ready_for_result_processing": not operational_blockers and bool(latest_attempts),
		"ready_for_result_approval": not approval_blockers and bool(latest_attempts),
		"operational_blockers": operational_blockers,
		"approval_blockers": approval_blockers,
	}


@frappe.whitelist()
def get_schedule_result_readiness(exam_schedule: str) -> dict:
	return get_result_readiness(exam_schedule)


def assert_result_processing_ready(exam_schedule: str) -> dict:
	readiness = get_result_readiness(exam_schedule)
	if readiness["operational_blockers"]:
		labels = ", ".join(
			f"{row['label']} ({row['count']})"
			for row in readiness["operational_blockers"]
		)
		frappe.throw(
			_("CBT result processing is blocked: {0}.").format(labels),
			frappe.ValidationError,
			title=_("Resolve CBT Attempt Issues"),
		)
	return readiness


def assert_result_approval_ready(exam_schedule: str) -> dict:
	readiness = get_result_readiness(exam_schedule)
	if readiness["approval_blockers"]:
		labels = ", ".join(
			f"{row['label']} ({row['count']})"
			for row in readiness["approval_blockers"]
		)
		frappe.throw(
			_("CBT result approval is blocked: {0}.").format(labels),
			frappe.ValidationError,
			title=_("CBT Results Not Ready for Approval"),
		)
	return readiness
