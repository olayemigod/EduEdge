from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import frappe
from frappe import _

from eduedge.api.cbt_schedule_operations_hardened import (
	assign_template_student_group as _assign_template_student_group,
	get_candidate,
	get_context as _get_context,
	get_schedule,
	get_template_context,
	record_intervention as _record_intervention,
	save_candidate as _save_candidate,
	save_schedule as _save_schedule,
	search_options as _search_options,
	set_candidate_status as _set_candidate_status,
	set_schedule_status as _set_schedule_status,
)
from eduedge.cbt.public_access import get_public_exam_capability_summary
from eduedge.cbt.schedule_governance import (
	controlled_cbt_operation,
	schedule_operation_lock,
	withdraw_non_started_candidates_for_cancellation,
)
from eduedge.education.offerings import assert_branch_access

SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
SCHOOL_EXAM = "School Examination"
MAX_OPTIONS = 50


def _parse_values(value: str | dict | None) -> dict[str, Any]:
	if not value:
		return {}
	if isinstance(value, dict):
		return dict(value)
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Expected a JSON object."), frappe.ValidationError)
	return parsed


def _candidate_schedule(name: str | None = None, values: str | dict | None = None) -> str:
	if name:
		schedule = frappe.db.get_value(ASSIGNMENT_DOCTYPE, name, "exam_schedule")
		if not schedule:
			frappe.throw(_("The selected Candidate Assignment does not exist."), frappe.DoesNotExistError)
		return schedule
	payload = _parse_values(values)
	schedule = str(payload.get("exam_schedule") or "").strip()
	if not schedule:
		frappe.throw(_("Examination Schedule is required."), frappe.ValidationError)
	return schedule


def _lock_schedule_row(schedule: str) -> None:
	frappe.get_doc(SCHEDULE_DOCTYPE, schedule, for_update=True)


def _institution_owned_options(
	*,
	doctype: str,
	title_field: str,
	payload: dict[str, Any],
	query: str,
) -> list[dict]:
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You do not have read permission for {0}.").format(doctype), frappe.PermissionError)
	if (payload.get("exam_scope") or SCHOOL_EXAM) != SCHOOL_EXAM:
		return []
	branch_name = str(payload.get("school_branch") or payload.get("page_branch") or "").strip()
	if not branch_name:
		return []
	assert_branch_access(branch_name)
	branch = frappe.db.get_value(
		"EduEdge School Branch",
		branch_name,
		["institution", "company", "enabled"],
		as_dict=True,
	)
	if not branch or not branch.enabled:
		return []
	meta = frappe.get_meta(doctype)
	filters: dict[str, Any] = {}
	if meta.has_field("eduedge_institution"):
		filters["eduedge_institution"] = branch.institution
	elif meta.has_field("institution"):
		filters["institution"] = branch.institution
	elif meta.has_field("company"):
		filters["company"] = branch.company
	else:
		# Fail closed when the master has no ownership field.
		return []
	pattern = f"%{str(query or '').strip()}%"
	or_filters = [["name", "like", pattern]]
	fields = ["name"]
	if meta.has_field(title_field):
		fields.append(title_field)
		or_filters.append([title_field, "like", pattern])
	rows = frappe.get_list(
		doctype,
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by=f"{title_field} asc" if meta.has_field(title_field) else "name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{"value": row.name, "label": row.get(title_field) or row.name}
		for row in rows
	]


@frappe.whitelist()
def get_context(
	exam_scope: str | None = None,
	branch: str | None = None,
	status: str | None = None,
	search: str | None = None,
	schedule: str | None = None,
) -> dict:
	state = _get_context(
		exam_scope=exam_scope,
		branch=branch,
		status=status,
		search=search,
		schedule=schedule,
	)
	public_access = get_public_exam_capability_summary(frappe.session.user)
	state.setdefault(
		"can_manage_public",
		bool(public_access.get("capabilities", {}).get("author", {}).get("allowed")),
	)
	state.setdefault(
		"user",
		{
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
	)
	return state


@frappe.whitelist()
def save_schedule(values: str | dict, name: str | None = None) -> dict:
	payload = _parse_values(values)
	lock_identity = name or payload.get("schedule_code") or "new-schedule"
	with schedule_operation_lock(str(lock_identity)):
		if name:
			_lock_schedule_row(name)
		with controlled_cbt_operation("eduedge_access_guarded"):
			return _save_schedule(values=payload, name=name)


@frappe.whitelist()
def set_schedule_status(name: str, status: str, reason: str | None = None) -> dict:
	# One site-wide activation lock prevents concurrent phantom collision checks
	# for different Schedules sharing a Centre, Invigilator or candidate.
	activation_lock = schedule_operation_lock("activation-governance") if status == "Active" else nullcontext()
	with activation_lock:
		with schedule_operation_lock(name):
			locked = frappe.get_doc(SCHEDULE_DOCTYPE, name, for_update=True)
			locked.check_permission("write")
			with controlled_cbt_operation("eduedge_controlled_status_action"):
				if status == "Cancelled":
					withdraw_non_started_candidates_for_cancellation(name, str(reason or "").strip())
				with controlled_cbt_operation("eduedge_access_guarded"):
					return _set_schedule_status(name=name, status=status, reason=reason)


@frappe.whitelist()
def save_candidate(values: str | dict, name: str | None = None) -> dict:
	payload = _parse_values(values)
	# Extra time is exclusively an audited Time Extension intervention.
	payload.pop("approved_extra_time_minutes", None)
	schedule = _candidate_schedule(name=name, values=payload)
	with schedule_operation_lock(schedule):
		_lock_schedule_row(schedule)
		with controlled_cbt_operation(
			"eduedge_access_guarded",
			"eduedge_controlled_status_action",
		):
			return _save_candidate(values=payload, name=name)


@frappe.whitelist()
def set_candidate_status(name: str, status: str, reason: str | None = None) -> dict:
	schedule = _candidate_schedule(name=name)
	with schedule_operation_lock(schedule):
		_lock_schedule_row(schedule)
		with controlled_cbt_operation(
			"eduedge_access_guarded",
			"eduedge_controlled_status_action",
		):
			return _set_candidate_status(name=name, status=status, reason=reason)


@frappe.whitelist()
def assign_template_student_group(schedule: str) -> dict:
	"""Assign one Schedule Class idempotently under a Schedule mutation lock."""
	with schedule_operation_lock(schedule):
		_lock_schedule_row(schedule)
		with controlled_cbt_operation(
			"eduedge_access_guarded",
			"eduedge_controlled_status_action",
		):
			try:
				return _assign_template_student_group(schedule)
			except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
				return _assign_template_student_group(schedule)


@frappe.whitelist()
def record_intervention(values: str | dict) -> dict:
	payload = _parse_values(values)
	assignment = str(payload.get("candidate_assignment") or "").strip()
	if not assignment:
		frappe.throw(_("Candidate Assignment is required."), frappe.ValidationError)
	schedule = _candidate_schedule(name=assignment)
	with schedule_operation_lock(schedule):
		_lock_schedule_row(schedule)
		with controlled_cbt_operation(
			"eduedge_access_guarded",
			"eduedge_controlled_intervention",
		):
			return _record_intervention(values=payload)


@frappe.whitelist()
def search_options(fieldname: str, txt: str | None = None, values: str | dict | None = None) -> list[dict]:
	payload = _parse_values(values)
	if fieldname == "primary_invigilator":
		if not any(
			frappe.has_permission(SCHEDULE_DOCTYPE, permission_type)
			for permission_type in ("create", "write")
		):
			frappe.throw(_("Schedule management permission is required to search Invigilators."), frappe.PermissionError)
		if (payload.get("exam_scope") or SCHOOL_EXAM) == SCHOOL_EXAM and not (
			payload.get("school_branch") or payload.get("page_branch")
		):
			frappe.throw(_("Select a School Branch / Campus before searching Invigilators."), frappe.ValidationError)
	if fieldname == "program":
		return _institution_owned_options(
			doctype="Program",
			title_field="program_name",
			payload=payload,
			query=str(txt or ""),
		)
	if fieldname == "assessment_group":
		return _institution_owned_options(
			doctype="Assessment Group",
			title_field="assessment_group_name",
			payload=payload,
			query=str(txt or ""),
		)
	return _search_options(fieldname=fieldname, txt=txt, values=payload)


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
