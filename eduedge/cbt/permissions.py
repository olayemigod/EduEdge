from __future__ import annotations

import frappe

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import can_assign_public_exams, can_author_public_exams
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	is_branch_access_enforced,
)

CBT_DOCTYPES = (
	"EduEdge Examination Centre",
	"EduEdge CBT Question",
	"EduEdge CBT Exam Template",
	"EduEdge CBT Exam Schedule",
	"EduEdge CBT Candidate Assignment",
	"EduEdge CBT Intervention Log",
	"EduEdge CBT Lifecycle Log",
)

PUBLIC_ASSIGNMENT_DOCTYPES = {
	"EduEdge CBT Candidate Assignment",
	"EduEdge CBT Intervention Log",
	"EduEdge CBT Lifecycle Log",
}

SCHOOL_EXAM = "School Examination"
REUSE_UNIVERSAL = "Universal"
REUSE_INSTITUTION = "Institution-wide"
REUSE_BRANCH = "Branch-wide"


def examination_centre_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge Examination Centre", user)


def cbt_question_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Question", user)


def cbt_exam_template_query(user: str | None = None) -> str:
	return _exam_template_condition(user)


def cbt_exam_schedule_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Exam Schedule", user)


def cbt_candidate_assignment_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Candidate Assignment", user)


def cbt_intervention_log_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Intervention Log", user)


def cbt_lifecycle_log_query(user: str | None = None) -> str:
	return _school_branch_condition("EduEdge CBT Lifecycle Log", user)


def has_school_branch_permission(doc, user=None, permission_type=None) -> bool:
	"""Allow role permissions unless exact public capability or branch isolation denies the record."""
	resolved_user = user or frappe.session.user
	if not _is_cbt_operational_user(resolved_user):
		return True
	if doc and doc.doctype == "EduEdge CBT Exam Template":
		return _has_exam_template_scope_permission(doc, resolved_user)

	branch = doc.get("school_branch") if doc else None
	if not branch:
		return _has_public_record_access(doc.doctype if doc else None, resolved_user)
	if not is_branch_access_enforced():
		return True

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return True
	return branch in allowed


def _has_exam_template_scope_permission(doc, user: str) -> bool:
	if doc.get("exam_scope") != SCHOOL_EXAM:
		return _has_public_record_access(doc.doctype, user)
	if not is_branch_access_enforced():
		return True
	rows = _allowed_branch_rows(user)
	if rows is None:
		return True
	scope = doc.get("template_reuse_scope") or REUSE_BRANCH
	if scope == REUSE_UNIVERSAL:
		return doc.get("company") in {row.get("company") for row in rows}
	if scope == REUSE_INSTITUTION:
		return doc.get("institution") in {row.get("institution") for row in rows}
	return doc.get("school_branch") in {row.get("name") for row in rows}


def _school_branch_condition(doctype: str, user: str | None) -> str:
	resolved_user = user or frappe.session.user
	if not _is_cbt_operational_user(resolved_user):
		return ""

	public_allowed = _has_public_record_access(doctype, resolved_user)
	branch_column = f"`tab{doctype}`.`school_branch`"
	if not is_branch_access_enforced():
		return "" if public_allowed else f"{branch_column} is not null"

	allowed = _allowed_branch_names(resolved_user)
	if allowed is None:
		return "" if public_allowed else f"{branch_column} is not null"

	conditions: list[str] = []
	if allowed:
		values = ", ".join(frappe.db.escape(value) for value in sorted(allowed))
		conditions.append(f"{branch_column} in ({values})")
	if public_allowed:
		conditions.append(f"{branch_column} is null")
	if not conditions:
		return "1=0"
	return "(" + " OR ".join(conditions) + ")"


def _exam_template_condition(user: str | None) -> str:
	resolved_user = user or frappe.session.user
	doctype = "EduEdge CBT Exam Template"
	if not _is_cbt_operational_user(resolved_user):
		return ""

	public_allowed = _has_public_record_access(doctype, resolved_user)
	public_condition = (
		f"`tab{doctype}`.`exam_scope` != {frappe.db.escape(SCHOOL_EXAM)}"
		if public_allowed
		else ""
	)
	if not is_branch_access_enforced():
		return "" if public_allowed else f"`tab{doctype}`.`exam_scope` = {frappe.db.escape(SCHOOL_EXAM)}"

	rows = _allowed_branch_rows(resolved_user)
	if rows is None:
		return "" if public_allowed else f"`tab{doctype}`.`exam_scope` = {frappe.db.escape(SCHOOL_EXAM)}"

	branches = sorted({row.get("name") for row in rows if row.get("name")})
	institutions = sorted({row.get("institution") for row in rows if row.get("institution")})
	companies = sorted({row.get("company") for row in rows if row.get("company")})
	branch_values = ", ".join(frappe.db.escape(value) for value in branches) or "''"
	institution_values = ", ".join(frappe.db.escape(value) for value in institutions) or "''"
	company_values = ", ".join(frappe.db.escape(value) for value in companies) or "''"
	school_condition = (
		f"`tab{doctype}`.`exam_scope` = {frappe.db.escape(SCHOOL_EXAM)} AND ("
		f"(`tab{doctype}`.`template_reuse_scope` = {frappe.db.escape(REUSE_UNIVERSAL)} "
		f"AND `tab{doctype}`.`company` in ({company_values})) OR "
		f"(`tab{doctype}`.`template_reuse_scope` = {frappe.db.escape(REUSE_INSTITUTION)} "
		f"AND `tab{doctype}`.`institution` in ({institution_values})) OR "
		f"((`tab{doctype}`.`template_reuse_scope` = {frappe.db.escape(REUSE_BRANCH)} "
		f"OR `tab{doctype}`.`template_reuse_scope` is null OR `tab{doctype}`.`template_reuse_scope` = '') "
		f"AND `tab{doctype}`.`school_branch` in ({branch_values}))"
		")"
	)
	if public_condition:
		return f"({school_condition}) OR ({public_condition})"
	return school_condition


def _has_public_record_access(doctype: str | None, user: str) -> bool:
	if doctype in PUBLIC_ASSIGNMENT_DOCTYPES:
		return can_assign_public_exams(user)
	return can_author_public_exams(user)


def _allowed_branch_rows(user: str) -> list[dict] | None:
	if not frappe.db.count("EduEdge School Branch", {"enabled": 1}):
		return None
	return [dict(row) for row in get_allowed_school_branches(user=user)]


def _allowed_branch_names(user: str) -> set[str] | None:
	rows = _allowed_branch_rows(user)
	if rows is None:
		return None
	return {row.get("name") for row in rows if row.get("name")}


def _is_cbt_operational_user(user: str) -> bool:
	if not user or user == "Guest":
		return False
	return any(
		user_has_role_permission(doctype, permission_type, user)
		for doctype in CBT_DOCTYPES
		for permission_type in ("read", "create", "write", "report")
	)
