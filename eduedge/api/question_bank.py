from __future__ import annotations

import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, strip_html

from eduedge.cbt.public_access import can_author_public_exams
from eduedge.eduedge.doctype.eduedge_cbt_question.eduedge_cbt_question import PLATFORM_BANK, SCHOOL_BANK
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

QUESTION_DOCTYPE = "EduEdge CBT Question"
STATUSES = (
	"Draft",
	"Under Review",
	"Under Subject Review",
	"Changes Requested",
	"Recommended",
	"Approved",
	"Retired",
)
DIFFICULTIES = ("Easy", "Moderate", "Hard")
QUESTION_TYPES = ("Single Choice", "Multiple Choice", "True/False", "Yes/No", "Short Answer", "Essay", "Numeric")
EXAM_BODIES = ("School Internal", "WAEC", "NECO", "JAMB", "Post-UTME", "Other")
SORT_OPTIONS = {
	"modified_desc": "modified desc",
	"modified_asc": "modified asc",
	"code_asc": "question_code asc",
	"code_desc": "question_code desc",
	"status_asc": "status asc, modified desc",
}
PAGE_LENGTH_OPTIONS = (20, 50, 100)
DEFAULT_PAGE_LENGTH = 20
MAX_PAGE_LENGTH = 100
PREVIEW_LENGTH = 180


def _require_read_access() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not frappe.has_permission(QUESTION_DOCTYPE, "read"):
		frappe.throw(_("You are not permitted to view the Question Bank."), frappe.PermissionError)


def _option(value: str) -> dict[str, str]:
	return {"value": value, "label": _(value)}


def _branch_context() -> tuple[list[dict], list[dict]]:
	allowed = get_allowed_school_branches()
	allowed_names = [row.get("name") for row in allowed if row.get("name")]
	if not allowed_names:
		return [], []
	rows = frappe.get_all(
		"EduEdge School Branch",
		filters={"name": ["in", allowed_names], "enabled": 1},
		fields=["name", "branch_name", "company", "institution", "institution_type", "is_default"],
		order_by="is_default desc, branch_name asc",
	)
	institution_names = sorted({row.institution for row in rows if row.institution})
	institutions = []
	if institution_names:
		institution_rows = frappe.get_all(
			"EduEdge Institution",
			filters={"name": ["in", institution_names], "enabled": 1},
			fields=["name", "institution_name", "institution_type", "company", "is_default"],
			order_by="is_default desc, institution_name asc",
		)
		institutions = [
			{
				"value": row.name,
				"label": row.institution_name or row.name,
				"description": row.institution_type or "",
				"company": row.company or "",
			}
			for row in institution_rows
		]
	branches = [
		{
			"value": row.name,
			"label": row.branch_name or row.name,
			"description": row.company or "",
			"institution": row.institution or "",
			"institution_type": row.institution_type or "",
		}
		for row in rows
	]
	return branches, institutions


def _normalise_selection(value: str | None, allowed: set[str]) -> str:
	cleaned = str(value or "").strip()
	return cleaned if cleaned in allowed else ""


def _require_allowed_selection(value: str | None, allowed: set[str], label: str) -> str:
	cleaned = str(value or "").strip()
	if cleaned and cleaned not in allowed:
		frappe.throw(
			_("You are not permitted to use the selected {0}.").format(label),
			frappe.PermissionError,
		)
	return cleaned


def _effective_institution(institution: str, branch: str, branches: list[dict]) -> str:
	if institution:
		return institution
	if not branch:
		return ""
	return next((row.get("institution") or "" for row in branches if row.get("value") == branch), "")


def _course_scope_filters(
	*,
	ownership_scope: str,
	institution: str,
	branch: str,
	branches: list[dict],
) -> dict:
	meta = frappe.get_meta("Course")
	if not meta.has_field("eduedge_institution") or ownership_scope == PLATFORM_BANK:
		return {}
	effective_institution = _effective_institution(institution, branch, branches)
	if effective_institution:
		return {"eduedge_institution": effective_institution}
	permitted_institutions = sorted({row.get("institution") for row in branches if row.get("institution")})
	return {"eduedge_institution": ["in", permitted_institutions or [""]]}


def _resolve_course(
	course: str | None,
	*,
	ownership_scope: str,
	institution: str,
	branch: str,
	branches: list[dict],
) -> str:
	cleaned = str(course or "").strip()
	if not cleaned:
		return ""
	if not frappe.has_permission("Course", "read"):
		frappe.throw(_("You are not permitted to filter by Subject / Course."), frappe.PermissionError)
	filters = {"name": cleaned}
	filters.update(
		_course_scope_filters(
			ownership_scope=ownership_scope,
			institution=institution,
			branch=branch,
			branches=branches,
		)
	)
	rows = frappe.get_list("Course", filters=filters, fields=["name"], limit_page_length=1)
	if not rows:
		frappe.throw(
			_("The selected Subject / Course is not available in the permitted Question Bank context."),
			frappe.PermissionError,
		)
	return cleaned


def _normalise_page_length(value: int | str | None) -> int:
	requested = cint(value)
	return requested if requested in PAGE_LENGTH_OPTIONS else DEFAULT_PAGE_LENGTH


def _clamp_page_start(start: int | str | None, total: int, page_length: int) -> int:
	if total <= 0:
		return 0
	requested = max(0, cint(start))
	last_start = ((total - 1) // page_length) * page_length
	return min(requested, last_start)


def _question_preview(value: Any) -> str:
	plain = re.sub(r"\s+", " ", strip_html(str(value or ""))).strip()
	return plain if len(plain) <= PREVIEW_LENGTH else f"{plain[: PREVIEW_LENGTH - 1].rstrip()}…"


def _filters(
	*,
	ownership_scope: str,
	institution: str,
	branch: str,
	course: str,
	status: str,
	difficulty: str,
	question_type: str,
	exam_body: str,
	branches: list[dict],
	include_status: bool = True,
) -> dict:
	filters: dict[str, Any] = {"ownership_scope": ownership_scope}
	if ownership_scope == SCHOOL_BANK:
		branch_names = {row["value"] for row in branches}
		if branch:
			filters["school_branch"] = branch
		elif institution:
			institution_branches = sorted(row["value"] for row in branches if row.get("institution") == institution)
			filters["school_branch"] = ["in", institution_branches or [""]]
		else:
			filters["school_branch"] = ["in", sorted(branch_names) or [""]]
	if course:
		filters["course"] = course
	if include_status and status:
		filters["status"] = status
	if difficulty:
		filters["difficulty"] = difficulty
	if question_type:
		filters["question_type"] = question_type
	if exam_body:
		filters["exam_body"] = exam_body
	return filters


def _search_or_filters(search: str) -> list[list[str]]:
	if not search:
		return []
	pattern = f"%{search}%"
	return [
		["question_code", "like", pattern],
		["question_text", "like", pattern],
		["course", "like", pattern],
		["topic", "like", pattern],
		["curriculum", "like", pattern],
	]


def _status_counts(base_filters: dict, or_filters: list[list[str]]) -> dict:
	counts = {"Total": frappe.db.count(QUESTION_DOCTYPE, filters=base_filters, or_filters=or_filters or None)}
	for value in STATUSES:
		filters = dict(base_filters)
		filters["status"] = value
		counts[value] = frappe.db.count(QUESTION_DOCTYPE, filters=filters, or_filters=or_filters or None)
	return counts


def _label_maps(rows: list[dict], branches: list[dict], institutions: list[dict]) -> tuple[dict, dict, dict, dict]:
	courses = sorted({row.get("course") for row in rows if row.get("course")})
	topics = sorted({row.get("topic") for row in rows if row.get("topic")})
	course_map = {}
	topic_map = {}
	if courses:
		course_map = {
			row.name: row.course_name or row.name
			for row in frappe.get_all("Course", filters={"name": ["in", courses]}, fields=["name", "course_name"])
		}
	if topics:
		topic_map = {
			row.name: row.topic_name or row.name
			for row in frappe.get_all("Topic", filters={"name": ["in", topics]}, fields=["name", "topic_name"])
		}
	branch_map = {row["value"]: row for row in branches}
	institution_map = {row["value"]: row for row in institutions}
	return course_map, topic_map, branch_map, institution_map


@frappe.whitelist()
def get_question_bank(
	search: str | None = None,
	ownership_scope: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	course: str | None = None,
	status: str | None = None,
	difficulty: str | None = None,
	question_type: str | None = None,
	exam_body: str | None = None,
	sort_by: str | None = None,
	start: int = 0,
	page_length: int = DEFAULT_PAGE_LENGTH,
) -> dict:
	_require_read_access()
	branches, institutions = _branch_context()
	can_manage_public = bool(can_author_public_exams(frappe.session.user))
	scope_options = [_option(SCHOOL_BANK)]
	if can_manage_public:
		scope_options.append(_option(PLATFORM_BANK))
	allowed_scopes = {row["value"] for row in scope_options}
	requested_scope = _require_allowed_selection(ownership_scope, allowed_scopes, _("Question Bank"))
	resolved_scope = requested_scope or SCHOOL_BANK

	institution_values = {row["value"] for row in institutions}
	if resolved_scope == SCHOOL_BANK:
		resolved_institution = _require_allowed_selection(institution, institution_values, _("Institution"))
	else:
		resolved_institution = ""
	visible_branches = [row for row in branches if not resolved_institution or row.get("institution") == resolved_institution]
	branch_values = {row["value"] for row in visible_branches}
	if resolved_scope == SCHOOL_BANK:
		resolved_branch = _require_allowed_selection(branch, branch_values, _("Branch / Campus"))
	else:
		resolved_branch = ""

	resolved_status = _normalise_selection(status, set(STATUSES))
	resolved_difficulty = _normalise_selection(difficulty, set(DIFFICULTIES))
	resolved_type = _normalise_selection(question_type, set(QUESTION_TYPES))
	resolved_exam_body = _normalise_selection(exam_body, set(EXAM_BODIES))
	resolved_course = _resolve_course(
		course,
		ownership_scope=resolved_scope,
		institution=resolved_institution,
		branch=resolved_branch,
		branches=branches,
	)
	resolved_search = str(search or "").strip()[:120]
	resolved_sort = sort_by if sort_by in SORT_OPTIONS else "modified_desc"
	resolved_page_length = _normalise_page_length(page_length)

	base_filters = _filters(
		ownership_scope=resolved_scope,
		institution=resolved_institution,
		branch=resolved_branch,
		course=resolved_course,
		status="",
		difficulty=resolved_difficulty,
		question_type=resolved_type,
		exam_body=resolved_exam_body,
		branches=branches,
		include_status=False,
	)
	row_filters = dict(base_filters)
	if resolved_status:
		row_filters["status"] = resolved_status
	or_filters = _search_or_filters(resolved_search)
	counts = _status_counts(base_filters, or_filters)
	filtered_total = counts.get(resolved_status, 0) if resolved_status else counts["Total"]
	resolved_start = _clamp_page_start(start, filtered_total, resolved_page_length)

	rows = frappe.get_list(
		QUESTION_DOCTYPE,
		filters=row_filters,
		or_filters=or_filters or None,
		fields=[
			"name", "question_code", "ownership_scope", "school_branch", "course", "topic",
			"curriculum", "exam_body", "difficulty", "question_type", "question_text",
			"default_mark", "negative_mark", "version_number", "status", "modified", "owner",
		],
		order_by=SORT_OPTIONS[resolved_sort],
		limit_start=resolved_start,
		limit_page_length=resolved_page_length,
	)
	serialised = [dict(row) for row in rows]
	course_map, topic_map, branch_map, institution_map = _label_maps(serialised, branches, institutions)
	for row in serialised:
		row["question_preview"] = _question_preview(row.pop("question_text", ""))
		row["course_label"] = course_map.get(row.get("course"), row.get("course") or "")
		row["topic_label"] = topic_map.get(row.get("topic"), row.get("topic") or "")
		branch_row = branch_map.get(row.get("school_branch"), {})
		row["branch_label"] = branch_row.get("label") or ""
		row["institution"] = branch_row.get("institution") or ""
		row["institution_label"] = institution_map.get(row["institution"], {}).get("label") or ""

	current_branch = get_current_school_branch() or {}
	return {
		"rows": serialised,
		"counts": counts,
		"pagination": {
			"start": resolved_start,
			"page_length": resolved_page_length,
			"total": filtered_total,
			"has_previous": resolved_start > 0,
			"has_next": resolved_start + len(serialised) < filtered_total,
		},
		"filters": {
			"search": resolved_search,
			"ownership_scope": resolved_scope,
			"institution": resolved_institution,
			"branch": resolved_branch,
			"course": resolved_course,
			"status": resolved_status,
			"difficulty": resolved_difficulty,
			"question_type": resolved_type,
			"exam_body": resolved_exam_body,
			"sort_by": resolved_sort,
		},
		"options": {
			"ownership_scopes": scope_options,
			"institutions": institutions,
			"branches": visible_branches,
			"statuses": [_option(value) for value in STATUSES],
			"difficulties": [_option(value) for value in DIFFICULTIES],
			"question_types": [_option(value) for value in QUESTION_TYPES],
			"exam_bodies": [_option(value) for value in EXAM_BODIES],
			"page_lengths": [{"value": value, "label": str(value)} for value in PAGE_LENGTH_OPTIONS],
			"sort": [
				{"value": "modified_desc", "label": _("Recently Updated")},
				{"value": "modified_asc", "label": _("Oldest Updated")},
				{"value": "code_asc", "label": _("Question Code A–Z")},
				{"value": "code_desc", "label": _("Question Code Z–A")},
				{"value": "status_asc", "label": _("Status")},
			],
		},
		"permissions": {
			"can_create": bool(frappe.has_permission(QUESTION_DOCTYPE, "create")),
			"can_write": bool(frappe.has_permission(QUESTION_DOCTYPE, "write")),
			"can_import": bool(frappe.has_permission(QUESTION_DOCTYPE, "import")),
			"can_manage_public": can_manage_public,
		},
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
		"current_branch": current_branch,
		"tenant_name": current_branch.get("company") or "",
	}


@frappe.whitelist()
def search_courses(
	txt: str | None = None,
	institution: str | None = None,
	branch: str | None = None,
	ownership_scope: str | None = None,
	page_length: int = 20,
) -> list[dict]:
	_require_read_access()
	if not frappe.has_permission("Course", "read"):
		return []

	branches, institutions = _branch_context()
	can_manage_public = bool(can_author_public_exams(frappe.session.user))
	allowed_scopes = {SCHOOL_BANK}
	if can_manage_public:
		allowed_scopes.add(PLATFORM_BANK)
	resolved_scope = _require_allowed_selection(ownership_scope, allowed_scopes, _("Question Bank")) or SCHOOL_BANK

	resolved_institution = ""
	resolved_branch = ""
	if resolved_scope == SCHOOL_BANK:
		institution_values = {row["value"] for row in institutions}
		resolved_institution = _require_allowed_selection(institution, institution_values, _("Institution"))
		visible_branches = [row for row in branches if not resolved_institution or row.get("institution") == resolved_institution]
		resolved_branch = _require_allowed_selection(
			branch,
			{row["value"] for row in visible_branches},
			_("Branch / Campus"),
		)

	pattern = f"%{str(txt or '').strip()}%"
	filters = _course_scope_filters(
		ownership_scope=resolved_scope,
		institution=resolved_institution,
		branch=resolved_branch,
		branches=branches,
	)
	rows = frappe.get_list(
		"Course",
		filters=filters,
		or_filters=[["name", "like", pattern], ["course_name", "like", pattern]],
		fields=["name", "course_name"],
		order_by="course_name asc",
		limit_page_length=min(50, max(10, cint(page_length) or 20)),
	)
	return [{"value": row.name, "label": row.course_name or row.name} for row in rows]
