from __future__ import annotations

import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt

from eduedge.cbt.public_access import can_author_public_exams, require_public_exam_authoring
from eduedge.eduedge.doctype.eduedge_cbt_exam_template.eduedge_cbt_exam_template import (
	PUBLIC_EXAM,
	SCHOOL_EXAM,
	can_review_templates,
)
from eduedge.platform.access import require_eduedge_access
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

TEMPLATE_DOCTYPE = "EduEdge CBT Exam Template"
QUESTION_DOCTYPE = "EduEdge CBT Question"
SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"
STATUSES = ("Draft", "Under Review", "Approved", "Retired")
EXAM_BODIES = ("School Internal", "WAEC", "NECO", "JAMB", "Post-UTME", "Other")
PAGE_LENGTH_OPTIONS = (20, 50, 100)
DEFAULT_PAGE_LENGTH = 20
MAX_OPTIONS = 50
SORT_OPTIONS = {
	"modified_desc": "modified desc",
	"modified_asc": "modified asc",
	"code_asc": "template_code asc",
	"code_desc": "template_code desc",
	"title_asc": "template_title asc",
	"status_asc": "status asc, modified desc",
}
EDITABLE_FIELDS = (
	"template_title",
	"exam_scope",
	"school_branch",
	"version_number",
	"supersedes_template",
	"academic_year",
	"academic_term",
	"program",
	"student_group",
	"course",
	"assessment_group",
	"exam_body",
	"default_examination_centre",
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
	"candidate_instructions",
	"notes",
)


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission(TEMPLATE_DOCTYPE, permission_type):
		frappe.throw(
			_("You are not permitted to {0} CBT exam templates.").format(permission_type),
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


def _option(value: str, label: str | None = None, description: str = "", **extra) -> dict:
	return {
		"value": value,
		"label": label or value,
		"description": description,
		**extra,
	}


def _allowed_branch_rows() -> list[dict]:
	allowed = get_allowed_school_branches()
	names = [row.get("name") for row in allowed if row.get("name")]
	if not names:
		return []
	rows = frappe.get_all(
		"EduEdge School Branch",
		filters={"name": ["in", names], "enabled": 1},
		fields=["name", "branch_name", "company", "institution", "institution_type", "is_default"],
		order_by="is_default desc, branch_name asc",
	)
	return [dict(row) for row in rows]


def _branch_options(branches: list[dict], institution: str = "") -> list[dict]:
	return [
		_option(
			row.get("name"),
			row.get("branch_name") or row.get("name"),
			row.get("company") or "",
			institution=row.get("institution") or "",
		)
		for row in branches
		if not institution or row.get("institution") == institution
	]


def _institution_options(branches: list[dict]) -> list[dict]:
	names = sorted({row.get("institution") for row in branches if row.get("institution")})
	if not names:
		return []
	rows = frappe.get_all(
		"EduEdge Institution",
		filters={"name": ["in", names], "enabled": 1},
		fields=["name", "institution_name", "institution_type", "company", "is_default"],
		order_by="is_default desc, institution_name asc",
	)
	return [
		_option(
			row.name,
			row.institution_name or row.name,
			row.institution_type or "",
			company=row.company or "",
		)
		for row in rows
	]


def _require_allowed(value: str | None, allowed: set[str], label: str, *, optional: bool = True) -> str:
	cleaned = str(value or "").strip()
	if not cleaned and optional:
		return ""
	if cleaned not in allowed:
		frappe.throw(_("Select a permitted {0}.").format(label), frappe.PermissionError)
	return cleaned


def _resolve_scope(exam_scope: str | None) -> str:
	resolved = str(exam_scope or SCHOOL_EXAM).strip()
	if resolved not in {SCHOOL_EXAM, PUBLIC_EXAM}:
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)
	if resolved == PUBLIC_EXAM:
		require_public_exam_authoring()
	return resolved


def _normalise_page_length(value: int | str) -> int:
	resolved = cint(value) or DEFAULT_PAGE_LENGTH
	return resolved if resolved in PAGE_LENGTH_OPTIONS else DEFAULT_PAGE_LENGTH


def _clamp_start(start: int | str, total: int, page_length: int) -> int:
	if total <= 0:
		return 0
	requested = max(0, cint(start))
	last_start = ((total - 1) // page_length) * page_length
	return min(requested, last_start)


def _search_or_filters(search: str) -> list[list[str]]:
	if not search:
		return []
	pattern = f"%{search}%"
	return [
		["template_title", "like", pattern],
		["template_code", "like", pattern],
		["course", "like", pattern],
		["program", "like", pattern],
		["student_group", "like", pattern],
	]


def _list_filters(
	*,
	exam_scope: str,
	institution: str,
	branch: str,
	course: str,
	status: str,
	exam_body: str,
	academic_year: str,
	branches: list[dict],
	include_status: bool = True,
) -> dict:
	filters: dict[str, Any] = {"exam_scope": exam_scope}
	if exam_scope == SCHOOL_EXAM:
		if branch:
			filters["school_branch"] = branch
		elif institution:
			names = sorted(row.get("name") for row in branches if row.get("institution") == institution)
			filters["school_branch"] = ["in", names or [""]]
		else:
			filters["school_branch"] = ["in", sorted(row.get("name") for row in branches) or [""]]
	if course:
		filters["course"] = course
	if include_status and status:
		filters["status"] = status
	if exam_body:
		filters["exam_body"] = exam_body
	if academic_year and exam_scope == SCHOOL_EXAM:
		filters["academic_year"] = academic_year
	return filters


def _status_counts(base_filters: dict, or_filters: list[list[str]]) -> dict:
	counts = {"Total": frappe.db.count(TEMPLATE_DOCTYPE, filters=base_filters, or_filters=or_filters or None)}
	for status in STATUSES:
		filters = dict(base_filters)
		filters["status"] = status
		counts[status] = frappe.db.count(TEMPLATE_DOCTYPE, filters=filters, or_filters=or_filters or None)
	return counts


def _course_label_map(rows: list[dict]) -> dict[str, str]:
	names = sorted({row.get("course") for row in rows if row.get("course")})
	if not names:
		return {}
	return {
		row.name: row.course_name or row.name
		for row in frappe.get_all("Course", filters={"name": ["in", names]}, fields=["name", "course_name"])
	}


@frappe.whitelist()
def get_exam_templates(
	search: str | None = None,
	exam_scope: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	course: str | None = None,
	status: str | None = None,
	exam_body: str | None = None,
	academic_year: str | None = None,
	sort_by: str | None = None,
	start: int = 0,
	page_length: int = DEFAULT_PAGE_LENGTH,
) -> dict:
	_require_permission("read")
	branches = _allowed_branch_rows()
	institutions = _institution_options(branches)
	resolved_scope = _resolve_scope(exam_scope)
	resolved_institution = ""
	resolved_branch = ""
	if resolved_scope == SCHOOL_EXAM:
		resolved_institution = _require_allowed(
			institution,
			{row["value"] for row in institutions},
			_("Institution"),
		)
		visible_branches = _branch_options(branches, resolved_institution)
		resolved_branch = _require_allowed(
			branch,
			{row["value"] for row in visible_branches},
			_("Branch / Campus"),
		)
	else:
		visible_branches = []

	resolved_status = str(status or "").strip()
	if resolved_status and resolved_status not in STATUSES:
		resolved_status = ""
	resolved_exam_body = str(exam_body or "").strip()
	if resolved_exam_body and resolved_exam_body not in EXAM_BODIES:
		resolved_exam_body = ""
	resolved_search = str(search or "").strip()[:120]
	resolved_sort = sort_by if sort_by in SORT_OPTIONS else "modified_desc"
	resolved_page_length = _normalise_page_length(page_length)
	resolved_course = str(course or "").strip()
	if resolved_course and not frappe.db.exists("Course", resolved_course):
		frappe.throw(_("Select a valid Subject / Course."), frappe.ValidationError)
	resolved_academic_year = str(academic_year or "").strip()
	if resolved_academic_year and not frappe.db.exists("Academic Year", resolved_academic_year):
		frappe.throw(_("Select a valid Academic Year."), frappe.ValidationError)

	base_filters = _list_filters(
		exam_scope=resolved_scope,
		institution=resolved_institution,
		branch=resolved_branch,
		course=resolved_course,
		status="",
		exam_body=resolved_exam_body,
		academic_year=resolved_academic_year,
		branches=branches,
		include_status=False,
	)
	row_filters = dict(base_filters)
	if resolved_status:
		row_filters["status"] = resolved_status
	or_filters = _search_or_filters(resolved_search)
	counts = _status_counts(base_filters, or_filters)
	filtered_total = counts.get(resolved_status, 0) if resolved_status else counts["Total"]
	resolved_start = _clamp_start(start, filtered_total, resolved_page_length)

	rows = frappe.get_list(
		TEMPLATE_DOCTYPE,
		filters=row_filters,
		or_filters=or_filters or None,
		fields=[
			"name",
			"template_title",
			"template_code",
			"exam_scope",
			"school_branch",
			"academic_year",
			"academic_term",
			"program",
			"student_group",
			"course",
			"exam_body",
			"duration_minutes",
			"question_count",
			"total_marks",
			"status",
			"version_number",
			"modified",
		],
		order_by=SORT_OPTIONS[resolved_sort],
		start=resolved_start,
		page_length=resolved_page_length,
	)
	serialised = [dict(row) for row in rows]
	branch_map = {row.get("name"): row for row in branches}
	course_map = _course_label_map(serialised)
	for row in serialised:
		branch_row = branch_map.get(row.get("school_branch")) or {}
		row["branch_label"] = branch_row.get("branch_name") or row.get("school_branch") or "EduEdge Public Examination"
		row["institution"] = branch_row.get("institution") or ""
		row["course_label"] = course_map.get(row.get("course"), row.get("course") or "")

	permissions = {
		"can_create": bool(frappe.has_permission(TEMPLATE_DOCTYPE, "create")),
		"can_write": bool(frappe.has_permission(TEMPLATE_DOCTYPE, "write")),
		"can_review": bool(can_review_templates(frappe.session.user)),
	}
	return {
		"rows": serialised,
		"counts": counts,
		"filters": {
			"search": resolved_search,
			"exam_scope": resolved_scope,
			"institution": resolved_institution,
			"branch": resolved_branch,
			"course": resolved_course,
			"status": resolved_status,
			"exam_body": resolved_exam_body,
			"academic_year": resolved_academic_year,
			"sort_by": resolved_sort,
		},
		"options": {
			"scope": [_option(SCHOOL_EXAM)] + ([_option(PUBLIC_EXAM)] if can_author_public_exams(frappe.session.user) else []),
			"institutions": institutions,
			"branches": visible_branches,
			"statuses": [_option(value) for value in STATUSES],
			"exam_bodies": [_option(value) for value in EXAM_BODIES],
			"page_lengths": list(PAGE_LENGTH_OPTIONS),
		},
		"pagination": {
			"start": resolved_start,
			"page_length": resolved_page_length,
			"total": filtered_total,
			"has_previous": resolved_start > 0,
			"has_next": resolved_start + resolved_page_length < filtered_total,
		},
		"permissions": permissions,
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
	}


def _question_rows(doc) -> list[dict]:
	questions = [row.question for row in (doc.get("questions") or []) if row.question]
	labels = {}
	if questions:
		labels = {
			row.name: row.question_code or row.name
			for row in frappe.get_all(
				QUESTION_DOCTYPE,
				filters={"name": ["in", questions]},
				fields=["name", "question_code"],
			)
		}
	return [
		{
			"question": row.question,
			"question_label": labels.get(row.question, row.question),
			"display_order": cint(row.display_order) or cint(row.idx),
			"section_label": row.section_label or "",
			"question_type": row.question_type or "",
			"topic": row.topic or "",
			"mark": flt(row.mark),
			"negative_mark": flt(row.negative_mark),
		}
		for row in (doc.get("questions") or [])
	]


def _serialize_template(doc) -> dict:
	return {
		"name": None if doc.is_new() else doc.name,
		"template_title": doc.template_title or "",
		"template_code": doc.template_code or "",
		"exam_scope": doc.exam_scope or SCHOOL_EXAM,
		"school_branch": doc.school_branch or "",
		"version_number": cint(doc.version_number) or 1,
		"supersedes_template": doc.supersedes_template or "",
		"academic_year": doc.academic_year or "",
		"academic_term": doc.academic_term or "",
		"program": doc.program or "",
		"student_group": doc.student_group or "",
		"course": doc.course or "",
		"assessment_group": doc.assessment_group or "",
		"exam_body": doc.exam_body or "School Internal",
		"default_examination_centre": doc.default_examination_centre or "",
		"duration_minutes": cint(doc.duration_minutes) or 60,
		"maximum_attempts": cint(doc.maximum_attempts) or 1,
		"pass_percentage": flt(doc.pass_percentage),
		"navigation_policy": doc.navigation_policy or "Free Navigation",
		"auto_submit_on_timeout": cint(doc.auto_submit_on_timeout),
		"allow_resume": cint(doc.allow_resume),
		"randomise_questions": cint(doc.randomise_questions),
		"randomise_options": cint(doc.randomise_options),
		"marking_policy": doc.marking_policy or "Use Question Marks",
		"result_release_policy": doc.result_release_policy or "Manual Approval",
		"device_change_policy": doc.device_change_policy or "Invigilator Approval Required",
		"attempt_review_policy": doc.attempt_review_policy or "Review Flagged Attempts Only",
		"questions": _question_rows(doc),
		"question_count": cint(doc.question_count),
		"total_marks": flt(doc.total_marks),
		"total_negative_marks": flt(doc.total_negative_marks),
		"candidate_instructions": doc.candidate_instructions or "",
		"status": doc.status or "Draft",
		"reviewed_by": doc.reviewed_by or "",
		"reviewed_on": doc.reviewed_on,
		"notes": doc.notes or "",
		"modified": str(doc.modified or ""),
	}


def _new_template() -> dict:
	current = get_current_school_branch() or {}
	return {
		"name": None,
		"template_title": "",
		"template_code": "",
		"exam_scope": SCHOOL_EXAM,
		"school_branch": current.get("name") or "",
		"version_number": 1,
		"supersedes_template": "",
		"academic_year": "",
		"academic_term": "",
		"program": "",
		"student_group": "",
		"course": "",
		"assessment_group": "",
		"exam_body": "School Internal",
		"default_examination_centre": "",
		"duration_minutes": 60,
		"maximum_attempts": 1,
		"pass_percentage": 50,
		"navigation_policy": "Free Navigation",
		"auto_submit_on_timeout": 1,
		"allow_resume": 1,
		"randomise_questions": 1,
		"randomise_options": 1,
		"marking_policy": "Use Question Marks",
		"result_release_policy": "Manual Approval",
		"device_change_policy": "Invigilator Approval Required",
		"attempt_review_policy": "Review Flagged Attempts Only",
		"questions": [],
		"question_count": 0,
		"total_marks": 0,
		"total_negative_marks": 0,
		"candidate_instructions": "",
		"status": "Draft",
		"reviewed_by": "",
		"reviewed_on": None,
		"notes": "",
		"modified": "",
	}


def _action_state(doc, *, is_new: bool = False) -> list[dict]:
	status = doc.get("status") if isinstance(doc, dict) else doc.status
	can_write = frappe.has_permission(TEMPLATE_DOCTYPE, "create") if is_new else bool(doc.has_permission("write"))
	can_review = bool(can_review_templates(frappe.session.user))
	if (doc.get("exam_scope") if isinstance(doc, dict) else doc.exam_scope) == PUBLIC_EXAM:
		can_review = bool(can_author_public_exams(frappe.session.user))
	definitions = [
		("submit_for_review", _("Send for Review"), "Draft", "Under Review", can_write, False),
		("return_to_draft", _("Return to Draft"), "Under Review", "Draft", can_write, True),
		("approve", _("Approve Template"), "Under Review", "Approved", can_review, True),
		("retire", _("Retire Template"), "Approved", "Retired", can_review, True),
	]
	return [
		{
			"action": action,
			"label": label,
			"source_status": source,
			"target_status": target,
			"allowed": bool(status == source and capability),
			"reason": "" if status == source and capability else _("This action is unavailable for the current status or permission."),
			"requires_confirmation": confirmation,
		}
		for action, label, source, target, capability, confirmation in definitions
	]


def _builder_response(template: dict, source_doc=None) -> dict:
	is_new = not template.get("name")
	can_write = bool(
		(frappe.has_permission(TEMPLATE_DOCTYPE, "create") if is_new else source_doc and source_doc.has_permission("write"))
		and template.get("status") == "Draft"
	)
	branches = _allowed_branch_rows()
	return {
		"template": template,
		"allowed_branches": _branch_options(branches),
		"scope_options": [_option(SCHOOL_EXAM)] + ([_option(PUBLIC_EXAM)] if can_author_public_exams(frappe.session.user) else []),
		"exam_bodies": list(EXAM_BODIES),
		"navigation_policies": ["Free Navigation", "Forward Only"],
		"marking_policies": ["Use Question Marks", "Disable Negative Marking"],
		"result_release_policies": ["Manual Approval", "After Submission"],
		"device_change_policies": [
			"Not Allowed",
			"Invigilator Approval Required",
			"Administrator Approval Required",
			"Allowed Before First Answer Only",
		],
		"attempt_review_policies": [
			"Review Flagged Attempts Only",
			"Review All Attempts",
			"No Pre-publication Review",
		],
		"permissions": {
			"can_write": can_write,
			"can_create_version": bool(
				template.get("name")
				and template.get("status") in {"Approved", "Retired"}
				and frappe.has_permission(TEMPLATE_DOCTYPE, "create")
			),
			"can_open_technical_record": bool(frappe.has_permission(TEMPLATE_DOCTYPE, "read")),
		},
		"actions": _action_state(source_doc or template, is_new=is_new),
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
	}


@frappe.whitelist()
def get_template_builder_context(template: str | None = None) -> dict:
	if template:
		_require_permission("read")
		doc = frappe.get_doc(TEMPLATE_DOCTYPE, template)
		doc.check_permission("read")
		return _builder_response(_serialize_template(doc), doc)
	_require_login()
	if not frappe.has_permission(TEMPLATE_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create CBT exam templates."), frappe.PermissionError)
	return _builder_response(_new_template())


def _assert_template_scope(values: dict) -> None:
	scope = _resolve_scope(values.get("exam_scope"))
	if scope == PUBLIC_EXAM:
		return
	branches = {row.get("name") for row in _allowed_branch_rows()}
	_require_allowed(values.get("school_branch"), branches, _("Branch / Campus"), optional=False)


@frappe.whitelist()
def save_template(payload: str | dict) -> dict:
	values = _parse_json(payload)
	name = str(values.get("name") or "").strip()
	if name:
		doc = frappe.get_doc(TEMPLATE_DOCTYPE, name)
		doc.check_permission("write")
		if doc.status != "Draft":
			frappe.throw(_("Template content can be changed only while the template is Draft."), frappe.ValidationError)
		if values.get("template_code") and str(values.get("template_code")).strip().upper() != doc.template_code:
			frappe.throw(_("Template Code cannot be changed after the first save."), frappe.ValidationError)
		action = "update_exam_template"
	else:
		_require_permission("create")
		doc = frappe.new_doc(TEMPLATE_DOCTYPE)
		doc.template_code = str(values.get("template_code") or "").strip().upper()
		doc.status = "Draft"
		action = "create_exam_template"

	_assert_template_scope(values)
	for fieldname in EDITABLE_FIELDS:
		if fieldname in values:
			doc.set(fieldname, values.get(fieldname))
	doc.status = "Draft"
	doc.set("questions", [])
	for index, row in enumerate(values.get("questions") or [], start=1):
		doc.append(
			"questions",
			{
				"question": row.get("question"),
				"display_order": cint(row.get("display_order")) or index,
				"section_label": str(row.get("section_label") or "").strip(),
			},
		)
	require_eduedge_access(
		feature_key="cbt",
		action=action,
		reference_doctype=TEMPLATE_DOCTYPE,
		reference_name=name or None,
	)
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return _builder_response(_serialize_template(doc), doc)


@frappe.whitelist()
def perform_template_action(
	template: str,
	action: str,
	expected_modified: str | None = None,
) -> dict:
	_require_permission("read")
	doc = frappe.get_doc(TEMPLATE_DOCTYPE, template)
	doc.check_permission("read")
	if expected_modified and str(doc.modified) != str(expected_modified):
		frappe.throw(
			_("This template changed after the page was loaded. Refresh before applying the action."),
			frappe.TimestampMismatchError,
		)
	actions = {row["action"]: row for row in _action_state(doc)}
	state = actions.get(action)
	if not state or not state.get("allowed"):
		frappe.throw((state or {}).get("reason") or _("This Template action is not available."), frappe.PermissionError)
	require_eduedge_access(
		feature_key="cbt",
		action=f"template_{action}",
		reference_doctype=TEMPLATE_DOCTYPE,
		reference_name=doc.name,
	)
	doc.status = state["target_status"]
	doc.save()
	return _builder_response(_serialize_template(doc), doc)


def _next_template_code(source_code: str, version_number: int) -> str:
	base = re.sub(r"-V\d+(?:-\d+)?$", "", str(source_code or "TEMPLATE").strip().upper())
	candidate = f"{base}-V{version_number}"
	sequence = 2
	while frappe.db.exists(TEMPLATE_DOCTYPE, candidate):
		candidate = f"{base}-V{version_number}-{sequence}"
		sequence += 1
	return candidate


@frappe.whitelist()
def create_template_version(template: str) -> dict:
	_require_permission("create")
	source = frappe.get_doc(TEMPLATE_DOCTYPE, template)
	source.check_permission("read")
	if source.status not in {"Approved", "Retired"}:
		frappe.throw(_("Only an Approved or Retired template can start a new version."), frappe.ValidationError)
	version_number = cint(source.version_number) + 1
	doc = frappe.copy_doc(source)
	doc.name = None
	doc.template_code = _next_template_code(source.template_code, version_number)
	doc.template_title = source.template_title
	doc.version_number = version_number
	doc.supersedes_template = source.name
	doc.status = "Draft"
	doc.reviewed_by = None
	doc.reviewed_on = None
	doc.insert()
	return _builder_response(_serialize_template(doc), doc)


def _filter_rows(rows: list[dict], query: str) -> list[dict]:
	if not query:
		return rows[:MAX_OPTIONS]
	needle = query.lower()
	return [
		row
		for row in rows
		if needle in str(row.get("value") or "").lower()
		or needle in str(row.get("label") or "").lower()
		or needle in str(row.get("description") or "").lower()
	][:MAX_OPTIONS]


def _simple_link_options(doctype: str, query: str, fields: list[str], label_field: str | None = None, filters=None) -> list[dict]:
	pattern = f"%{query}%"
	rows = frappe.get_list(
		doctype,
		filters=filters or {},
		or_filters=[[fieldname, "like", pattern] for fieldname in fields],
		fields=list(dict.fromkeys(["name", *fields])),
		order_by=f"{label_field or 'name'} asc",
		page_length=MAX_OPTIONS,
	)
	return [
		_option(row.name, row.get(label_field) or row.name if label_field else row.name)
		for row in rows
	]


@frappe.whitelist()
def search_template_options(
	fieldname: str,
	txt: str | None = None,
	values: str | dict | None = None,
) -> list[dict]:
	_require_permission("read")
	payload = _parse_json(values)
	query = str(txt or "").strip()
	scope = _resolve_scope(payload.get("exam_scope"))
	branch = str(payload.get("school_branch") or "").strip()
	if scope == SCHOOL_EXAM:
		_require_allowed(branch, {row.get("name") for row in _allowed_branch_rows()}, _("Branch / Campus"), optional=False)

	if fieldname == "school_branch":
		return _filter_rows(_branch_options(_allowed_branch_rows()), query)
	if fieldname == "course":
		filters: dict[str, Any] = {}
		if scope == SCHOOL_EXAM and branch:
			institution = frappe.db.get_value("EduEdge School Branch", branch, "institution")
			meta = frappe.get_meta("Course")
			if institution and meta.has_field("eduedge_institution"):
				filters["eduedge_institution"] = institution
		return _simple_link_options("Course", query, ["name", "course_name"], "course_name", filters)
	if fieldname == "academic_year":
		return _simple_link_options("Academic Year", query, ["name"])
	if fieldname == "academic_term":
		filters = {"academic_year": payload.get("academic_year")} if payload.get("academic_year") else {}
		return _simple_link_options("Academic Term", query, ["name"], filters=filters)
	if fieldname == "program":
		filters: dict[str, Any] = {}
		if branch and frappe.db.exists("DocType", "EduEdge Program Offering"):
			programs = frappe.get_all(
				"EduEdge Program Offering",
				filters={"school_branch": branch, "is_active": 1},
				pluck="program",
			)
			filters["name"] = ["in", programs or [""]]
		return _simple_link_options("Program", query, ["name", "program_name"], "program_name", filters)
	if fieldname == "student_group":
		filters: dict[str, Any] = {"disabled": 0}
		meta = frappe.get_meta("Student Group")
		if branch and meta.has_field("eduedge_school_branch"):
			filters["eduedge_school_branch"] = branch
		for key in ("academic_year", "academic_term", "program"):
			if payload.get(key):
				filters[key] = payload.get(key)
		return _simple_link_options("Student Group", query, ["name", "student_group_name"], "student_group_name", filters)
	if fieldname == "assessment_group":
		return _simple_link_options("Assessment Group", query, ["name"])
	if fieldname == "default_examination_centre":
		filters = {
			"centre_status": "Active",
			"centre_type": SCHOOL_CENTRE if scope == SCHOOL_EXAM else PLATFORM_CENTRE,
		}
		if scope == SCHOOL_EXAM:
			filters["school_branch"] = branch
		return _simple_link_options(
			"EduEdge Examination Centre",
			query,
			["name", "centre_name", "centre_code", "location"],
			"centre_name",
			filters,
		)
	if fieldname == "supersedes_template":
		filters = {
			"status": ["in", ["Approved", "Retired"]],
			"exam_scope": scope,
			"course": payload.get("course") or "",
			"exam_body": payload.get("exam_body") or "",
		}
		if scope == SCHOOL_EXAM:
			filters["school_branch"] = branch
		return _simple_link_options(TEMPLATE_DOCTYPE, query, ["name", "template_title", "template_code"], "template_title", filters)
	if fieldname == "question":
		course = str(payload.get("course") or "").strip()
		if not course:
			return []
		filters: dict[str, Any] = {
			"status": "Approved",
			"course": course,
			"ownership_scope": SCHOOL_BANK if scope == SCHOOL_EXAM else PLATFORM_BANK,
		}
		if scope == SCHOOL_EXAM:
			filters["school_branch"] = branch
		pattern = f"%{query}%"
		rows = frappe.get_list(
			QUESTION_DOCTYPE,
			filters=filters,
			or_filters=[
				["question_code", "like", pattern],
				["topic", "like", pattern],
				["question_text", "like", pattern],
			],
			fields=["name", "question_code", "question_type", "topic", "difficulty", "default_mark", "negative_mark"],
			order_by="question_code asc",
			page_length=MAX_OPTIONS,
		)
		return [
			_option(
				row.name,
				row.question_code or row.name,
				" · ".join(filter(None, [row.topic, row.question_type, row.difficulty])),
				question_type=row.question_type or "",
				topic=row.topic or "",
				mark=flt(row.default_mark),
				negative_mark=flt(row.negative_mark),
			)
			for row in rows
		]
	frappe.throw(_("This field does not support option search."), frappe.ValidationError)
