from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.education.assessment_operations import (
	PUBLICATION_DOCTYPE,
	append_publication_log,
	get_publication_readiness,
)
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.education.result_snapshots import create_publication_snapshots
from eduedge.education.result_profile import (
	freeze_publication_result_profile_config,
	get_publication_result_profile_config,
	get_result_profile_config,
	set_publication_result_profile_config,
)
from eduedge.platform.access import guard_eduedge_action
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch

ASSESSMENT_OPERATOR_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
	"Instructor",
	"Teacher",
}
APPROVER_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_operator() -> None:
	_require_login()
	if not ASSESSMENT_OPERATOR_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to manage assessments."), frappe.PermissionError)


def _require_approver() -> None:
	_require_login()
	if not APPROVER_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to approve or publish results."), frappe.PermissionError)


def _resolve_branch(branch: str | None = None) -> str:
	resolved = branch or (get_current_school_branch() or {}).get("name") or get_context_branch()
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus first."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved



def _publication_scope_filters(
	*,
	school_branch: str,
	student_group: str,
	academic_year: str,
	academic_term: str | None,
	assessment_group: str | None,
	result_profile: str | None,
	result_mode: str,
) -> dict:
	filters = {
		"school_branch": school_branch,
		"student_group": student_group,
		"academic_year": academic_year,
		"academic_term": academic_term if academic_term else ["is", "not set"],
		"result_mode": result_mode or "Terminal",
	}
	if result_profile:
		filters["result_profile"] = result_profile
		filters["assessment_group"] = ["is", "not set"]
	else:
		filters["result_profile"] = ["is", "not set"]
		filters["assessment_group"] = assessment_group
	return filters


def _current_academic_defaults() -> tuple[str | None, str | None]:
	return (
		frappe.db.get_single_value("Education Settings", "current_academic_year"),
		frappe.db.get_single_value("Education Settings", "current_academic_term"),
	)


@frappe.whitelist()
def get_assessment_context(
	branch: str | None = None,
	academic_year: str | None = None,
	academic_term: str | None = None,
	student_group: str | None = None,
	assessment_group: str | None = None,
	result_profile: str | None = None,
	result_mode: str | None = None,
) -> dict:
	_require_operator()
	resolved_branch = _resolve_branch(branch)
	default_year, default_term = _current_academic_defaults()
	academic_year = academic_year or default_year
	result_mode = result_mode or "Terminal"
	if result_mode not in {"Terminal", "Annual"}:
		frappe.throw(_("Invalid Result Mode."), frappe.ValidationError)
	academic_term = None if result_mode == "Annual" else (academic_term if academic_term is not None else default_term)

	institution = frappe.db.get_value("EduEdge School Branch", resolved_branch, "institution")
	result_profiles = frappe.get_list(
		"EduEdge Result Profile",
		filters={"institution": institution, "is_active": 1},
		fields=["name", "profile_name", "school_branch", "is_default", "annual_aggregation_method"],
		order_by="is_default desc, profile_name asc",
		page_length=200,
	)
	result_profiles = [
		row for row in result_profiles
		if not row.school_branch or row.school_branch == resolved_branch
	]
	if result_profile and result_profile not in {row.name for row in result_profiles}:
		frappe.throw(_("Selected Result Profile is not available for this Branch / Institution."), frappe.PermissionError)

	group_filters: dict = {BRANCH_FIELD: resolved_branch, "disabled": 0}
	if academic_year:
		group_filters["academic_year"] = academic_year
	if result_mode == "Annual":
		group_filters["academic_term"] = ["is", "not set"]
	elif academic_term:
		group_filters["academic_term"] = ["in", [academic_term, ""]]
	groups = frappe.get_list(
		"Student Group",
		filters=group_filters,
		fields=["name", "student_group_name", "program", "course", "academic_year", "academic_term"],
		order_by="student_group_name asc",
		page_length=200,
	)
	if student_group and student_group not in {row.name for row in groups}:
		frappe.throw(_("Selected Student Group is not available in this branch."), frappe.PermissionError)

	assessment_groups = frappe.get_list(
		"Assessment Group",
		filters={"is_group": 0},
		fields=["name", "assessment_group_name"],
		order_by="assessment_group_name asc",
		page_length=200,
	)

	plan_filters: dict = {BRANCH_FIELD: resolved_branch}
	if academic_year:
		plan_filters["academic_year"] = academic_year
	if academic_term:
		plan_filters["academic_term"] = academic_term
	if student_group:
		plan_filters["student_group"] = student_group
	if result_profile:
		profile_config = get_result_profile_config(result_profile)
		profile_groups = sorted(
			{
				leaf
				for source in profile_config.get("component_sources") or []
				for leaf in source.get("leaf_assessment_groups") or []
			}
		)
		plan_filters["assessment_group"] = ["in", profile_groups or ["__none__"]]
	elif assessment_group:
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
		page_length=200,
	)

	publication = None
	readiness = None
	if student_group and academic_year and (assessment_group or result_profile):
		publication_rows = frappe.get_all(
			PUBLICATION_DOCTYPE,
			filters=_publication_scope_filters(
				school_branch=resolved_branch,
				student_group=student_group,
				academic_year=academic_year,
				academic_term=academic_term,
				assessment_group=assessment_group,
				result_profile=result_profile,
				result_mode=result_mode,
			),
			fields=[
				"name",
				"title",
				"result_profile",
				"result_profile_config_hash",
				"result_profile_config_json",
				"result_mode",
				"publication_version",
				"supersedes_publication",
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
			order_by="publication_version desc, creation desc",
			limit=1,
		)
		publication = publication_rows[0] if publication_rows else None
		publication_profile_config = (
			_readiness_profile_config(publication)
			if publication and publication.get("result_profile")
			else None
		)
		readiness = get_publication_readiness(
			school_branch=resolved_branch,
			student_group=student_group,
			academic_year=academic_year,
			academic_term=academic_term,
			assessment_group=assessment_group,
			result_profile=(publication or {}).get("result_profile") or result_profile,
			result_mode=(publication or {}).get("result_mode") or result_mode,
			profile_config_override=publication_profile_config,
		)
		if publication:
			publication.pop("result_profile_config_json", None)
			publication.pop("result_profile_config_hash", None)

	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
		"allowed_branches": get_allowed_school_branches(),
		"can_approve": bool(APPROVER_ROLES.intersection(frappe.get_roles(frappe.session.user))),
		"filters": {
			"branch": resolved_branch,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"student_group": student_group,
			"assessment_group": assessment_group or "",
			"result_profile": (publication or {}).get("result_profile") or result_profile,
			"result_mode": (publication or {}).get("result_mode") or result_mode,
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
		"result_profiles": result_profiles,
		"plans": plans,
		"publication": publication,
		"readiness": readiness,
	}


@frappe.whitelist()
@guard_eduedge_action("assessment", action="ensure_result_publication")
def ensure_result_publication(
	school_branch: str,
	student_group: str,
	academic_year: str,
	assessment_group: str | None = None,
	academic_term: str | None = None,
	result_profile: str | None = None,
	result_mode: str = "Terminal",
) -> dict:
	_require_operator()
	branch = _resolve_branch(school_branch)
	locked_group = frappe.db.sql(
		"select name from `tabStudent Group` where name=%s for update",
		(student_group,),
	)
	if not locked_group:
		frappe.throw(_("Student Group does not exist."), frappe.DoesNotExistError)
	if not assessment_group and not result_profile:
		frappe.throw(_("Select a Result Profile or Assessment Group."), frappe.ValidationError)
	if (result_mode or "Terminal") == "Annual":
		academic_term = None
	filters = _publication_scope_filters(
		school_branch=branch,
		student_group=student_group,
		academic_year=academic_year,
		academic_term=academic_term,
		assessment_group=assessment_group,
		result_profile=result_profile,
		result_mode=result_mode or "Terminal",
	)
	existing_rows = frappe.get_all(
		PUBLICATION_DOCTYPE,
		filters=filters,
		fields=["name", "publication_version"],
		order_by="publication_version desc, creation desc",
		limit=1,
	)
	name = existing_rows[0].name if existing_rows else None
	if name:
		doc = frappe.get_doc(PUBLICATION_DOCTYPE, name)
		requested_mode = result_mode or "Terminal"
		if result_profile and doc.result_profile != result_profile:
			if doc.status not in {"Draft", "Rejected"}:
				frappe.throw(
					_("Result Profile cannot change after approval begins."),
					frappe.ValidationError,
				)
			doc.result_profile = result_profile
		if result_mode and doc.result_mode != requested_mode:
			if doc.status not in {"Draft", "Rejected"}:
				frappe.throw(
					_("Result Mode cannot change after approval begins."),
					frappe.ValidationError,
				)
			doc.result_mode = requested_mode
		if doc.has_value_changed("result_profile") or doc.has_value_changed("result_mode"):
			if not doc.supersedes_publication:
				set_publication_result_profile_config(doc, None)
			doc.save()
			_refresh_readiness(doc)
		return _publication_payload(name)

	doc = frappe.get_doc(
		{
			"doctype": PUBLICATION_DOCTYPE,
			"school_branch": branch,
			"student_group": student_group,
			"academic_year": academic_year,
			"academic_term": academic_term,
			"assessment_group": assessment_group,
			"result_profile": result_profile,
			"result_mode": result_mode or "Terminal",
			"publication_version": 1,
			"status": "Draft",
		}
	)
	doc.insert()
	append_publication_log(
		doc.name,
		action="Created",
		from_status=None,
		to_status="Draft",
		remarks=_("Result publication scope created."),
	)
	_refresh_readiness(doc)
	return _publication_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="refresh_result_publication")
def refresh_result_publication(publication: str) -> dict:
	_require_operator()
	doc = _get_publication(publication)
	_refresh_readiness(doc)
	return _publication_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="request_result_approval")
def request_result_approval(publication: str) -> dict:
	_require_operator()
	doc = _get_publication(publication, for_update=True)
	if doc.status not in {"Draft", "Rejected"}:
		frappe.throw(_("Only Draft or Rejected publications can be submitted for approval."))
	freeze_publication_result_profile_config(
		doc,
		force_current=not bool(doc.supersedes_publication),
	)
	readiness = _refresh_readiness(doc)
	if not readiness["ready"]:
		frappe.throw(
			_("Results are incomplete. Resolve draft or missing results before requesting approval."),
			frappe.ValidationError,
		)
	_transition(
		doc,
		"Pending Approval",
		action="Requested Approval",
		updates={
			"requested_by": frappe.session.user,
			"requested_on": now_datetime(),
			"approved_by": None,
			"approved_on": None,
			"published_by": None,
			"published_on": None,
			"rejected_by": None,
			"rejected_on": None,
			"rejection_reason": None,
		},
	)
	return _publication_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="approve_results")
def approve_results(publication: str) -> dict:
	_require_approver()
	doc = _get_publication(publication, for_update=True)
	if doc.status != "Pending Approval":
		frappe.throw(_("Only publications pending approval can be approved."))
	readiness = _refresh_readiness(doc)
	if not readiness["ready"]:
		frappe.throw(_("Result completeness changed. Approval is blocked."), frappe.ValidationError)
	_transition(
		doc,
		"Approved",
		action="Approved",
		updates={"approved_by": frappe.session.user, "approved_on": now_datetime()},
	)
	return _publication_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="reject_results")
def reject_results(publication: str, reason: str) -> dict:
	_require_approver()
	doc = _get_publication(publication, for_update=True)
	if doc.status not in {"Pending Approval", "Approved"}:
		frappe.throw(_("Only Pending Approval or Approved publications can be rejected."))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A rejection reason is required."), frappe.ValidationError)
	_transition(
		doc,
		"Rejected",
		action="Rejected",
		remarks=reason,
		updates={
			"rejected_by": frappe.session.user,
			"rejected_on": now_datetime(),
			"rejection_reason": reason,
			"approved_by": None,
			"approved_on": None,
		},
	)
	return _publication_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="publish_results")
def publish_results(publication: str) -> dict:
	_require_approver()
	doc = _get_publication(publication, for_update=True)
	if doc.status != "Approved":
		frappe.throw(_("Results must be approved before publication."))
	readiness = _refresh_readiness(doc)
	if not readiness["ready"]:
		frappe.throw(_("Result completeness changed. Publication is blocked."), frappe.ValidationError)
	_transition(
		doc,
		"Published",
		action="Published",
		updates={
			"published_by": frappe.session.user,
			"published_on": now_datetime(),
			"report_card_ready": 1,
		},
	)
	snapshot_names = create_publication_snapshots(doc.name)
	payload = _publication_payload(doc.name)
	payload["snapshot_count"] = len(snapshot_names)
	return payload


@frappe.whitelist()
@guard_eduedge_action("assessment", action="create_result_publication_revision")
def create_result_publication_revision(publication: str) -> dict:
	_require_approver()
	source = _get_publication(publication, for_update=True)
	if source.status != "Published":
		frappe.throw(_("Only a Published Result Publication can be revised."), frappe.ValidationError)

	filters = _publication_scope_filters(
		school_branch=source.school_branch,
		student_group=source.student_group,
		academic_year=source.academic_year,
		academic_term=source.academic_term,
		assessment_group=source.assessment_group,
		result_profile=source.result_profile,
		result_mode=source.result_mode or "Terminal",
	)
	frappe.db.sql(
		"select name from `tabEduEdge Result Publication` "
		"where school_branch=%(school_branch)s and student_group=%(student_group)s "
		"and academic_year=%(academic_year)s and coalesce(academic_term, '')=%(academic_term)s "
		"and coalesce(assessment_group, '')=%(assessment_group)s "
		"and coalesce(result_profile, '')=%(result_profile)s and result_mode=%(result_mode)s for update",
		{
			"school_branch": source.school_branch,
			"student_group": source.student_group,
			"academic_year": source.academic_year,
			"academic_term": source.academic_term or "",
			"assessment_group": source.assessment_group or "",
			"result_profile": source.result_profile or "",
			"result_mode": source.result_mode or "Terminal",
		},
	)
	existing = frappe.get_all(
		PUBLICATION_DOCTYPE,
		filters=filters,
		fields=["name", "publication_version", "status", "supersedes_publication"],
		order_by="publication_version desc, creation desc",
		limit=1,
	)
	if existing and existing[0].name != source.name:
		if existing[0].status != "Published":
			return _publication_payload(existing[0].name)
		frappe.throw(
			_("A newer published result version exists. Create the correction from {0}.").format(
				existing[0].name
			),
			frappe.ValidationError,
		)
	next_version = int(source.publication_version or 1) + 1
	source_profile_config = get_publication_result_profile_config(source)
	doc = frappe.get_doc(
		{
			"doctype": PUBLICATION_DOCTYPE,
			"school_branch": source.school_branch,
			"student_group": source.student_group,
			"academic_year": source.academic_year,
			"academic_term": source.academic_term,
			"assessment_group": source.assessment_group,
			"result_profile": source.result_profile,
			"result_mode": source.result_mode or "Terminal",
			"publication_version": next_version,
			"supersedes_publication": source.name,
			"status": "Draft",
		}
	)
	if source_profile_config:
		set_publication_result_profile_config(doc, source_profile_config)
	doc.insert()
	append_publication_log(
		doc.name,
		action="Revision Created",
		from_status=None,
		to_status="Draft",
		remarks=_("Created as revision {0} of {1}.").format(next_version, source.name),
	)
	_refresh_readiness(doc)
	return _publication_payload(doc.name)


@frappe.whitelist()
def get_report_card_readiness(
	student_group: str,
	academic_year: str,
	assessment_group: str | None = None,
	academic_term: str | None = None,
) -> dict:
	_require_login()
	branch = frappe.db.get_value("Student Group", student_group, BRANCH_FIELD)
	assert_branch_access(branch)
	publication_rows = frappe.get_all(
		PUBLICATION_DOCTYPE,
		filters={
			"school_branch": branch,
			"student_group": student_group,
			"academic_year": academic_year,
			"academic_term": academic_term or "",
			"assessment_group": assessment_group or "",
		},
		fields=["name", "status", "report_card_ready", "published_on", "publication_version"],
		order_by="publication_version desc, creation desc",
		limit=1,
	)
	publication = publication_rows[0] if publication_rows else None
	return {
		"ready": bool(publication and publication.status == "Published" and publication.report_card_ready),
		"publication": publication,
		"reason": None if publication and publication.status == "Published" else _("Results are not published."),
	}


def _get_publication(name: str, *, for_update: bool = False):
	if for_update:
		rows = frappe.db.sql(
			"select name from `tabEduEdge Result Publication` where name=%s for update",
			(name,),
		)
		if not rows:
			frappe.throw(_("Result Publication does not exist."), frappe.DoesNotExistError)
	doc = frappe.get_doc(PUBLICATION_DOCTYPE, name)
	doc.check_permission("write")
	assert_branch_access(doc.school_branch)
	return doc



def _readiness_profile_config(publication) -> dict | None:
	if not publication or not publication.get("result_profile"):
		return None
	if (
		publication.get("status") in {"Draft", "Rejected"}
		and not publication.get("supersedes_publication")
	):
		return get_result_profile_config(publication.get("result_profile"))
	return get_publication_result_profile_config(publication)

def _refresh_readiness(doc) -> dict:
	readiness = get_publication_readiness(
		school_branch=doc.school_branch,
		student_group=doc.student_group,
		academic_year=doc.academic_year,
		academic_term=doc.academic_term,
		assessment_group=doc.assessment_group,
		result_profile=doc.get("result_profile"),
		result_mode=doc.get("result_mode") or "Terminal",
		profile_config_override=(
			_readiness_profile_config(doc)
			if doc.get("result_profile")
			else None
		),
	)
	updates = {
		"expected_results": readiness["expected_results"],
		"submitted_results": readiness["submitted_results"],
		"draft_results": readiness["draft_results"],
		"missing_results": readiness["missing_results"],
		"report_card_ready": int(doc.status == "Published" and readiness["ready"]),
	}
	for fieldname, value in updates.items():
		doc.db_set(fieldname, value, update_modified=False)
		doc.set(fieldname, value)
	return readiness


def _transition(
	doc,
	to_status: str,
	*,
	action: str,
	updates: dict | None = None,
	remarks: str | None = None,
) -> None:
	from_status = doc.status
	frappe.flags.in_eduedge_result_publication_transition = True
	try:
		doc.status = to_status
		for fieldname, value in (updates or {}).items():
			doc.set(fieldname, value)
		doc.save()
	finally:
		frappe.flags.in_eduedge_result_publication_transition = False
	append_publication_log(
		doc.name,
		action=action,
		from_status=from_status,
		to_status=to_status,
		remarks=remarks,
	)


def _publication_payload(name: str) -> dict:
	row = frappe.db.get_value(
		PUBLICATION_DOCTYPE,
		name,
		[
			"name",
			"title",
			"school_branch",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
			"publication_version",
			"supersedes_publication",
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
	return row or {}
