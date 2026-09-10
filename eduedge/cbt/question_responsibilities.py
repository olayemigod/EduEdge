from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from eduedge.services.branch_context import get_allowed_school_branches

RESPONSIBILITY_DOCTYPE = "EduEdge Question Responsibility Assignment"
RESPONSIBILITY_FIELDS = {
	"author": "can_author",
	"subject_review": "can_subject_review",
	"final_approve": "can_final_approve",
}
GLOBAL_SCOPE_ROLES = {
	"Administrator",
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
}


def _user_roles(user: str) -> set[str]:
	return set(frappe.get_roles(user)) | ({user} if user else set())


def has_global_responsibility_scope(user: str | None = None) -> bool:
	resolved_user = user or frappe.session.user
	return bool(GLOBAL_SCOPE_ROLES.intersection(_user_roles(resolved_user)))


def permitted_responsibility_scope(user: str | None = None) -> dict[str, set[str]] | None:
	resolved_user = user or frappe.session.user
	if has_global_responsibility_scope(resolved_user):
		return None
	rows = get_allowed_school_branches(user=resolved_user)
	return {
		"branches": {row.get("name") for row in rows if row.get("name")},
		"institutions": {row.get("institution") for row in rows if row.get("institution")},
		"companies": {row.get("company") for row in rows if row.get("company")},
	}


def assert_responsibility_scope_access(
	institution: str,
	school_branch: str | None = None,
	*,
	user: str | None = None,
) -> None:
	resolved_user = user or frappe.session.user
	scope = permitted_responsibility_scope(resolved_user)
	if scope is None:
		return
	if not institution or institution not in scope["institutions"]:
		frappe.throw(
			_("You are not permitted to manage question responsibilities for this Institution."),
			frappe.PermissionError,
		)
	if school_branch and school_branch not in scope["branches"]:
		frappe.throw(
			_("You are not permitted to manage question responsibilities for this Branch / Campus."),
			frappe.PermissionError,
		)


def assignment_is_active(row: Any, on_date=None) -> bool:
	if not cint(_value(row, "enabled")):
		return False
	resolved_date = getdate(on_date or nowdate())
	valid_from = _value(row, "valid_from")
	valid_to = _value(row, "valid_to")
	if valid_from and getdate(valid_from) > resolved_date:
		return False
	if valid_to and getdate(valid_to) < resolved_date:
		return False
	return True


def get_matching_question_responsibilities(
	*,
	user: str,
	institution: str,
	course: str,
	school_branch: str | None = None,
	on_date=None,
) -> list[dict]:
	if not user or not institution or not course:
		return []
	if not frappe.db.exists("DocType", RESPONSIBILITY_DOCTYPE):
		return []
	rows = frappe.get_all(
		RESPONSIBILITY_DOCTYPE,
		filters={
			"user": user,
			"institution": institution,
			"course": course,
			"enabled": 1,
		},
		fields=[
			"name",
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
		],
		order_by="school_branch desc, modified desc",
	)
	matched = []
	for row in rows:
		if not assignment_is_active(row, on_date=on_date):
			continue
		assignment_branch = row.get("school_branch") or ""
		if assignment_branch and assignment_branch != (school_branch or ""):
			continue
		matched.append(dict(row))
	return matched


def get_question_responsibility_state(
	*,
	user: str,
	institution: str,
	course: str,
	school_branch: str | None = None,
	on_date=None,
) -> dict:
	rows = get_matching_question_responsibilities(
		user=user,
		institution=institution,
		course=course,
		school_branch=school_branch,
		on_date=on_date,
	)
	state = {
		"user": user,
		"institution": institution,
		"school_branch": school_branch or "",
		"course": course,
		"can_author": False,
		"can_subject_review": False,
		"can_final_approve": False,
		"assignment_names": [],
	}
	for row in rows:
		state["assignment_names"].append(row.get("name"))
		for fieldname in RESPONSIBILITY_FIELDS.values():
			state[fieldname] = bool(state[fieldname] or cint(row.get(fieldname)))
	return state


def user_has_question_responsibility(
	responsibility: str,
	*,
	user: str,
	institution: str,
	course: str,
	school_branch: str | None = None,
	on_date=None,
) -> bool:
	fieldname = RESPONSIBILITY_FIELDS.get(responsibility)
	if not fieldname:
		return False
	state = get_question_responsibility_state(
		user=user,
		institution=institution,
		course=course,
		school_branch=school_branch,
		on_date=on_date,
	)
	return bool(state.get(fieldname))


def _value(row: Any, fieldname: str, default=None):
	if hasattr(row, "get"):
		value = row.get(fieldname)
	else:
		value = getattr(row, fieldname, None)
	return default if value is None else value
