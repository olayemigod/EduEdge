from __future__ import annotations

import frappe

from eduedge.api import assessment_operations as base
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

MAX_CONTEXT_ROWS = 200


def _term_compatible(group_term: str | None, selected_term: str | None) -> bool:
	"""A session-wide Class Arm is valid in every Term of its Academic Session.

	Grandfathered term-bound Student Groups remain valid only in their exact historical
	Term. New sessional Student Groups intentionally have no academic_term value.
	"""
	return not selected_term or not group_term or str(group_term) == str(selected_term)


def _student_groups(branch: str, academic_year: str | None, academic_term: str | None) -> list[dict]:
	filters: dict = {BRANCH_FIELD: branch, "disabled": 0}
	if academic_year:
		filters["academic_year"] = academic_year
	rows = frappe.get_list(
		"Student Group",
		filters=filters,
		fields=["name", "student_group_name", "program", "course", "academic_year", "academic_term"],
		order_by="student_group_name asc",
		page_length=MAX_CONTEXT_ROWS,
	)
	return [dict(row) for row in rows if _term_compatible(row.academic_term, academic_term)]


@frappe.whitelist()
def get_assessment_context(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	assessment_group: str | None = None,
) -> dict:
	"""Assessment Operations context for sessional Class Arms and term-scoped work.

	The Student Group/Class Arm is session-wide. Assessment Plans, result publication
	and report-card readiness remain scoped to the selected Term/Semester.
	"""
	base._require_operator()
	resolved_branch = base._resolve_branch(branch)
	default_year, default_term = base._current_academic_defaults()
	academic_year = academic_year or default_year
	academic_term = academic_term if academic_term is not None else default_term

	groups = _student_groups(resolved_branch, academic_year, academic_term)
	group_names = {row["name"] for row in groups}
	if student_group and student_group not in group_names:
		frappe.throw(
			frappe._("Selected Student Group / Class Arm is not available in this Branch, Academic Session and Term."),
			frappe.PermissionError,
		)

	assessment_groups = frappe.get_list(
		"Assessment Group",
		filters={"is_group": 0},
		fields=["name", "assessment_group_name"],
		order_by="assessment_group_name asc",
		page_length=MAX_CONTEXT_ROWS,
	)

	plan_filters: dict = {BRANCH_FIELD: resolved_branch}
	if academic_year:
		plan_filters["academic_year"] = academic_year
	if academic_term:
		plan_filters["academic_term"] = academic_term
	if student_group:
		plan_filters["student_group"] = student_group
	if assessment_group:
		plan_filters["assessment_group"] = assessment_group
	plans = frappe.get_list(
		"Assessment Plan",
		filters=plan_filters,
		fields=[
			"name",
			"assessment_name",
			"student_group",
			"assessment_group",
			"course",
			"schedule_date",
			"from_time",
			"to_time",
			"room",
			"examiner_name",
			"maximum_assessment_score",
			"docstatus",
		],
		order_by="schedule_date desc, assessment_name asc",
		page_length=MAX_CONTEXT_ROWS,
	)

	publication = None
	readiness = None
	if student_group and assessment_group and academic_year:
		publication = frappe.db.get_value(
			base.PUBLICATION_DOCTYPE,
			{
				"school_branch": resolved_branch,
				"student_group": student_group,
				"academic_year": academic_year,
				"academic_term": academic_term or "",
				"assessment_group": assessment_group,
			},
			[
				"name",
				"title",
				"status",
				"expected_results",
				"submitted_results",
				"draft_results",
				"missing_results",
				"report_card_ready",
				"requested_by",
				"requested_on",
				"approved_by",
				"approved_on",
				"published_by",
				"published_on",
				"rejection_reason",
			],
			as_dict=True,
		)
		readiness = base.get_publication_readiness(
			school_branch=resolved_branch,
			student_group=student_group,
			academic_year=academic_year,
			academic_term=academic_term,
			assessment_group=assessment_group,
		)

	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
		"allowed_branches": get_allowed_school_branches(),
		"can_approve": bool(base.APPROVER_ROLES.intersection(frappe.get_roles(frappe.session.user))),
		"filters": {
			"branch": resolved_branch,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"student_group": student_group,
			"assessment_group": assessment_group,
		},
		"counts": {
			"plans": len(plans),
			"submitted_plans": sum(1 for row in plans if row.docstatus == 1),
			"draft_plans": sum(1 for row in plans if row.docstatus == 0),
			"expected_results": (readiness or {}).get("expected_results", 0),
			"submitted_results": (readiness or {}).get("submitted_results", 0),
			"missing_results": (readiness or {}).get("missing_results", 0),
		},
		"student_groups": groups,
		"assessment_groups": assessment_groups,
		"plans": plans,
		"publication": publication,
		"readiness": readiness,
	}
