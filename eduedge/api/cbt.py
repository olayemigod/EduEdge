from __future__ import annotations

import frappe

from eduedge.cbt import service
from eduedge.platform.access import guard_eduedge_action


@frappe.whitelist()
def get_exam_access(exam: str, student: str | None = None) -> dict:
	return service.get_exam_access(exam, student=student)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="schedule_exam")
def schedule_exam(exam: str) -> dict:
	return service.schedule_exam(exam)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="activate_exam")
def activate_exam(exam: str) -> dict:
	return service.activate_exam(exam)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="close_exam")
def close_exam(exam: str) -> dict:
	return service.close_exam(exam)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="start_attempt")
def start_attempt(
	exam: str,
	student: str | None = None,
	device_id: str | None = None,
	session_id: str | None = None,
) -> dict:
	return service.start_attempt(
		exam,
		student=student,
		device_id=device_id,
		session_id=session_id,
	)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="resume_attempt")
def resume_attempt(attempt: str) -> dict:
	return service.resume_attempt(attempt)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="sync_answers")
def sync_answers(
	attempt: str,
	client_batch_id: str,
	answers,
	client_pending_count: int = 0,
	network_state: str = "Unknown",
) -> dict:
	return service.sync_answers(
		attempt,
		client_batch_id,
		answers,
		client_pending_count=client_pending_count,
		network_state=network_state,
	)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="submit_attempt")
def submit_attempt(
	attempt: str,
	client_batch_id: str | None = None,
	answers=None,
	client_pending_count: int = 0,
	network_state: str = "Online",
) -> dict:
	return service.submit_attempt(
		attempt,
		client_batch_id=client_batch_id,
		answers=answers,
		client_pending_count=client_pending_count,
		network_state=network_state,
	)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="record_integrity_event")
def record_integrity_event(attempt: str, event_type: str, count: int = 1) -> dict:
	return service.record_integrity_event(attempt, event_type, count=count)


@frappe.whitelist()
def get_invigilator_monitor(exam: str) -> dict:
	return service.get_invigilator_monitor(exam)


@frappe.whitelist()
@guard_eduedge_action("cbt", action="approve_attempt_result")
def approve_attempt_result(attempt: str) -> dict:
	return service.approve_attempt_result(attempt)
