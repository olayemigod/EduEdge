from __future__ import annotations

import frappe

from eduedge.education.academic_fields import INSTITUTION_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, is_branch_access_enforced

PRIVILEGED_ROLES = {"System Manager", "EduEdge Administrator"}


def academic_section_query(user: str | None = None) -> str:
	return _institution_query("EduEdge Academic Section", "institution", user)


def academic_level_query(user: str | None = None) -> str:
	return _institution_query("EduEdge Academic Level", "institution", user)


def program_query(user: str | None = None) -> str:
	return _institution_query("Program", INSTITUTION_FIELD, user)


def course_query(user: str | None = None) -> str:
	return _institution_query("Course", INSTITUTION_FIELD, user)


def has_academic_institution_permission(doc, user=None, permission_type=None) -> bool | None:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user) or not doc:
		return None
	fieldname = "institution" if doc.doctype in {"EduEdge Academic Section", "EduEdge Academic Level"} else INSTITUTION_FIELD
	if not frappe.get_meta(doc.doctype).has_field(fieldname):
		return None
	institution = doc.get(fieldname)
	if not institution:
		return None
	return None if institution in _allowed_institutions(resolved_user) else False


def _institution_query(doctype: str, fieldname: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _should_scope(resolved_user):
		return ""
	if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(fieldname):
		return ""
	institutions = _allowed_institutions(resolved_user)
	if not institutions:
		return "1=0"
	values = ", ".join(frappe.db.escape(value) for value in sorted(institutions))
	return f"(`tab{doctype}`.`{fieldname}` in ({values}) or coalesce(`tab{doctype}`.`{fieldname}`, '') = '')"


def _allowed_institutions(user: str) -> set[str]:
	return {
		row.get("institution")
		for row in get_allowed_school_branches(user=user)
		if row.get("institution")
	}


def _should_scope(user: str) -> bool:
	if not is_branch_access_enforced() or not user or user in {"Guest", "Administrator"}:
		return False
	return not bool(set(frappe.get_roles(user)).intersection(PRIVILEGED_ROLES))
