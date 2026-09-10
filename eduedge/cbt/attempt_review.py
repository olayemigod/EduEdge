from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

REVIEWER_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}
REVIEW_DECISIONS = {
	"Accept for Scoring",
	"Keep Flagged",
	"Disqualify Candidate",
}
ACCEPTABLE_STATUSES = {"Submitted", "Auto Submitted", "Timed Out"}


@contextmanager
def _review_service():
	previous = getattr(frappe.flags, "in_cbt_attempt_review_service", False)
	frappe.flags.in_cbt_attempt_review_service = True
	try:
		yield
	finally:
		frappe.flags.in_cbt_attempt_review_service = previous


def _require_reviewer() -> None:
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(REVIEWER_ROLES):
		frappe.throw(_("You are not authorised to resolve CBT Attempt reviews."), frappe.PermissionError)


def _lock(doctype: str, name: str) -> None:
	frappe.db.sql(f"select name from `tab{doctype}` where name=%s for update", name)


def _require_attempt(attempt_name: str):
	if not attempt_name:
		frappe.throw(_("CBT Attempt is required."), frappe.ValidationError)
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if not frappe.has_permission("EduEdge CBT Attempt", "read", doc=attempt):
		frappe.throw(_("You are not permitted to review this CBT Attempt."), frappe.PermissionError)
	if attempt.exam_scope != "School Examination":
		frappe.throw(
			_("Public examination reviews are resolved by the central signed-result service."),
			frappe.PermissionError,
		)
	return attempt


def _interventions(attempt) -> list[dict]:
	rows = frappe.get_all(
		"EduEdge CBT Intervention Log",
		filters={"candidate_assignment": attempt.candidate_assignment},
		fields=[
			"name",
			"intervention_type",
			"reason",
			"attempt_reference",
			"outcome",
			"acted_by",
			"acted_on",
		],
		order_by="acted_on asc",
	)
	return [
		row
		for row in rows
		if not row.attempt_reference or row.attempt_reference == attempt.name
	]


def _previous_reviews(attempt_name: str) -> list[dict]:
	return frappe.get_all(
		"EduEdge CBT Attempt Review",
		filters={"attempt": attempt_name},
		fields=["name", "decision", "decision_note", "decided_by", "decided_on"],
		order_by="decided_on desc",
	)


def _queue_row(attempt) -> dict:
	interventions = _interventions(attempt)
	previous_reviews = _previous_reviews(attempt.name)
	return {
		"attempt": attempt.name,
		"exam_schedule": attempt.exam_schedule,
		"school_branch": attempt.school_branch,
		"candidate_assignment": attempt.candidate_assignment,
		"student": attempt.student,
		"candidate_name": attempt.candidate_name,
		"attempt_number": cint(attempt.attempt_number),
		"attempt_status": attempt.attempt_status,
		"reported_pending_sync_count": cint(attempt.reported_pending_sync_count),
		"started_at": attempt.started_at,
		"expires_at": attempt.expires_at,
		"submitted_at": attempt.submitted_at,
		"submission_source": attempt.submission_source,
		"last_sync_at": attempt.last_sync_at,
		"review_reasons": attempt.review_reasons or "",
		"intervention_count": len(interventions),
		"interventions": interventions,
		"previous_review_count": len(previous_reviews),
		"previous_reviews": previous_reviews[:5],
		"result_exists": bool(frappe.db.exists("EduEdge CBT Result", {"attempt": attempt.name})),
		"can_accept": (
			attempt.attempt_status in ACCEPTABLE_STATUSES
			and not cint(attempt.reported_pending_sync_count)
			and not frappe.db.exists("EduEdge CBT Result", {"attempt": attempt.name})
		),
	}


@frappe.whitelist()
def get_attempt_review_queue(
	exam_schedule: str | None = None,
	school_branch: str | None = None,
	limit_start: int = 0,
	limit_page_length: int = 50,
) -> dict:
	_require_reviewer()
	filters = {"requires_review": 1, "attempt_status": ["!=", "Cancelled"]}
	if exam_schedule:
		filters["exam_schedule"] = exam_schedule
	if school_branch:
		filters["school_branch"] = school_branch
	attempt_names = frappe.get_list(
		"EduEdge CBT Attempt",
		filters=filters,
		pluck="name",
		order_by="modified asc",
		limit_page_length=1000,
	)
	rows = [_queue_row(_require_attempt(name)) for name in attempt_names]
	start = max(0, cint(limit_start))
	page_length = min(200, max(1, cint(limit_page_length)))
	return {
		"total": len(rows),
		"limit_start": start,
		"limit_page_length": page_length,
		"rows": rows[start : start + page_length],
	}


def _append_resolution_reason(reasons: str | None, decision: str, note: str) -> str:
	parts = [line.strip() for line in str(reasons or "").splitlines() if line.strip()]
	parts.append(f"Review decision — {decision}: {note}")
	return "\n".join(parts)


@frappe.whitelist()
def resolve_attempt_review(
	attempt_name: str,
	decision: str,
	decision_note: str,
) -> dict:
	_require_reviewer()
	decision = str(decision or "").strip()
	note = str(decision_note or "").strip()
	if decision not in REVIEW_DECISIONS:
		frappe.throw(_("Select a valid CBT Attempt review decision."), frappe.ValidationError)
	if not note:
		frappe.throw(_("Decision Note is required for every CBT Attempt review."), frappe.ValidationError)

	_lock("EduEdge CBT Attempt", attempt_name)
	attempt = _require_attempt(attempt_name)
	if not cint(attempt.requires_review):
		frappe.throw(_("This CBT Attempt no longer requires review."), frappe.ValidationError)

	status_before = attempt.attempt_status
	status_after = status_before
	requires_review_after = 1
	result_exists = bool(frappe.db.exists("EduEdge CBT Result", {"attempt": attempt.name}))

	if decision == "Accept for Scoring":
		if result_exists:
			frappe.throw(
				_("A CBT Result already exists. Resolve it through a controlled result-repair workflow."),
				frappe.ValidationError,
			)
		if cint(attempt.reported_pending_sync_count):
			frappe.throw(
				_("Pending browser answers must be resolved before accepting the attempt for scoring."),
				frappe.ValidationError,
			)
		if attempt.attempt_status not in ACCEPTABLE_STATUSES:
			frappe.throw(
				_("Only Submitted, Auto Submitted, or Timed Out attempts can be accepted for scoring."),
				frappe.ValidationError,
			)
		status_after = "Auto Submitted" if attempt.attempt_status == "Timed Out" else attempt.attempt_status
		requires_review_after = 0
	elif decision == "Disqualify Candidate":
		if result_exists:
			frappe.throw(
				_("A CBT Result already exists. Disqualification requires a controlled result-cancellation workflow."),
				frappe.ValidationError,
			)
		status_after = "Cancelled"
		requires_review_after = 0

	updates = {
		"attempt_status": status_after,
		"requires_review": requires_review_after,
		"review_reasons": _append_resolution_reason(attempt.review_reasons, decision, note),
	}
	frappe.db.set_value(
		"EduEdge CBT Attempt",
		attempt.name,
		updates,
		update_modified=False,
	)
	if decision == "Disqualify Candidate" and attempt.candidate_assignment:
		frappe.db.set_value(
			"EduEdge CBT Candidate Assignment",
			attempt.candidate_assignment,
			"assignment_status",
			"Disqualified",
			update_modified=False,
		)

	intervention_count = len(_interventions(attempt))
	with _review_service():
		review = frappe.get_doc(
			{
				"doctype": "EduEdge CBT Attempt Review",
				"attempt": attempt.name,
				"exam_schedule": attempt.exam_schedule,
				"school_branch": attempt.school_branch,
				"candidate_assignment": attempt.candidate_assignment,
				"student": attempt.student,
				"candidate_name": attempt.candidate_name,
				"attempt_status_before": status_before,
				"reported_pending_sync_count": attempt.reported_pending_sync_count,
				"review_reasons_snapshot": attempt.review_reasons,
				"intervention_count": intervention_count,
				"decision": decision,
				"decision_note": note,
				"attempt_status_after": status_after,
				"requires_review_after": requires_review_after,
				"decided_by": frappe.session.user,
				"decided_on": now_datetime(),
			}
		).insert(ignore_permissions=True)
	return {
		"review": review.name,
		"attempt": attempt.name,
		"decision": decision,
		"attempt_status_before": status_before,
		"attempt_status_after": status_after,
		"requires_review_after": requires_review_after,
	}
