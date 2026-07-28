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
from eduedge.education.offerings import assert_branch_access
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

SCHEDULE_DOCTYPE = "EduEdge CBT Exam Schedule"
ASSIGNMENT_DOCTYPE = "EduEdge CBT Candidate Assignment"
INTERVENTION_DOCTYPE = "EduEdge CBT Intervention Log"
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

INTERVENTION_TYPES = (
	"Device Change",
	"Time Extension",
	"Force Submission",
	"Attempt Unlock",
	"Attempt Suspension",
	"Reconnection Approval",
	"Manual Sync Resolution",
	"Candidate Reassignment",
	"Other",
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
		"read": bool(frappe.has_permission(doctype, "read")),
		"create": bool(frappe.has_permission(doctype, "create")),
		"write": bool(frappe.has_permission(doctype, "write")),
		"delete": bool(frappe.has_permission(doctype, "delete")),
	}


def _branch_options() -> list[dict]:
	rows = get_allowed_school_branches()
	return [
		{
			"value": row.get("name"),
			"label": row.get("branch_name") or row.get("name"),
			"description": row.get("institution") or row.get("company") or "",
			"institution": row.get("institution") or "",
			"company": row.get("company") or "",
		}
		for row in rows
		if row.get("name")
	]


def _select_branch(branch: str | None, branch_options: list[dict]) -> str:
	allowed = {row["value"] for row in branch_options}
	if branch:
		if branch not in allowed:
			frappe.throw(_("Select a permitted School Branch / Campus."), frappe.PermissionError)
		assert_branch_access(branch)
		return branch
	current = (get_current_school_branch() or {}).get("name")
	if current in allowed:
		return current
	return branch_options[0]["value"] if branch_options else ""


def _branch_context(branch: str) -> dict:
	if not branch:
		return {}
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
	values = {fieldname: doc.get(fieldname) for fieldname in SCHEDULE_EDITABLE_FIELDS}
	values.update({fieldname: doc.get(fieldname) for fieldname in SCHEDULE_SNAPSHOT_FIELDS})
	values.update(
		{
			"name": doc.name,
			"exam_scope": doc.exam_scope,
			"scheduled_end": doc.scheduled_end,
			"status": doc.status,
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
			"outcome",
			"requires_attempt_review",
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
			1
			for row in rows
			if row.get("assignment_status") in {"Withdrawn", "Disqualified"}
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
			return {
				"exam_scope": exam_scope,
				"branch": "",
				"branch_options": branches,
				"schedules": [],
				"selected_schedule": None,
				"candidates": [],
				"interventions": [],
				"counts": {"schedules": 0, "ready": 0, "active": 0, "candidates": 0},
				"candidate_counts": _candidate_counts([]),
				"permissions": {
					"schedule": _permissions(SCHEDULE_DOCTYPE),
					"candidate": _permissions(ASSIGNMENT_DOCTYPE),
					"intervention": _permissions(INTERVENTION_DOCTYPE),
				},
			}
	else:
		require_public_exam_authoring()

	rows = _schedule_rows(exam_scope, selected_branch, status, search)
	selected_name = schedule if schedule and any(row["name"] == schedule for row in rows) else ""
	if schedule and not selected_name:
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, schedule)
		doc.check_permission("read")
		if doc.exam_scope != exam_scope or (exam_scope == SCHOOL_EXAM and doc.school_branch != selected_branch):
			frappe.throw(_("The selected schedule is outside the current operational scope."), frappe.PermissionError)
		selected_name = doc.name
	if not selected_name and rows:
		selected_name = rows[0]["name"]

	selected_schedule = None
	candidates: list[dict] = []
	interventions: list[dict] = []
	if selected_name:
		doc = frappe.get_doc(SCHEDULE_DOCTYPE, selected_name)
		doc.check_permission("read")
		selected_schedule = _schedule_values(doc)
		selected_schedule["student_group"] = frappe.db.get_value(
			TEMPLATE_DOCTYPE, doc.exam_template, "student_group"
		)
		candidates = _candidate_rows(doc.name)
		interventions = _intervention_rows(doc.name)

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
		},
		"can_manage_public": bool(public_access.get("capabilities", {}).get("author", {}).get("allowed")),
		"user": {"name": frappe.session.user, "full_name": full_name},
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
	_require_permission(SCHEDULE_DOCTYPE, "read")
	row = frappe.db.get_value(
		TEMPLATE_DOCTYPE,
		template,
		[
			"name",
			"template_title",
			"status",
			"exam_scope",
			"template_reuse_scope",
			"company",
			"institution",
			"school_branch",
			"subject_applicability",
			"course",
			"default_examination_centre",
			"student_group",
			*SCHEDULE_SNAPSHOT_FIELDS,
		],
		as_dict=True,
	)
	if not row or row.status != "Approved":
		frappe.throw(_("Select an Approved CBT Exam Template."), frappe.ValidationError)
	resolved_branch = row.school_branch or school_branch or ""
	if row.exam_scope == SCHOOL_EXAM:
		if not resolved_branch:
			frappe.throw(_("Select a School Branch / Campus for this template."), frappe.ValidationError)
		branch = _branch_context(resolved_branch)
		if row.template_reuse_scope == "Branch-wide" and row.school_branch != resolved_branch:
			frappe.throw(_("This Branch-wide template cannot be used by the selected Branch."), frappe.PermissionError)
		if row.template_reuse_scope == "Institution-wide" and row.institution != branch.get("institution"):
			frappe.throw(_("This Institution-wide template cannot be used by the selected Branch."), frappe.PermissionError)
		if row.template_reuse_scope == "Universal" and row.company != branch.get("company"):
			frappe.throw(_("This Universal template cannot be used by the selected Branch."), frappe.PermissionError)
	else:
		require_public_exam_authoring()
		resolved_branch = ""
	return {
		"name": row.name,
		"label": row.template_title or row.name,
		"exam_scope": row.exam_scope,
		"school_branch": resolved_branch,
		"course": row.course if row.subject_applicability == "Specific Subject" else "",
		"subject_applicability": row.subject_applicability,
		"default_examination_centre": row.default_examination_centre or "",
		"student_group": row.student_group or "",
		"snapshot": {fieldname: row.get(fieldname) for fieldname in SCHEDULE_SNAPSHOT_FIELDS},
	}


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
def set_schedule_status(name: str, status: str) -> dict:
	doc = frappe.get_doc(SCHEDULE_DOCTYPE, name)
	doc.check_permission("write")
	require_eduedge_access(
		feature_key="cbt",
		action=f"set_cbt_schedule_{str(status or '').lower().replace(' ', '_')}",
		reference_doctype=SCHEDULE_DOCTYPE,
		reference_name=doc.name,
	)
	doc.status = status
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
def set_candidate_status(name: str, status: str) -> dict:
	doc = frappe.get_doc(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("write")
	require_eduedge_access(
		feature_key="cbt",
		action=f"set_cbt_candidate_{str(status or '').lower().replace(' ', '_')}",
		reference_doctype=ASSIGNMENT_DOCTYPE,
		reference_name=doc.name,
	)
	doc.assignment_status = status
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
		frappe.throw(_("Candidates can be assigned only while the schedule is Draft or Ready."), frappe.ValidationError)
	student_group = frappe.db.get_value(TEMPLATE_DOCTYPE, schedule_doc.exam_template, "student_group")
	if not student_group:
		frappe.throw(_("The selected exam template does not define a Student Group / Class."), frappe.ValidationError)
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
		action="bulk_assign_cbt_template_class",
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
		doc.insert()
		created.append(doc.name)
	return {"created": created, "skipped": skipped, "student_group": student_group}


@frappe.whitelist()
def record_intervention(values: str | dict) -> dict:
	_require_permission(INTERVENTION_DOCTYPE, "create")
	payload = _parse_json(values)
	doc = frappe.new_doc(INTERVENTION_DOCTYPE)
	for fieldname in (
		"candidate_assignment",
		"intervention_type",
		"reason",
		"additional_minutes",
		"previous_value",
		"new_value",
		"attempt_reference",
		"outcome",
	):
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	require_eduedge_access(
		feature_key="cbt",
		action="record_cbt_intervention",
		reference_doctype=ASSIGNMENT_DOCTYPE,
		reference_name=doc.candidate_assignment,
	)
	doc.insert()
	return {"name": doc.name, "exam_schedule": doc.exam_schedule, "candidate_assignment": doc.candidate_assignment}


@frappe.whitelist()
def search_options(fieldname: str, txt: str | None = None, values: str | dict | None = None) -> list[dict]:
	payload = _parse_json(values)
	query = str(txt or "").strip()
	branches = _branch_options()
	if fieldname == "school_branch":
		return _filter_options(branches, query)

	if fieldname == "exam_template":
		_require_permission(TEMPLATE_DOCTYPE, "read")
		exam_scope = payload.get("exam_scope") or SCHOOL_EXAM
		branch_name = payload.get("school_branch") or payload.get("page_branch") or ""
		branch = _branch_context(branch_name) if exam_scope == SCHOOL_EXAM else {}
		if exam_scope == PUBLIC_EXAM:
			require_public_exam_authoring()
		rows = frappe.get_list(
			TEMPLATE_DOCTYPE,
			filters={"status": "Approved", "exam_scope": exam_scope},
			fields=[
				"name",
				"template_title",
				"template_code",
				"template_reuse_scope",
				"company",
				"institution",
				"school_branch",
				"subject_applicability",
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
						row.template_code or row.name,
						row.course or row.subject_applicability,
						row.duration_minutes or 0,
					),
				}
			)
		return _filter_options(options, query)

	if fieldname == "course":
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
			branch = _branch_context(branch_name)
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

	if fieldname == "examination_centre":
		_require_permission(CENTRE_DOCTYPE, "read")
		exam_scope = payload.get("exam_scope") or SCHOOL_EXAM
		filters: dict[str, Any] = {
			"centre_status": "Active",
			"centre_type": SCHOOL_CENTRE if exam_scope == SCHOOL_EXAM else PUBLIC_CENTRE,
		}
		if exam_scope == SCHOOL_EXAM:
			branch_name = payload.get("school_branch") or payload.get("page_branch") or ""
			filters["school_branch"] = _branch_context(branch_name).get("name")
		else:
			require_public_exam_authoring()
		pattern = f"%{query}%"
		rows = frappe.get_list(
			CENTRE_DOCTYPE,
			filters=filters,
			or_filters=[
				["centre_name", "like", pattern],
				["centre_code", "like", pattern],
				["location", "like", pattern],
			],
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

	if fieldname == "primary_invigilator":
		pattern = f"%{query}%"
		rows = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			or_filters=[["name", "like", pattern], ["full_name", "like", pattern]],
			fields=["name", "full_name"],
			order_by="full_name asc",
			limit_page_length=MAX_OPTIONS * 2,
		)
		return [
			{"value": row.name, "label": row.full_name or row.name, "description": row.name}
			for row in rows
			if set(frappe.get_roles(row.name)).intersection(INVIGILATOR_ROLES)
		][:MAX_OPTIONS]

	if fieldname == "student":
		_require_permission("Student", "read")
		schedule_name = payload.get("exam_schedule")
		if not schedule_name:
			return []
		schedule_doc = frappe.get_doc(SCHEDULE_DOCTYPE, schedule_name)
		schedule_doc.check_permission("read")
		if schedule_doc.exam_scope != SCHOOL_EXAM:
			return []
		filters: dict[str, Any] = {}
		meta = frappe.get_meta("Student")
		if meta.has_field("eduedge_school_branch"):
			filters["eduedge_school_branch"] = schedule_doc.school_branch
		student_group = frappe.db.get_value(TEMPLATE_DOCTYPE, schedule_doc.exam_template, "student_group")
		if student_group:
			member_names = [
				row.student
				for row in frappe.get_all(
					"Student Group Student",
					filters={"parent": student_group, "active": 1},
					fields=["student"],
				)
			]
			filters["name"] = ["in", member_names or [""]]
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

	frappe.throw(_("This field does not support option search."), frappe.ValidationError)
