from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import nowdate

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import (
	get_allowed_school_branches,
	get_current_school_branch,
)
from eduedge.services.setup_readiness import get_setup_readiness


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _count_for_branch(doctype: str, branch: str | None, extra_filters: dict | None = None) -> int:
	if not branch or not frappe.db.exists("DocType", doctype):
		return 0
	meta = frappe.get_meta(doctype)
	if not meta.has_field(BRANCH_FIELD):
		return 0
	filters = {BRANCH_FIELD: branch, **(extra_filters or {})}
	return frappe.db.count(doctype, filters)


@frappe.whitelist()
def get_home_context() -> dict:
	"""Return permission-safe context for the EdgeSuite UI EduEdge home page."""
	_require_login()

	allowed_branches = get_allowed_school_branches()
	current_branch = get_current_school_branch()
	branch_name = current_branch.get("name") if current_branch else None
	readiness = get_setup_readiness()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

	return {
		"product": "EduEdge",
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company")
			or readiness.get("school", {}).get("default_company"),
		"current_branch": current_branch,
		"allowed_branches": allowed_branches,
		"requires_branch_selection": bool(allowed_branches and not current_branch),
		"readiness": {
			"ready": bool(readiness.get("ready")),
			"blocker_count": len(readiness.get("blockers") or []),
			"warning_count": len(readiness.get("warnings") or []),
		},
		"counts": {
			"students": _count_for_branch("Student", branch_name, {"enabled": 1}),
			"applicants": _count_for_branch(
				"Student Applicant",
				branch_name,
				{"application_status": ["in", ["Applied", "Approved"]]},
			),
			"admissions": _count_for_branch(
				"Student Admission",
				branch_name,
				{"published": 1},
			),
			"program_offerings": _count_for_branch(
				"EduEdge Program Offering",
				branch_name,
				{"is_active": 1},
			),
			"student_groups": _count_for_branch(
				"Student Group",
				branch_name,
				{"disabled": 0},
			),
			"today_schedules": _count_for_branch(
				"Course Schedule",
				branch_name,
				{"schedule_date": nowdate()},
			),
		},
	}
