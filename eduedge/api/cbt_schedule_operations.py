import frappe

from eduedge.api.cbt_schedule_operations_hardened import (
	assign_template_student_group as _assign_template_student_group,
	get_candidate,
	get_context,
	get_schedule,
	get_template_context,
	record_intervention,
	save_candidate,
	save_schedule,
	search_options,
	set_candidate_status,
	set_schedule_status,
)


@frappe.whitelist()
def assign_template_student_group(schedule: str) -> dict:
	"""Retry once when a concurrent request wins a candidate unique constraint.

	The hardened implementation recalculates existing assignments on each call,
	so the retry becomes an idempotent skip rather than a duplicate failure.
	"""
	try:
		return _assign_template_student_group(schedule)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		return _assign_template_student_group(schedule)


__all__ = (
	"assign_template_student_group",
	"get_candidate",
	"get_context",
	"get_schedule",
	"get_template_context",
	"record_intervention",
	"save_candidate",
	"save_schedule",
	"search_options",
	"set_candidate_status",
	"set_schedule_status",
)
