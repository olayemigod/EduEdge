from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from eduedge.access_control import build_access_manifest
from eduedge.cbt.public_access import (
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
CBT_RESOURCES = ("examination_centre", "cbt_question", "cbt_template")


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _access_manifest() -> dict:
	_require_login()
	return build_access_manifest(frappe.session.user)


def _resource_allowed(manifest: dict, resource: str, *permission_types: str) -> bool:
	permissions = manifest.get("resources", {}).get(resource, {})
	return any(bool(permissions.get(permission_type)) for permission_type in permission_types)


def _require_viewer() -> dict:
	manifest = _access_manifest()
	if not any(_resource_allowed(manifest, resource, "read") for resource in CBT_RESOURCES):
		frappe.throw(_("You are not permitted to view CBT operations."), frappe.PermissionError)
	return manifest


def _require_resource(manifest: dict, resource: str, *permission_types: str) -> None:
	if not _resource_allowed(manifest, resource, *permission_types):
		frappe.throw(_("You do not have the required CBT permission for this action."), frappe.PermissionError)


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


def _public_permissions(resources: dict) -> dict:
	return {
		resource: {
			permission_type: bool(value)
			for permission_type, value in resources.get(resource, {}).items()
		}
		for resource in CBT_RESOURCES
	}


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
	manifest = _require_viewer()
	resource_permissions = manifest.get("resources", {})
	permissions = _public_permissions(resource_permissions)
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

	all_centres = []
	centres = []
	templates = []
	questions = []

	# A school scope without a selected branch deliberately returns empty
	# collections so the page can render the branch selector safely.
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

		if permissions["examination_centre"].get("read"):
			all_centres = frappe.get_list(
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
			centres = [
				row for row in all_centres if row.centre_status == "Active" or cint(row.enabled)
			]

		if permissions["cbt_template"].get("read"):
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

		if permissions["cbt_question"].get("read"):
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
	can_author_questions = bool(
		permissions["cbt_question"].get("create") or permissions["cbt_question"].get("write")
	)
	can_manage_templates = bool(
		permissions["cbt_template"].get("create") or permissions["cbt_template"].get("write")
	)
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
		"permissions": permissions,
		"can_manage_public": can_manage_public,
		# Retained for compatibility while existing pages move to granular rights.
		"can_author_questions": can_author_questions,
		"can_manage_templates": can_manage_templates,
		"can_manage_centres": bool(
			permissions["examination_centre"].get("create")
			or permissions["examination_centre"].get("write")
		),
		"counts": {
			"centres": len(all_centres),
			"enabled_centres": len(centres),
			"non_active_centres": len(all_centres) - len(centres),
			"public_host_centres": sum(1 for row in all_centres if row.public_hosting_status == "Approved"),
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
	manifest = _access_manifest()
	_require_resource(manifest, "cbt_template", "create", "write")
	_require_resource(manifest, "cbt_question", "read")
	filters = _parse_filters(filters)
	exam_scope = filters.get("exam_scope")
	course = filters.get("course")
	if exam_scope not in {SCHOOL_EXAM, PUBLIC_EXAM} or not course:
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
		[row.name, row.topic or _("No topic"), row.question_type, row.difficulty]
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
	manifest = _access_manifest()
	_require_resource(manifest, "cbt_template", "create", "write")
	_require_resource(manifest, "examination_centre", "read")
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
