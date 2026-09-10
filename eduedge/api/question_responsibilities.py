from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.cbt.question_responsibilities import (
	RESPONSIBILITY_DOCTYPE,
	assert_responsibility_scope_access,
	assignment_is_active,
	permitted_responsibility_scope,
)
from eduedge.education.operations_policy import resolve_question_governance
from eduedge.platform.access import require_eduedge_access

MAX_OPTIONS = 50


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_permission(permission_type: str) -> None:
	_require_login()
	if not frappe.has_permission(RESPONSIBILITY_DOCTYPE, permission_type):
		frappe.throw(
			_("You are not permitted to {0} Question responsibility assignments.").format(permission_type),
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


def _branch_rows() -> list[dict]:
	scope = permitted_responsibility_scope()
	filters: dict[str, Any] = {"enabled": 1}
	if scope is not None:
		filters["name"] = ["in", sorted(scope["branches"]) or [""]]
	rows = frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		fields=["name", "branch_name", "institution", "company", "is_default"],
		order_by="is_default desc, branch_name asc",
	)
	return [dict(row) for row in rows]


def _institution_options(branches: list[dict] | None = None) -> list[dict]:
	branches = branches if branches is not None else _branch_rows()
	scope = permitted_responsibility_scope()
	institution_names = {row.get("institution") for row in branches if row.get("institution")}
	if scope is None and not institution_names:
		filters: dict[str, Any] = {"enabled": 1}
	else:
		filters = {"enabled": 1, "name": ["in", sorted(institution_names) or [""]]}
	rows = frappe.get_all(
		"EduEdge Institution",
		filters=filters,
		fields=["name", "institution_name", "institution_type", "company", "is_default"],
		order_by="is_default desc, institution_name asc",
	)
	return [
		{
			"value": row.name,
			"label": row.institution_name or row.name,
			"description": row.institution_type or "",
			"company": row.company or "",
		}
		for row in rows
	]


def _select_institution(requested: str | None, options: list[dict]) -> str:
	values = [row.get("value") for row in options if row.get("value")]
	if requested:
		if requested not in values:
			frappe.throw(_("Select a permitted Institution."), frappe.PermissionError)
		return requested
	return values[0] if values else ""


def _branches_for_institution(branches: list[dict], institution: str) -> list[dict]:
	return [
		{
			"value": row.get("name"),
			"label": row.get("branch_name") or row.get("name"),
			"description": row.get("company") or "",
		}
		for row in branches
		if row.get("institution") == institution
	]


def _status(row: dict) -> str:
	if not cint(row.get("enabled")):
		return "Disabled"
	today = getdate(nowdate())
	if row.get("valid_from") and getdate(row.get("valid_from")) > today:
		return "Scheduled"
	if row.get("valid_to") and getdate(row.get("valid_to")) < today:
		return "Expired"
	return "Active" if assignment_is_active(row) else "Inactive"


def _assignment_rows(institution: str, search: str | None = None) -> list[dict]:
	if not institution:
		return []
	filters: dict[str, Any] = {"institution": institution}
	query = str(search or "").strip()
	or_filters = None
	if query:
		pattern = f"%{query}%"
		or_filters = [
			["user", "like", pattern],
			["user_full_name", "like", pattern],
			["course", "like", pattern],
			["school_branch", "like", pattern],
		]
	rows = frappe.get_list(
		RESPONSIBILITY_DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"user",
			"user_full_name",
			"institution",
			"school_branch",
			"course",
			"can_author",
			"can_subject_review",
			"can_final_approve",
			"enabled",
			"valid_from",
			"valid_to",
			"notes",
			"modified",
		],
		order_by="enabled desc, user_full_name asc, course asc",
		limit_page_length=500,
	)
	serialised = [dict(row) for row in rows]
	branch_names = sorted({row.get("school_branch") for row in serialised if row.get("school_branch")})
	course_names = sorted({row.get("course") for row in serialised if row.get("course")})
	branch_map = {
		row.name: row.branch_name or row.name
		for row in frappe.get_all(
			"EduEdge School Branch",
			filters={"name": ["in", branch_names or [""]]},
			fields=["name", "branch_name"],
		)
	}
	course_map = {
		row.name: row.course_name or row.name
		for row in frappe.get_all(
			"Course",
			filters={"name": ["in", course_names or [""]]},
			fields=["name", "course_name"],
		)
	}
	for row in serialised:
		row["branch_label"] = branch_map.get(row.get("school_branch"), "All Institution Branches")
		row["course_label"] = course_map.get(row.get("course"), row.get("course") or "")
		row["status"] = _status(row)
	return serialised


def _counts(rows: list[dict]) -> dict:
	active = [row for row in rows if row.get("status") == "Active"]
	return {
		"total": len(rows),
		"active": len(active),
		"authors": sum(1 for row in active if cint(row.get("can_author"))),
		"subject_reviewers": sum(1 for row in active if cint(row.get("can_subject_review"))),
		"final_approvers": sum(1 for row in active if cint(row.get("can_final_approve"))),
	}


def _assignment_values(doc) -> dict:
	return {
		"user": doc.user or "",
		"institution": doc.institution or "",
		"school_branch": doc.school_branch or "",
		"course": doc.course or "",
		"can_author": cint(doc.can_author),
		"can_subject_review": cint(doc.can_subject_review),
		"can_final_approve": cint(doc.can_final_approve),
		"enabled": cint(doc.enabled),
		"valid_from": doc.valid_from,
		"valid_to": doc.valid_to,
		"notes": doc.notes or "",
	}


@frappe.whitelist()
def get_context(institution: str | None = None, search: str | None = None) -> dict:
	_require_permission("read")
	branches = _branch_rows()
	institution_options = _institution_options(branches)
	selected_institution = _select_institution(institution, institution_options)
	rows = _assignment_rows(selected_institution, search=search)
	return {
		"institution": selected_institution,
		"institution_options": institution_options,
		"branch_options": _branches_for_institution(branches, selected_institution),
		"assignments": rows,
		"counts": _counts(rows),
		"effective_policy": resolve_question_governance(selected_institution) if selected_institution else None,
		"permissions": {
			"can_create": bool(frappe.has_permission(RESPONSIBILITY_DOCTYPE, "create")),
			"can_write": bool(frappe.has_permission(RESPONSIBILITY_DOCTYPE, "write")),
			"can_delete": bool(frappe.has_permission(RESPONSIBILITY_DOCTYPE, "delete")),
		},
		"user": {
			"name": frappe.session.user,
			"full_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
		},
	}


@frappe.whitelist()
def get_assignment(name: str) -> dict:
	_require_permission("read")
	doc = frappe.get_doc(RESPONSIBILITY_DOCTYPE, name)
	doc.check_permission("read")
	assert_responsibility_scope_access(doc.institution, doc.school_branch)
	return {"name": doc.name, "values": _assignment_values(doc), "can_write": bool(doc.has_permission("write"))}


@frappe.whitelist()
def save_assignment(values: str | dict, name: str | None = None) -> dict:
	payload = _parse_json(values)
	if name:
		doc = frappe.get_doc(RESPONSIBILITY_DOCTYPE, name)
		doc.check_permission("write")
		action = "update_question_responsibility"
	else:
		_require_permission("create")
		doc = frappe.new_doc(RESPONSIBILITY_DOCTYPE)
		action = "create_question_responsibility"
	for fieldname in (
		"user",
		"institution",
		"school_branch",
		"course",
		"can_author",
		"can_subject_review",
		"can_final_approve",
		"enabled",
		"valid_from",
		"valid_to",
		"notes",
	):
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))
	assert_responsibility_scope_access(doc.institution, doc.school_branch)
	require_eduedge_access(
		feature_key="cbt",
		action=action,
		reference_doctype=RESPONSIBILITY_DOCTYPE,
		reference_name=name,
	)
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return {"name": doc.name, "values": _assignment_values(doc)}


@frappe.whitelist()
def set_enabled(name: str, enabled: int | str) -> dict:
	doc = frappe.get_doc(RESPONSIBILITY_DOCTYPE, name)
	doc.check_permission("write")
	assert_responsibility_scope_access(doc.institution, doc.school_branch)
	require_eduedge_access(
		feature_key="cbt",
		action="enable_question_responsibility" if cint(enabled) else "disable_question_responsibility",
		reference_doctype=RESPONSIBILITY_DOCTYPE,
		reference_name=doc.name,
	)
	doc.enabled = cint(enabled)
	doc.save()
	return {"name": doc.name, "enabled": cint(doc.enabled), "status": _status(_assignment_values(doc))}


@frappe.whitelist()
def search_options(fieldname: str, txt: str | None = None, values: str | dict | None = None) -> list[dict]:
	_require_permission("read")
	payload = _parse_json(values)
	query = str(txt or "").strip()
	branches = _branch_rows()
	institutions = _institution_options(branches)
	institution_values = {row["value"] for row in institutions}
	selected_institution = str(payload.get("institution") or "")
	if selected_institution and selected_institution not in institution_values:
		frappe.throw(_("Select a permitted Institution."), frappe.PermissionError)

	if fieldname == "institution":
		return _filter_options(institutions, query)
	if fieldname == "school_branch":
		return _filter_options(_branches_for_institution(branches, selected_institution), query)
	if fieldname == "user":
		pattern = f"%{query}%"
		rows = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			or_filters=[["name", "like", pattern], ["full_name", "like", pattern]],
			fields=["name", "full_name"],
			order_by="full_name asc",
			limit_page_length=MAX_OPTIONS,
		)
		return [
			{"value": row.name, "label": row.full_name or row.name, "description": row.name}
			for row in rows
		]
	if fieldname == "course":
		if not selected_institution:
			return []
		pattern = f"%{query}%"
		filters: dict[str, Any] = {}
		meta = frappe.get_meta("Course")
		if meta.has_field("eduedge_institution"):
			filters["eduedge_institution"] = selected_institution
		rows = frappe.get_list(
			"Course",
			filters=filters,
			or_filters=[["name", "like", pattern], ["course_name", "like", pattern]],
			fields=["name", "course_name"],
			order_by="course_name asc",
			limit_page_length=MAX_OPTIONS,
		)
		return [{"value": row.name, "label": row.course_name or row.name} for row in rows]
	frappe.throw(_("This field does not support option search."), frappe.ValidationError)


def _filter_options(options: list[dict], query: str) -> list[dict]:
	if not query:
		return options[:MAX_OPTIONS]
	needle = query.lower()
	return [
		row
		for row in options
		if needle in str(row.get("value") or "").lower()
		or needle in str(row.get("label") or "").lower()
		or needle in str(row.get("description") or "").lower()
	][:MAX_OPTIONS]
