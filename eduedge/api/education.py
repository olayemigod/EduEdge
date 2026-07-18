from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def school_branch_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = frappe.parse_json(filters) or {}
	rows = get_allowed_school_branches(company=filters.get("company"))
	needle = (txt or "").strip().lower()
	if needle:
		rows = [
			row
			for row in rows
			if needle
			in " ".join(
				str(row.get(key) or "")
				for key in ("name", "branch_name", "branch_code", "company")
			).lower()
		]
	rows = rows[int(start) : int(start) + int(page_len)]
	return [
		[row["name"], row.get("branch_name"), row.get("branch_code"), row.get("company")]
		for row in rows
	]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def student_query(doctype, txt, searchfield, start, page_len, filters):
	_require_login()
	filters = frappe.parse_json(filters) or {}
	branch = filters.get(BRANCH_FIELD)
	allowed = {row["name"] for row in get_allowed_school_branches()}
	if branch and branch not in allowed:
		frappe.throw(_("You do not have access to the selected School Branch."), frappe.PermissionError)
	if not branch:
		current = get_current_school_branch()
		branch = current.get("name") if current else None

	student_filters: dict = {"enabled": 1}
	if branch:
		student_filters[BRANCH_FIELD] = branch
	rows = frappe.get_list(
		"Student",
		filters=student_filters,
		or_filters={
			"name": ["like", f"%{txt}%"],
			"student_name": ["like", f"%{txt}%"],
			"student_email_id": ["like", f"%{txt}%"],
		},
		fields=["name", "student_name", "student_email_id", BRANCH_FIELD],
		start=int(start),
		page_length=int(page_len),
		order_by="student_name asc",
	)
	return [
		[row["name"], row.get("student_name"), row.get("student_email_id"), row.get(BRANCH_FIELD)]
		for row in rows
	]


@frappe.whitelist()
def get_guardian_branch_summary(guardian: str) -> dict:
	_require_login()
	if not frappe.has_permission("Guardian", "read", guardian):
		frappe.throw(_("Not permitted to read this Guardian."), frappe.PermissionError)
	students = frappe.get_all(
		"Guardian Student",
		filters={"parent": guardian, "parenttype": "Guardian"},
		pluck="student",
	)
	if not students:
		return {"guardian": guardian, "branches": [], "students": []}
	rows = frappe.get_list(
		"Student",
		filters={"name": ["in", students]},
		fields=["name", "student_name", BRANCH_FIELD],
		order_by="student_name asc",
	)
	branches = sorted({row.get(BRANCH_FIELD) for row in rows if row.get(BRANCH_FIELD)})
	return {"guardian": guardian, "branches": branches, "students": rows}
