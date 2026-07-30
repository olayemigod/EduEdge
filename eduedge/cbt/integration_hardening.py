from __future__ import annotations

import frappe
from frappe import _

from eduedge.cbt import attempt_review, invigilation
from eduedge.services.branch_context import get_allowed_school_branches


def _allowed_branch_names() -> set[str]:
	return {
		row.get("name")
		for row in get_allowed_school_branches(user=frappe.session.user)
		if row.get("name")
	}


def _assert_permitted_branch(branch: str | None) -> None:
	if not branch:
		frappe.throw(_("A School Branch / Campus is required."), frappe.ValidationError)
	if branch not in _allowed_branch_names():
		frappe.throw(
			_("You are not permitted to use the selected School Branch / Campus."),
			frappe.PermissionError,
		)


def _review_schedule(exam_schedule: str):
	schedule = frappe.get_doc("EduEdge CBT Exam Schedule", exam_schedule)
	if not frappe.has_permission("EduEdge CBT Exam Schedule", "read", doc=schedule):
		frappe.throw(
			_("You are not permitted to review this Examination Schedule."),
			frappe.PermissionError,
		)
	if schedule.exam_scope != "School Examination":
		frappe.throw(
			_("Public examination reviews are resolved by the central signed-result service."),
			frappe.PermissionError,
		)
	_assert_permitted_branch(schedule.school_branch)
	return schedule


@frappe.whitelist()
def get_invigilation_schedules(school_branch: str | None = None) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Login is required."), frappe.PermissionError)
	if school_branch:
		_assert_permitted_branch(school_branch)
	return invigilation.get_invigilation_schedules(school_branch=school_branch)


@frappe.whitelist()
def get_attempt_review_queue(
	exam_schedule: str | None = None,
	school_branch: str | None = None,
	limit_start: int = 0,
	limit_page_length: int = 50,
) -> dict:
	if school_branch:
		_assert_permitted_branch(school_branch)
	if exam_schedule:
		schedule = _review_schedule(exam_schedule)
		if school_branch and schedule.school_branch != school_branch:
			frappe.throw(
				_("The selected Examination Schedule belongs to another Branch / Campus."),
				frappe.PermissionError,
			)
	return attempt_review.get_attempt_review_queue(
		exam_schedule=exam_schedule,
		school_branch=school_branch,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
	)


@frappe.whitelist()
def resolve_attempt_review(
	attempt_name: str,
	decision: str,
	decision_note: str,
) -> dict:
	attempt = frappe.get_doc("EduEdge CBT Attempt", attempt_name)
	if attempt.exam_scope == "School Examination":
		_assert_permitted_branch(attempt.school_branch)
	return attempt_review.resolve_attempt_review(
		attempt_name=attempt_name,
		decision=decision,
		decision_note=decision_note,
	)
