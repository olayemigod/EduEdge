from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.cbt.public_access import (
	get_public_exam_capability_summary,
	require_public_exam_assignment,
	require_public_exam_authoring,
)
from eduedge.cbt.schedule_governance import assert_user_branch_access
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access
from eduedge.eduedge.doctype.eduedge_cbt_exam_template.eduedge_cbt_exam_template import MODE_FIXED
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
INTERVENTION_DOCTYPE = "EduEdge CBT Intervention Log"
LIFECYCLE_DOCTYPE = "EduEdge CBT Lifecycle Log"
TEMPLATE_DOCTYPE = "EduEdge CBT Exam Template"
CENTRE_DOCTYPE = "EduEdge Examination Centre"
SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
SCHOOL_CENTRE = "School Examination Centre"
PUBLIC_CENTRE = "EduEdge Exam Centre"
MAX_OPTIONS = 50
MAX_LIST_ROWS = 200

SCHEDULE_EDITABLE_FIELDS = (
	"schedule_title",
	"schedule_code",
	"exam_template",
	"school_branch",
	"course",
	"student_group",
	"academic_year",
	"academic_term",
	"program",
	"assessment_group",
	"examination_centre",
	"scheduled_start",
	"check_in_opens_at",
	"require_candidate_check_in",
	"candidate_start_mode",
	"allow_late_entry",
	"late_entry_grace_minutes",
	"primary_invigilator",
	"allow_invigilator_time_extension",
	"maximum_time_extension_minutes",
	"allow_invigilator_force_submit",
	"notes",
)

SCHEDULE_SNAPSHOT_FIELDS = (
	"duration_minutes",
	"maximum_attempts",
	"pass_percentage",
	"navigation_policy",
	"auto_submit_on_timeout",
	"allow_resume",
	"randomise_questions",
	"randomise_options",
	"marking_policy",
	"result_release_policy",
	"device_change_policy",
	"attempt_review_policy",
)

ASSIGNMENT_EDITABLE_FIELDS = (
	"exam_schedule",
	"student",
	"public_candidate_reference",
	"candidate_name",
	"approved_extra_time_minutes",
	"notes",
)

INVIGILATOR_ROLES = {
	"CBT Invigilator",
	"Teacher",
	"Instructor",
	"Education Manager",
	"Academic Administrator",
	"School Administrator",
	"EduEdge Administrator",
	"EduEdge Super Administrator",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(doctype: str, permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission(doctype, permission_type):
		frappe.throw(
			_("You do not have {0} permission for {1}.").format(permission_type, doctype),
			frappe.PermissionError,
		)


def _parse_json(value: Any) -> dict:
	if not value:
		return {}
	if isinstance(value, dict):
		return value
	parsed = frappe.parse_json(value)
	if not isinstance(parsed, dict):
		frappe.throw(_("Expected a JSON object."), frappe.ValidationError)
	return parsed


def _permissions(doctype: str) -> dict[str, bool]:
	return {
		permission_type: bool(frappe.has_permission(doctype, permission_type))
		for permission_type in ("read", "create", "write", "delete")
	}


def _branch_options() -> list[dict]:
	return [
		{
			"value": row.get("name"),
			"label": row.get("branch_name") or row.get("name"),
			"description": row.get("institution") or row.get("company") or "",
			"institution": row.get("institution") or "",
			"company": row.get("company") or "",
		}
		for row in get_allowed_school_branches()
		if row.get("name")
	]


def _select_branch(branch: str | None, options: list[dict]) -> str:
	allowed = {row["value"] for row in options}
	if branch:
		if branch not in allowed:
			frappe.throw(_("Select a permitted School Branch / Campus."), frappe.PermissionError)
		assert_branch_access(branch)
		return branch
	current = (get_current_school_branch() or {}).get("name")
	if current in allowed:
		return current
	return options[0]["value"] if options else ""


def _filter_options(options: list[dict], query: str) -> list[dict]:
	needle = str(query or "").strip().lower()
	if not needle:
		return options[:MAX_OPTIONS]
	return [
		row
		for row in options
		if needle in str(row.get("value") or "").lower()
		or needle in str(row.get("label") or "").lower()
		or needle in str(row.get("description") or "").lower()
	][:MAX_OPTIONS]


def _schedule_values(doc) -> dict:
	fields = (*SCHEDULE_EDITABLE_FIELDS, *SCHEDULE_SNAPSHOT_FIELDS)
	values = {fieldname: doc.get(fieldname) for fieldname in fields}
	values.update(
		{
			"name": doc.name,
			"exam_scope": doc.exam_scope,
			"scheduled_end": doc.scheduled_end,
			"status": doc.status,
			"status_change_reason": doc.status_change_reason,
			"activated_by": doc.activated_by,
			"activated_on": doc.activated_on,
		}
	)
	return values


def _assignment_values(doc) -> dict:
	return {
		"name": doc.name,
		"exam_schedule": doc.exam_schedule,
		"exam_template": doc.exam_template,
		"exam_scope": doc.exam_scope,
		"school_branch": doc.school_branch,
		"course": doc.course,
		"candidate_type": doc.candidate_type,
		"student": doc.student,
		"student_name": doc.student_name,
		"public_candidate_reference": doc.public_candidate_reference,
		"candidate_name": doc.candidate_name,
		"student_group": doc.student_group,
		"eligibility_source": doc.eligibility_source,
		"approved_extra_time_minutes": cint(doc.approved_extra_time_minutes),
		"access_start": doc.access_start,
		"access_end": doc.access_end,
		"assignment_status": doc.assignment_status,
		"status_change_reason": doc.status_change_reason,
		"assigned_by": doc.assigned_by,
		"assigned_on": doc.assigned_on,
		"checked_in_by": doc.checked_in_by,
		"checked_in_on": doc.checked_in_on,
		"notes": doc.notes or "",
	}


def _schedule_rows(exam_scope: str, branch: str, status: str | None, search: str | None) -> list[dict]:
	filters: dict[str, Any] = {"exam_scope": exam_scope}
	if exam_scope == SCHOOL_EXAM:
		filters["school_branch"] = branch
	if status:
		filters["status"] = status
	or_filters = None
	query = str(search or "").strip()
	if query:
		pattern = f"%{query}%"
		or_filters = [
			["schedule_title", "like", pattern],
			["schedule_code", "like", pattern],
			["exam_template", "like", pattern],
			["course", "like", pattern],
			["student_group", "like", pattern],
		]
	rows = frappe.get_list(
		SCHEDULE_DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"schedule_title",
			"schedule_code",
			"exam_template",
			"exam_scope",
			"school_branch",
			"course",
			"student_group",
			"examination_centre",
			"scheduled_start",
			"scheduled_end",
			"status",
			"primary_invigilator",
			"duration_minutes",
			"activated_by",
			"activated_on",
			"modified",
		],
		order_by="scheduled_start desc, modified desc",
		limit_page_length=MAX_LIST_ROWS,
	)
	return [dict(row) for row in rows]


def _candidate_rows(schedule: str) -> list[dict]:
	if not frappe.has_permission(ASSIGNMENT_DOCTYPE, "read"):
		return []
	rows = frappe.get_list(
		ASSIGNMENT_DOCTYPE,
		filters={"exam_schedule": schedule},
		fields=[
			"name",
			"candidate_type",
			"student",
			"student_name",
			"public_candidate_reference",
			"candidate_name",
			"student_group",
			"eligibility_source",
			"approved_extra_time_minutes",
			"access_start",
			"access_end",
			"assignment_status",
			"status_change_reason",
			"assigned_by",
			"assigned_on",
			"checked_in_by",
			"checked_in_on",
		],
		order_by="candidate_name asc, student_name asc, creation asc",
		limit_page_length=MAX_LIST_ROWS,
	)
	return [dict(row) for row in rows]


def _intervention_rows(schedule: str) -> list[dict]:
	if not frappe.has_permission(INTERVENTION_DOCTYPE, "read"):
		return []
	rows = frappe.get_list(
		INTERVENTION_DOCTYPE,
		filters={"exam_schedule": schedule},
		fields=[
			"name",
			"candidate_assignment",
			"student",
			"public_candidate_reference",
			"candidate_status_snapshot",
			"intervention_type",
			"reason",
			"additional_minutes",
			"previous_value",
			"new_value",
			"outcome",
			"requires_attempt_review",
			"acted_by",
			"acted_on",
		],
		order_by="acted_on desc, creation desc",
		limit_page_length=MAX_LIST_ROWS,
	)
	return [dict(row) for row in rows]


def _lifecycle_rows(schedule: str) -> list[dict]:
	if not frappe.has_permission(LIFECYCLE_DOCTYPE, "read"):
		return []
	rows = frappe.get_list(
		LIFECYCLE_DOCTYPE,
		filters={"exam_schedule": schedule},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"candidate_assignment",
			"event_type",
			"from_status",
			"to_status",
			"reason",
			"acted_by",
			"acted_on",
		],
		order_by="acted_on desc, creation desc",
		limit_page_length=MAX_LIST_ROWS,
	)
	return [dict(row) for row in rows]


def _candidate_counts(rows: list[dict]) -> dict:
	return {
		"total": len(rows),
		"eligible": sum(1 for row in rows if row.get("assignment_status") == "Eligible"),
		"checked_in": sum(1 for row in rows if row.get("assignment_status") == "Checked In"),
		"released": sum(1 for row in rows if row.get("assignment_status") == "Released"),
		"completed": sum(1 for row in rows if row.get("assignment_status") == "Completed"),
		"exceptions": sum(
			1 for row in rows if row.get("assignment_status") in {"Withdrawn", "Disqualified"}
		),
	}


@frappe.whitelist()
def get_context(
	exam_scope: str | None = None,
	branch: str | None = None,
	status: str | None = None,
	search: str | None = None,
	schedule: str | None = None,
) -> dict:
	_require_permission(SCHEDULE_DOCTYPE, "read")
	exam_scope = exam_scope or SCHOOL_EXAM
	if exam_scope not in {SCHOOL_EXAM, PUBLIC_EXAM}:
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)
	branches = _branch_options()
	selected_branch = ""
	if exam_scope == SCHOOL_EXAM:
		selected_branch = _select_branch(branch, branches)
		if not selected_branch:
			return _empty_context(exam_scope, branches)
	else:
		require_public_exam_authoring()

	rows = _schedule_rows(exam_scope, selected_branch, status, search)
	selected_name = schedule if schedule and any(row["name"] == schedule for row in rows) else ""
	if schedule and not selected_name:
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, schedule)
		doc.check_permission("read")
		if doc.exam_scope != exam_scope or (exam_scope == SCHOOL_EXAM and doc.school_branch != selected_branch):
			frappe.throw(_("The selected Schedule is outside the current operational scope."), frappe.PermissionError)
		selected_name = doc.name
	if not selected_name and rows:
		selected_name = rows[0]["name"]

	selected_schedule = None
	candidates: list[dict] = []
	interventions: list[dict] = []
	lifecycle: list[dict] = []
	if selected_name:
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, selected_name)
		doc.check_permission("read")
		selected_schedule = _schedule_values(doc)
		candidates = _candidate_rows(doc.name)
		interventions = _intervention_rows(doc.name)
		lifecycle = _lifecycle_rows(doc.name)

	public_access = get_public_exam_capability_summary(frappe.session.user)
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	return {
		"exam_scope": exam_scope,
		"branch": selected_branch,
		"branch_options": branches,
		"schedules": rows,
		"selected_schedule": selected_schedule,
		"candidates": candidates,
		"interventions": interventions,
		"lifecycle": lifecycle,
		"counts": {
			"schedules": len(rows),
			"ready": sum(1 for row in rows if row.get("status") == "Ready"),
			"active": sum(1 for row in rows if row.get("status") == "Active"),
			"completed": sum(1 for row in rows if row.get("status") == "Completed"),
			"candidates": len(candidates),
		},
		"candidate_counts": _candidate_counts(candidates),
		"permissions": {
			"schedule": _permissions(SCHEDULE_DOCTYPE),
			"candidate": _permissions(ASSIGNMENT_DOCTYPE),
			"intervention": _permissions(INTERVENTION_DOCTYPE),
			"lifecycle": _permissions(LIFECYCLE_DOCTYPE),
		},
		"can_manage_public": bool(public_access.get("capabilities", {}).get("author", {}).get("allowed")),
		"user": {"name": frappe.session.user, "full_name": full_name},
	}


def _empty_context(exam_scope: str, branches: list[dict]) -> dict:
	return {
		"exam_scope": exam_scope,
		"branch": "",
		"branch_options": branches,
		"schedules": [],
		"selected_schedule": None,
		"candidates": [],
		"interventions": [],
		"lifecycle": [],
		"counts": {"schedules": 0, "ready": 0, "active": 0, "candidates": 0},
		"candidate_counts": _candidate_counts([]),
		"permissions": {
			"schedule": _permissions(SCHEDULE_DOCTYPE),
			"candidate": _permissions(ASSIGNMENT_DOCTYPE),
			"intervention": _permissions(INTERVENTION_DOCTYPE),
			"lifecycle": _permissions(LIFECYCLE_DOCTYPE),
		},
	}


@frappe.whitelist()
def get_schedule(name: str) -> dict:
	_require_permission(SCHEDULE_DOCTYPE, "read")
	doc = frappe.get_doc(SCHEDULE_DOCTYPE, name)
	doc.check_permission("read")
	return {"name": doc.name, "values": _schedule_values(doc), "can_write": bool(doc.has_permission("write"))}


@frappe.whitelist()
def get_candidate(name: str) -> dict:
	_require_permission(ASSIGNMENT_DOCTYPE, "read")
	doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("read")
	return {"name": doc.name, "values": _assignment_values(doc), "can_write": bool(doc.has_permission("write"))}


@frappe.whitelist()
def get_template_context(template: str, school_branch: str | None = None) -> dict:
	_require_permission(TEMPLATE_DOCTYPE, "read")
	doc = frappe.get_doc(TEMPLATE_DOCTYPE, template)
	doc.check_permission("read")
	if doc.status != "Approved":
		frappe.throw(_("Select an Approved CBT Exam Template."), frappe.ValidationError)
	if doc.template_mode != MODE_FIXED:
		frappe.throw(
			_("Policy Blueprint scheduling is not available until question generation and snapshotting are implemented."),
			frappe.ValidationError,
		)
	resolved_branch = doc.school_branch or school_branch or ""
	if doc.exam_scope == SCHOOL_EXAM:
		if not resolved_branch:
			frappe.throw(_("Select a School Branch / Campus for this Template."), frappe.ValidationError)
		branch = _branch_row(resolved_branch)
		if doc.template_reuse_scope == "Branch-wide" and doc.school_branch != resolved_branch:
			frappe.throw(_("This Branch-wide Template cannot be used by the selected Branch."), frappe.PermissionError)
		if doc.template_reuse_scope == "Institution-wide" and doc.institution != branch.get("institution"):
			frappe.throw(_("This Institution-wide Template cannot be used by the selected Branch."), frappe.PermissionError)
		if doc.template_reuse_scope == "Universal" and doc.company != branch.get("company"):
			frappe.throw(_("This Universal Template cannot be used by the selected Branch."), frappe.PermissionError)
	else:
		require_public_exam_authoring()
		resolved_branch = ""
	return {
		"name": doc.name,
		"label": doc.template_title or doc.name,
		"exam_scope": doc.exam_scope,
		"school_branch": resolved_branch,
		"course": doc.course if doc.subject_applicability == "Specific Subject" else "",
		"subject_applicability": doc.subject_applicability,
		"default_examination_centre": doc.default_examination_centre or "",
		"student_group": _compatible_group_default(doc.student_group, resolved_branch),
		"academic_year": doc.academic_year or "",
		"academic_term": doc.academic_term or "",
		"program": doc.program or "",
		"assessment_group": doc.assessment_group or "",
		"snapshot": {fieldname: doc.get(fieldname) for fieldname in SCHEDULE_SNAPSHOT_FIELDS},
	}


def _branch_row(branch: str) -> dict:
	assert_branch_access(branch)
	row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["name", "branch_name", "institution", "company", "enabled"],
		as_dict=True,
	)
	if not row or not cint(row.enabled):
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
	return dict(row)


def _compatible_group_default(student_group: str | None, branch: str | None) -> str:
	if not student_group or not branch:
		return ""
	return student_group if frappe.db.get_value("Student Group", student_group, BRANCH_FIELD) == branch else ""


@frappe.whitelist()
def save_schedule(values: str | dict, name: str | None = None) -> dict:
	payload = _parse_json(values)
	if name:
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, name)
		doc.check_permission("write")
		action = "update_cbt_exam_schedule"
	else:
		_require_permission(SCHEDULE_DOCTYPE, "create")
		doc = frappe.new_doc(SCHEDULE_DOCTYPE)
		doc.status = "Draft"
		action = "create_cbt_exam_schedule"
	for fieldname in SCHEDULE_EDITABLE_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	if not doc.school_branch and payload.get("page_branch"):
		doc.school_branch = payload.get("page_branch")
	require_eduedge_access(
		feature_key="cbt",
		action=action,
		reference_doctype=SCHEDULE_DOCTYPE,
		reference_name=name,
	)
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return {"name": doc.name, "values": _schedule_values(doc)}


@frappe.whitelist()
def set_schedule_status(name: str, status: str, reason: str | None = None) -> dict:
	doc = frappe.get_doc(SCHEDULE_DOCTYPE, name)
	doc.check_permission("write")
	require_eduedge_access(
		feature_key="cbt",
		action=f"set_cbt_schedule_{str(status or '').lower().replace(' ', '_')}",
		reference_doctype=SCHEDULE_DOCTYPE,
		reference_name=doc.name,
	)
	doc.status = status
	doc.status_change_reason = str(reason or "").strip()
	doc.save()
	return {"name": doc.name, "status": doc.status, "activated_by": doc.activated_by, "activated_on": doc.activated_on}


@frappe.whitelist()
def save_candidate(values: str | dict, name: str | None = None) -> dict:
	payload = _parse_json(values)
	if name:
		doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
		doc.check_permission("write")
		action = "update_cbt_candidate_assignment"
	else:
		_require_permission(ASSIGNMENT_DOCTYPE, "create")
		doc = frappe.new_doc(ASSIGNMENT_DOCTYPE)
		action = "create_cbt_candidate_assignment"
	for fieldname in ASSIGNMENT_EDITABLE_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	if doc.is_new():
		doc.assignment_status = payload.get("assignment_status") or "Eligible"
	require_eduedge_access(
		feature_key="cbt",
		action=action,
		reference_doctype=ASSIGNMENT_DOCTYPE,
		reference_name=name,
	)
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return {"name": doc.name, "values": _assignment_values(doc)}


@frappe.whitelist()
def set_candidate_status(name: str, status: str, reason: str | None = None) -> dict:
	doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("write")
	require_eduedge_access(
		feature_key="cbt",
		action=f"set_cbt_candidate_{str(status or '').lower().replace(' ', '_')}",
		reference_doctype=ASSIGNMENT_DOCTYPE,
		reference_name=doc.name,
	)
	doc.assignment_status = status
	doc.status_change_reason = str(reason or "").strip()
	doc.save()
	return {"name": doc.name, "status": doc.assignment_status}


@frappe.whitelist()
def assign_template_student_group(schedule: str) -> dict:
	_require_permission(ASSIGNMENT_DOCTYPE, "create")
	schedule_doc = frappe.get_doc(SCHEDULE_DOCTYPE, schedule)
	schedule_doc.check_permission("read")
	if schedule_doc.exam_scope != SCHOOL_EXAM:
		frappe.throw(_("Bulk class assignment is available only for School Examinations."), frappe.ValidationError)
	if schedule_doc.status not in {"Draft", "Ready"}:
		frappe.throw(_("Candidates can be assigned only while the Schedule is Draft or Ready."), frappe.ValidationError)
	student_group = schedule_doc.student_group
	if not student_group:
		frappe.throw(_("Select the actual Student Group / Class on the Schedule first."), frappe.ValidationError)
	rows = frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "active": 1},
		fields=["student"],
		order_by="idx asc",
	)
	existing = {
		row.student
		for row in frappe.get_all(
			ASSIGNMENT_DOCTYPE,
			filters={"exam_schedule": schedule_doc.name},
			fields=["student"],
		)
		if row.student
	}
	require_eduedge_access(
		feature_key="cbt",
		action="bulk_assign_cbt_schedule_class",
		reference_doctype=SCHEDULE_DOCTYPE,
		reference_name=schedule_doc.name,
	)
	created: list[str] = []
	skipped: list[str] = []
	for row in rows:
		if not row.student or row.student in existing:
			skipped.append(row.student or "")
			continue
		doc = frappe.new_doc(ASSIGNMENT_DOCTYPE)
		doc.exam_schedule = schedule_doc.name
		doc.student = row.student
		doc.assignment_status = "Eligible"
		try:
			doc.insert()
		except frappe.DuplicateEntryError:
			skipped.append(row.student)
			continue
		created.append(doc.name)
		existing.add(row.student)
	return {"created": created, "skipped": skipped, "student_group": student_group}


@frappe.whitelist()
def record_intervention(values: str | dict) -> dict:
	_require_permission(INTERVENTION_DOCTYPE, "create")
	payload = _parse_json(values)
	doc = frappe.new_doc(INTERVENTION_DOCTYPE)
	for fieldname in ("candidate_assignment", "intervention_type", "reason", "additional_minutes"):
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	require_eduedge_access(
		feature_key="cbt",
		action="record_cbt_intervention",
		reference_doctype=ASSIGNMENT_DOCTYPE,
		reference_name=doc.candidate_assignment,
	)
	doc.insert()
	return {
		"name": doc.name,
		"exam_schedule": doc.exam_schedule,
		"candidate_assignment": doc.candidate_assignment,
		"outcome": doc.outcome,
	}


@frappe.whitelist()
def search_options(fieldname: str, txt: str | None = None, values: str | dict | None = None) -> list[dict]:
	_require_login()
	payload = _parse_json(values)
	query = str(txt or "").strip()
	branches = _branch_options()
	if fieldname == "school_branch":
		_require_permission("EduEdge School Branch", "read")
		return _filter_options(branches, query)
	if fieldname == "exam_template":
		return _template_options(payload, query)
	if fieldname == "course":
		return _course_options(payload, query)
	if fieldname == "examination_centre":
		return _centre_options(payload, query)
	if fieldname == "primary_invigilator":
		return _invigilator_options(payload, query)
	if fieldname == "student":
		return _student_options(payload, query)
	if fieldname == "student_group":
		return _student_group_options(payload, query)
	if fieldname == "academic_year":
		return _simple_link_options("Academic Year", "year_start_date", query)
	if fieldname == "academic_term":
		filters = {"academic_year": payload.get("academic_year")} if payload.get("academic_year") else {}
		return _simple_link_options("Academic Term", "term_name", query, filters)
	if fieldname == "program":
		return _simple_link_options("Program", "program_name", query)
	if fieldname == "assessment_group":
		return _simple_link_options("Assessment Group", "assessment_group_name", query)
	frappe.throw(_("This field does not support option search."), frappe.ValidationError)


def _template_options(payload: dict, query: str) -> list[dict]:
	_require_permission(TEMPLATE_DOCTYPE, "read")
	exam_scope = payload.get("exam_scope") or SCHOOL_EXAM
	branch_name = payload.get("school_branch") or payload.get("page_branch") or ""
	branch = _branch_row(branch_name) if exam_scope == SCHOOL_EXAM else {}
	if exam_scope == PUBLIC_EXAM:
		require_public_exam_authoring()
	rows = frappe.get_list(
		TEMPLATE_DOCTYPE,
		filters={"status": "Approved", "exam_scope": exam_scope, "template_mode": MODE_FIXED},
		fields=[
			"name",
			"template_title",
			"template_code",
			"template_reuse_scope",
			"company",
			"institution",
			"school_branch",
			"course",
			"duration_minutes",
		],
		order_by="template_title asc",
		limit_page_length=MAX_LIST_ROWS,
	)
	options = []
	for row in rows:
		if exam_scope == SCHOOL_EXAM:
			if row.template_reuse_scope == "Branch-wide" and row.school_branch != branch_name:
				continue
			if row.template_reuse_scope == "Institution-wide" and row.institution != branch.get("institution"):
				continue
			if row.template_reuse_scope == "Universal" and row.company != branch.get("company"):
				continue
		options.append(
			{
				"value": row.name,
				"label": row.template_title or row.name,
				"description": _("{0} · {1} · {2} minutes").format(
					row.template_code or row.name, row.course or "Fixed Question Set", row.duration_minutes or 0
				),
			}
		)
	return _filter_options(options, query)


def _course_options(payload: dict, query: str) -> list[dict]:
	_require_permission("Course", "read")
	template_name = payload.get("exam_template")
	if template_name:
		template = frappe.db.get_value(
			TEMPLATE_DOCTYPE,
			template_name,
			["subject_applicability", "course"],
			as_dict=True,
		)
		if template and template.subject_applicability == "Specific Subject":
			label = frappe.db.get_value("Course", template.course, "course_name") or template.course
			return [{"value": template.course, "label": label}]
	filters: dict[str, Any] = {}
	branch_name = payload.get("school_branch") or payload.get("page_branch") or ""
	if branch_name:
		branch = _branch_row(branch_name)
		meta = frappe.get_meta("Course")
		if meta.has_field("eduedge_institution"):
			filters["eduedge_institution"] = branch.get("institution")
	pattern = f"%{query}%"
	rows = frappe.get_list(
		"Course",
		filters=filters,
		or_filters=[["name", "like", pattern], ["course_name", "like", pattern]],
		fields=["name", "course_name"],
		order_by="course_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [{"value": row.name, "label": row.course_name or row.name} for row in rows]


def _centre_options(payload: dict, query: str) -> list[dict]:
	_require_permission(CENTRE_DOCTYPE, "read")
	exam_scope = payload.get("exam_scope") or SCHOOL_EXAM
	filters: dict[str, Any] = {
		"centre_status": "Active",
		"enabled": 1,
		"centre_type": SCHOOL_CENTRE if exam_scope == SCHOOL_EXAM else PUBLIC_CENTRE,
	}
	if exam_scope == SCHOOL_EXAM:
		branch_name = payload.get("school_branch") or payload.get("page_branch") or ""
		filters["school_branch"] = _branch_row(branch_name).get("name")
	else:
		require_public_exam_authoring()
	pattern = f"%{query}%"
	rows = frappe.get_list(
		CENTRE_DOCTYPE,
		filters=filters,
		or_filters=[["centre_name", "like", pattern], ["centre_code", "like", pattern], ["location", "like", pattern]],
		fields=["name", "centre_name", "centre_code", "location", "capacity"],
		order_by="centre_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{
			"value": row.name,
			"label": row.centre_name or row.name,
			"description": _("{0} · Capacity {1}").format(row.location or row.centre_code, row.capacity or 0),
		}
		for row in rows
	]


def _invigilator_options(payload: dict, query: str) -> list[dict]:
	branch = payload.get("school_branch") or payload.get("page_branch") or ""
	pattern = f"%{query}%"
	rows = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		or_filters=[["name", "like", pattern], ["full_name", "like", pattern]],
		fields=["name", "full_name"],
		order_by="full_name asc",
		limit_page_length=MAX_OPTIONS * 3,
	)
	options = []
	for row in rows:
		if not set(frappe.get_roles(row.name)).intersection(INVIGILATOR_ROLES):
			continue
		try:
			assert_user_branch_access(row.name, branch, _("Invigilator"))
		except frappe.PermissionError:
			continue
		options.append({"value": row.name, "label": row.full_name or row.name, "description": row.name})
	return options[:MAX_OPTIONS]


def _student_options(payload: dict, query: str) -> list[dict]:
	_require_permission("Student", "read")
	schedule_name = payload.get("exam_schedule")
	if not schedule_name:
		return []
	schedule_doc = frappe.get_doc(SCHEDULE_DOCTYPE, schedule_name)
	schedule_doc.check_permission("read")
	if schedule_doc.exam_scope != SCHOOL_EXAM:
		return []
	filters: dict[str, Any] = {BRANCH_FIELD: schedule_doc.school_branch}
	if schedule_doc.student_group:
		members = [
			row.student
			for row in frappe.get_all(
				"Student Group Student",
				filters={"parent": schedule_doc.student_group, "active": 1},
				fields=["student"],
			)
		]
		filters["name"] = ["in", members or [""]]
	pattern = f"%{query}%"
	rows = frappe.get_list(
		"Student",
		filters=filters,
		or_filters=[["name", "like", pattern], ["student_name", "like", pattern]],
		fields=["name", "student_name"],
		order_by="student_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [{"value": row.name, "label": row.student_name or row.name, "description": row.name} for row in rows]


def _student_group_options(payload: dict, query: str) -> list[dict]:
	_require_permission("Student Group", "read")
	branch = payload.get("school_branch") or payload.get("page_branch") or ""
	if not branch:
		return []
	_branch_row(branch)
	filters: dict[str, Any] = {BRANCH_FIELD: branch, "disabled": 0}
	if payload.get("course"):
		filters["course"] = payload.get("course")
	pattern = f"%{query}%"
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		or_filters=[["name", "like", pattern], ["student_group_name", "like", pattern]],
		fields=["name", "student_group_name", "academic_year", "academic_term", "program", "course"],
		order_by="student_group_name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{
			"value": row.name,
			"label": row.student_group_name or row.name,
			"description": " · ".join(filter(None, [row.academic_year, row.academic_term, row.program, row.course])),
		}
		for row in rows
	]


def _simple_link_options(doctype: str, title_field: str, query: str, filters: dict | None = None) -> list[dict]:
	_require_permission(doctype, "read")
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	if meta.has_field(title_field):
		fields.append(title_field)
	pattern = f"%{query}%"
	or_filters = [["name", "like", pattern]]
	if meta.has_field(title_field):
		or_filters.append([title_field, "like", pattern])
	rows = frappe.get_list(
		doctype,
		filters=filters or {},
		or_filters=or_filters,
		fields=fields,
		order_by=f"{title_field} asc" if meta.has_field(title_field) else "name asc",
		limit_page_length=MAX_OPTIONS,
	)
	return [
		{"value": row.name, "label": row.get(title_field) or row.name}
		for row in rows
	]
