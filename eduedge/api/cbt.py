from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.cbt.public_access import (
	can_author_public_exams,
	get_public_exam_capability_summary,
	require_public_exam_authoring,
)
from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

SCHOOL_EXAM = "School Examination"
PUBLIC_EXAM = "EduEdge Public Examination"
SCHOOL_BANK = "School Question Bank"
PLATFORM_BANK = "EduEdge Examination Bank"
SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"
CBT_AUTHOR_ROLES = {
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Public Exam Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Teacher",
	"Instructor",
}
CBT_VIEW_ROLES = CBT_AUTHOR_ROLES | {
	"Academics User",
	"CBT Invigilator",
}


def _roles() -> set[str]:
	return set(frappe.get_roles(frappe.session.user))


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_viewer() -> set[str]:
	_require_login()
	roles = _roles()
	if frappe.session.user != "Administrator" and not roles.intersection(CBT_VIEW_ROLES):
		frappe.throw(_("You are not permitted to view CBT operations."), frappe.PermissionError)
	return roles


def _require_author() -> set[str]:
	_require_login()
	roles = _roles()
	if frappe.session.user != "Administrator" and not roles.intersection(CBT_AUTHOR_ROLES):
		frappe.throw(_("You are not permitted to configure CBT examinations."), frappe.PermissionError)
	return roles


def _school_branch_candidate(branch: str | None = None) -> str | None:
	return branch or (get_current_school_branch() or {}).get("name") or get_context_branch()


def _resolve_school_branch(branch: str | None = None) -> str:
	resolved = _school_branch_candidate(branch)
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus first."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved


def _parse_filters(filters) -> dict:
	if isinstance(filters, str):
		return frappe.parse_json(filters) or {}
	return filters or {}


@frappe.whitelist()
def get_public_exam_access_context() -> dict:
	"""Return server-authoritative capability flags for forms and CBT pages."""
	_require_login()
	return get_public_exam_capability_summary(frappe.session.user)


@frappe.whitelist()
def get_cbt_operations_context(
	exam_scope: str | None = None,
	branch: str | None = None,
) -> dict:
	roles = _require_viewer()
	public_access = get_public_exam_capability_summary(frappe.session.user)
	can_manage_public = bool(public_access["capabilities"]["author"]["allowed"])
	exam_scope = exam_scope or SCHOOL_EXAM
	if exam_scope not in {SCHOOL_EXAM, PUBLIC_EXAM}:
		frappe.throw(_("Select a valid Examination Scope."), frappe.ValidationError)

	resolved_branch = None
	if exam_scope == SCHOOL_EXAM:
		candidate = _school_branch_candidate(branch)
		if candidate:
			assert_branch_access(candidate)
			resolved_branch = candidate
	else:
		require_public_exam_authoring()

	can_author_questions = frappe.session.user == "Administrator" or bool(roles.intersection(CBT_AUTHOR_ROLES))
	centres = []
	templates = []
	questions = []

	# A school scope without a selected branch deliberately returns empty
	# operational collections so the page can render the branch selector without
	# falling back to cross-branch data.
	if exam_scope == PUBLIC_EXAM or resolved_branch:
		centre_filters = {
			"centre_type": SCHOOL_CENTRE if exam_scope == SCHOOL_EXAM else PLATFORM_CENTRE,
		}
		template_filters = {"exam_scope": exam_scope}
		question_filters = {
			"ownership_scope": SCHOOL_BANK if exam_scope == SCHOOL_EXAM else PLATFORM_BANK,
		}
		if resolved_branch:
			centre_filters["school_branch"] = resolved_branch
			template_filters["school_branch"] = resolved_branch
			question_filters["school_branch"] = resolved_branch

		centres = frappe.get_list(
			"EduEdge Examination Centre",
			filters=centre_filters,
			fields=[
				"name",
				"centre_name",
				"centre_code",
				"centre_type",
				"school_branch",
				"centre_status",
				"enabled",
				"allow_public_registration",
				"allow_paid_exams",
				"capacity",
				"public_hosting_status",
				"public_centre_reference",
				"location",
			],
			order_by="enabled desc, centre_name asc",
			page_length=200,
		)
		templates = frappe.get_list(
			"EduEdge CBT Exam Template",
			filters=template_filters,
			fields=[
				"name",
				"template_title",
				"template_code",
				"exam_scope",
				"school_branch",
				"course",
				"exam_body",
				"duration_minutes",
				"question_count",
				"total_marks",
				"status",
				"modified",
			],
			order_by="modified desc",
			page_length=200,
		)
		if can_author_questions:
			questions = frappe.get_list(
				"EduEdge CBT Question",
				filters=question_filters,
				fields=[
					"name",
					"question_code",
					"course",
					"topic",
					"question_type",
					"difficulty",
					"status",
					"modified",
				],
				order_by="modified desc",
				page_length=500,
			)

	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
		"allowed_branches": get_allowed_school_branches(),
		"filters": {
			"exam_scope": exam_scope,
			"branch": resolved_branch,
		},
		"public_exam_access": public_access,
		"can_manage_public": can_manage_public,
		"can_author_questions": can_author_questions,
		"can_manage_templates": frappe.session.user == "Administrator" or bool(roles.intersection(CBT_AUTHOR_ROLES)),
		"counts": {
			"centres": len(centres),
			"enabled_centres": sum(1 for row in centres if row.centre_status == "Active" or cint(row.enabled)),
			"public_host_centres": sum(1 for row in centres if row.public_hosting_status == "Approved"),
			"templates": len(templates),
			"approved_templates": sum(1 for row in templates if row.status == "Approved"),
			"draft_templates": sum(1 for row in templates if row.status in {"Draft", "Under Review"}),
			"approved_questions": sum(1 for row in questions if row.status == "Approved"),
			"draft_questions": sum(1 for row in questions if row.status in {"Draft", "Under Review"}),
		},
		"centres": centres[:12],
		"templates": templates[:12],
		"questions": questions[:12],
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def approved_question_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters,
):
	_require_author()
	filters = _parse_filters(filters)
	exam_scope = filters.get("exam_scope")
	course = filters.get("course")
	if exam_scope not in {SCHOOL_EXAM, PUBLIC_EXAM}:
		return []
	if not course:
		return []

	query_filters = {
		"status": "Approved",
		"course": course,
		"ownership_scope": SCHOOL_BANK if exam_scope == SCHOOL_EXAM else PLATFORM_BANK,
	}
	if exam_scope == SCHOOL_EXAM:
		branch = _resolve_school_branch(filters.get("school_branch"))
		query_filters["school_branch"] = branch
	else:
		require_public_exam_authoring()

	or_filters = []
	if txt:
		pattern = f"%{txt}%"
		or_filters = [
			["question_code", "like", pattern],
			["topic", "like", pattern],
			["question_text", "like", pattern],
		]
	rows = frappe.get_list(
		"EduEdge CBT Question",
		filters=query_filters,
		or_filters=or_filters or None,
		fields=["name", "question_code", "topic", "difficulty", "question_type"],
		order_by="question_code asc",
		start=cint(start),
		page_length=cint(page_len) or 20,
	)
	return [
		[
			row.name,
			row.topic or _("No topic"),
			row.question_type,
			row.difficulty,
		]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def examination_centre_link_query(
	doctype: str,
	txt: str,
	searchfield: str,
	start: int,
	page_len: int,
	filters,
):
	_require_author()
	filters = _parse_filters(filters)
	exam_scope = filters.get("exam_scope")
	if exam_scope not in {SCHOOL_EXAM, PUBLIC_EXAM}:
		return []

	query_filters = {
		"centre_status": "Active",
		"centre_type": SCHOOL_CENTRE if exam_scope == SCHOOL_EXAM else PLATFORM_CENTRE,
	}
	if exam_scope == SCHOOL_EXAM:
		branch = _resolve_school_branch(filters.get("school_branch"))
		query_filters["school_branch"] = branch
	else:
		require_public_exam_authoring()

	or_filters = []
	if txt:
		pattern = f"%{txt}%"
		or_filters = [
			["centre_name", "like", pattern],
			["centre_code", "like", pattern],
			["location", "like", pattern],
		]
	rows = frappe.get_list(
		"EduEdge Examination Centre",
		filters=query_filters,
		or_filters=or_filters or None,
		fields=["name", "centre_name", "centre_code", "location", "capacity"],
		order_by="centre_name asc",
		start=cint(start),
		page_length=cint(page_len) or 20,
	)
	return [
		[
			row.name,
			row.centre_name,
			row.location or _("No location"),
			_("Capacity: {0}").format(row.capacity or 0),
		]
		for row in rows
	]
