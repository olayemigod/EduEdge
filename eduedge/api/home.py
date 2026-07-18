from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import nowdate

from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_active_branch_context
from eduedge.services.setup_readiness import get_setup_readiness


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _count_for_branches(
	doctype: str,
	branches: list[str],
	extra_filters: dict | None = None,
	*,
	fieldname: str | None = None,
) -> int:
	if not branches or not frappe.db.exists("DocType", doctype):
		return 0
	meta = frappe.get_meta(doctype)
	resolved_fieldname = fieldname
	if not resolved_fieldname:
		if meta.has_field(BRANCH_FIELD):
			resolved_fieldname = BRANCH_FIELD
		elif meta.has_field("school_branch"):
			resolved_fieldname = "school_branch"
	if not resolved_fieldname or not meta.has_field(resolved_fieldname):
		return 0
	branch_filter: str | list = branches[0] if len(branches) == 1 else ["in", branches]
	filters = {resolved_fieldname: branch_filter, **(extra_filters or {})}
	return frappe.db.count(doctype, filters)


@frappe.whitelist()
def get_home_context() -> dict:
	"""Return permission-safe context for the EdgeSuite UI EduEdge home page."""
	_require_login()

	branch_context = get_active_branch_context()
	allowed_branches = branch_context["allowed_branches"]
	current_branch = branch_context.get("current_branch")
	active_company = branch_context.get("active_company")
	if branch_context["active_scope"] == "all":
		branch_names = [
			row["name"]
			for row in allowed_branches
			if not active_company or row.get("company") == active_company
		]
	else:
		branch_names = [current_branch["name"]] if current_branch and current_branch.get("name") else []

	readiness = get_setup_readiness()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	all_branch_options = [
		{
			"value": f'{branch_context["all_branches_key"]}::{company}',
			"company": company,
			"label": _("All Branches · {0}").format(company),
		}
		for company in branch_context.get("all_branch_companies") or []
	]

	return {
		"product": "EduEdge",
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": active_company or readiness.get("school", {}).get("default_company"),
		"current_branch": current_branch,
		"allowed_branches": allowed_branches,
		"active_scope": branch_context["active_scope"],
		"active_company": active_company,
		"active_label": branch_context["active_label"],
		"all_branches_key": branch_context["all_branches_key"],
		"all_branch_options": all_branch_options,
		"can_switch_branch": branch_context["can_switch_branch"],
		"can_view_all_branches": branch_context["can_view_all_branches"],
		"branch_access_enforced": branch_context["enforcement_enabled"],
		"can_manage_branch_access": bool({"System Manager", "EduEdge Administrator"}.intersection(frappe.get_roles(frappe.session.user))),
		"requires_branch_selection": bool(
			branch_context["active_scope"] == "branch"
			and allowed_branches
			and not (current_branch or {}).get("name")
		),
		"readiness": {
			"ready": bool(readiness.get("ready")),
			"blocker_count": len(readiness.get("blockers") or []),
			"warning_count": len(readiness.get("warnings") or []),
		},
		"counts": {
			"students": _count_for_branches("Student", branch_names, {"enabled": 1}),
			"applicants": _count_for_branches(
				"Student Applicant",
				branch_names,
				{"application_status": ["in", ["Applied", "Approved"]]},
			),
			"admissions": _count_for_branches(
				"Student Admission", branch_names, {"published": 1}
			),
			"program_offerings": _count_for_branches(
				"EduEdge Program Offering", branch_names, {"is_active": 1}
			),
			"student_groups": _count_for_branches(
				"Student Group", branch_names, {"disabled": 0}
			),
			"today_schedules": _count_for_branches(
				"Course Schedule", branch_names, {"schedule_date": nowdate()}
			),
			"assessment_plans": _count_for_branches(
				"Assessment Plan", branch_names, {"docstatus": ["!=", 2]}
			),
			"pending_result_approvals": _count_for_branches(
				"EduEdge Result Publication", branch_names, {"status": "Pending Approval"}
			),
			"pending_progression_reviews": _count_for_branches(
				"EduEdge Report Card Review", branch_names, {"progression_status": "Recommended"}
			),
		},
	}
