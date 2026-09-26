from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.pdf import get_pdf

from eduedge.education.report_cards import (
	APPROVER_ROLES,
	OPERATIONAL_ROLES,
	REVIEW_DOCTYPE,
	assert_report_card_access,
	assert_report_card_review_management,
	can_manage_report_card_reviews,
	can_view_report_card_scope,
	get_publication_student_summaries,
	get_published_publication,
	get_student_report_card_payload,
	refresh_review_metrics,
)
from eduedge.education.offerings import assert_branch_access, get_context_branch
from eduedge.education.report_card_issues import create_report_card_issue, get_report_card_issue_history
from eduedge.platform.access import guard_eduedge_action
from eduedge.services.branch_context import get_allowed_school_branches, get_current_school_branch
from eduedge.services.institution_branding import get_report_identity



def _attach_report_identity(payload: dict) -> dict:
	if (
		(payload.get("issue") or payload.get("issue_record"))
		and payload.get("branding")
		and payload.get("terminology")
	):
		return payload
	branch_name = (payload.get("branch") or {}).get("name")
	identity = get_report_identity(branch=branch_name)
	payload["institution"] = identity["institution"]
	payload["branding"] = identity["branding"]
	payload["terminology"] = identity["terminology"]
	if identity.get("address"):
		payload["address"] = identity["address"]
	return payload

def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)


def _require_operator() -> None:
	_require_login()
	if not OPERATIONAL_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to manage report cards."), frappe.PermissionError)


def _require_approver() -> None:
	_require_login()
	if not APPROVER_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(
			_("You are not permitted to approve progression recommendations."),
			frappe.PermissionError,
		)


def _resolve_branch(branch: str | None = None) -> str:
	resolved = branch or (get_current_school_branch() or {}).get("name") or get_context_branch()
	if not resolved:
		frappe.throw(_("Select a School Branch / Campus first."), frappe.ValidationError)
	assert_branch_access(resolved)
	return resolved


@frappe.whitelist()
def get_report_card_context(
	branch: str | None = None,
	publication: str | None = None,
	student: str | None = None,
) -> dict:
	_require_operator()
	resolved_branch = _resolve_branch(branch)
	publications = frappe.get_list(
		"EduEdge Result Publication",
		filters={
			"school_branch": resolved_branch,
			"status": "Published",
			"report_card_ready": 1,
		},
		fields=[
			"name",
			"title",
			"student_group",
			"academic_year",
			"academic_term",
			"assessment_group",
			"result_profile",
			"result_mode",
			"publication_version",
			"supersedes_publication",
			"published_on",
		],
		order_by="published_on desc, modified desc",
		page_length=200,
	)
	publications = [
		row for row in publications
		if can_view_report_card_scope(row)
	]


	selected_publication = None
	students = []
	selected_student = None
	if publication:
		selected_publication = get_published_publication(publication)
		if selected_publication.school_branch != resolved_branch:
			frappe.throw(_("Selected publication belongs to another branch."), frappe.PermissionError)
		students = get_publication_student_summaries(publication)
		if student:
			selected_student = next(
				(row for row in students if row.get("student") == student),
				None,
			)
			if not selected_student:
				frappe.throw(_("Selected student is outside this publication."), frappe.PermissionError)

	current_branch = get_current_school_branch()
	full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	roles = set(frappe.get_roles(frappe.session.user))
	return {
		"user": {"name": frappe.session.user, "full_name": full_name},
		"tenant_name": (current_branch or {}).get("company"),
		"current_branch": current_branch,
		"allowed_branches": get_allowed_school_branches(),
		"can_approve": bool(APPROVER_ROLES.intersection(roles)),
		"can_review": bool(
			selected_publication and can_manage_report_card_reviews(selected_publication)
		),
		"filters": {
			"branch": resolved_branch,
			"publication": publication,
			"student": student,
		},
		"publications": publications,
		"publication": dict(selected_publication) if selected_publication else None,
		"students": students,
		"selected_student": selected_student,
		"counts": {
			"students": len(students),
			"prepared_reviews": sum(1 for row in students if row.get("review")),
			"recommended": sum(
				1
				for row in students
				if (row.get("review") or {}).get("progression_status") == "Recommended"
			),
			"approved": sum(
				1
				for row in students
				if (row.get("review") or {}).get("progression_status") == "Approved"
			),
			"issued": sum(1 for row in students if row.get("issue")),
		},
	}


@frappe.whitelist()
@guard_eduedge_action("assessment", action="prepare_report_cards")
def prepare_report_cards(publication: str) -> dict:
	_require_operator()
	locked_publication = frappe.db.sql(
		"select name from `tabEduEdge Result Publication` where name=%s for update",
		(publication,),
	)
	if not locked_publication:
		frappe.throw(_("Result Publication does not exist."), frappe.DoesNotExistError)
	publication_row = get_published_publication(publication)
	assert_branch_access(publication_row.school_branch)
	assert_report_card_review_management(publication_row)
	summaries = get_publication_student_summaries(publication)
	created = 0
	updated = 0
	for summary in summaries:
		review_name = frappe.db.exists(
			REVIEW_DOCTYPE,
			{"result_publication": publication, "student": summary["student"]},
		)
		if review_name:
			doc = frappe.get_doc(REVIEW_DOCTYPE, review_name)
			if doc.progression_status == "Draft":
				refresh_review_metrics(doc)
				doc.save()
				updated += 1
			continue
		doc = frappe.get_doc(
			{
				"doctype": REVIEW_DOCTYPE,
				"result_publication": publication,
				"student": summary["student"],
				"progression_recommendation": "Pending Review",
				"progression_status": "Draft",
			}
		)
		refresh_review_metrics(doc)
		doc.insert()
		created += 1
	return {"created": created, "updated": updated, "total": len(summaries)}


@frappe.whitelist()
@guard_eduedge_action("assessment", action="save_report_card_review")
def save_report_card_review(
	review: str,
	class_teacher_comment: str | None = None,
	principal_comment: str | None = None,
	progression_recommendation: str | None = None,
	last_review_note: str | None = None,
) -> dict:
	_require_operator()
	doc = frappe.get_doc(REVIEW_DOCTYPE, review)
	doc.check_permission("write")
	assert_branch_access(doc.school_branch)
	assert_report_card_review_management(get_published_publication(doc.result_publication))
	if doc.progression_status != "Draft":
		frappe.throw(
			_("Only Draft report-card reviews can be edited. Reopen the review first."),
			frappe.ValidationError,
		)

	roles = set(frappe.get_roles(frappe.session.user))
	if principal_comment is not None and not APPROVER_ROLES.intersection(roles):
		if (principal_comment or "").strip() != (doc.principal_comment or "").strip():
			frappe.throw(
				_("Only an authorized academic approver can change the principal comment."),
				frappe.PermissionError,
			)

	if class_teacher_comment is not None:
		doc.class_teacher_comment = (class_teacher_comment or "").strip()
	if principal_comment is not None:
		doc.principal_comment = (principal_comment or "").strip()
	if progression_recommendation is not None:
		doc.progression_recommendation = progression_recommendation
	if last_review_note is not None:
		doc.last_review_note = (last_review_note or "").strip()
	refresh_review_metrics(doc)
	doc.save()
	return _review_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="recommend_progression")
def recommend_progression(review: str) -> dict:
	_require_operator()
	doc = _get_review_for_update(review)
	assert_report_card_review_management(get_published_publication(doc.result_publication))
	if doc.progression_status != "Draft":
		frappe.throw(_("Only Draft reviews can be recommended."), frappe.ValidationError)
	if doc.progression_recommendation == "Pending Review":
		frappe.throw(_("Select a progression recommendation first."), frappe.ValidationError)

	settings = frappe.get_single("EduEdge Settings")
	if settings.require_class_teacher_comment and not (doc.class_teacher_comment or "").strip():
		frappe.throw(_("Class Teacher Comment is required."), frappe.ValidationError)
	refresh_review_metrics(doc)
	_transition(
		doc,
		"Recommended",
		updates={
			"recommended_by": frappe.session.user,
			"recommended_on": now_datetime(),
			"approved_by": None,
			"approved_on": None,
		},
	)
	return _review_payload(doc.name)


@frappe.whitelist()
@guard_eduedge_action("assessment", action="approve_progression")
def approve_progression(review: str) -> dict:
	_require_approver()
	doc = _get_review_for_update(review)
	if doc.progression_status != "Recommended":
		frappe.throw(_("Only Recommended reviews can be approved."), frappe.ValidationError)
	settings = frappe.get_single("EduEdge Settings")
	if settings.require_principal_comment and not (doc.principal_comment or "").strip():
		frappe.throw(_("Principal Comment is required before approval."), frappe.ValidationError)
	refresh_review_metrics(doc)
	_transition(
		doc,
		"Approved",
		updates={
			"approved_by": frappe.session.user,
			"approved_on": now_datetime(),
		},
	)
	issue_name = create_report_card_issue(doc.name)
	payload = _review_payload(doc.name)
	payload["report_card_issue"] = issue_name
	return payload


@frappe.whitelist()
@guard_eduedge_action("assessment", action="reopen_progression_review")
def reopen_progression_review(review: str, reason: str) -> dict:
	_require_approver()
	doc = _get_review_for_update(review)
	if doc.progression_status not in {"Recommended", "Approved"}:
		frappe.throw(_("Only Recommended or Approved reviews can be reopened."))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A reopening reason is required."), frappe.ValidationError)
	_transition(
		doc,
		"Draft",
		updates={
			"recommended_by": None,
			"recommended_on": None,
			"approved_by": None,
			"approved_on": None,
			"last_review_note": reason,
		},
	)
	return _review_payload(doc.name)


@frappe.whitelist()
def get_report_card_history(publication: str, student: str) -> dict:
	_require_operator()
	publication_row = get_published_publication(publication)
	assert_report_card_access(publication_row, student)
	issue_history = get_report_card_issue_history(publication, student)

	filters = {
		"school_branch": publication_row.school_branch,
		"student_group": publication_row.student_group,
		"academic_year": publication_row.academic_year,
		"result_mode": publication_row.result_mode or "Terminal",
		"status": "Published",
	}
	if publication_row.academic_term:
		filters["academic_term"] = publication_row.academic_term
	else:
		filters["academic_term"] = ["is", "not set"]
	if publication_row.result_profile:
		filters["result_profile"] = publication_row.result_profile
	elif publication_row.assessment_group:
		filters["assessment_group"] = publication_row.assessment_group

	publications = frappe.get_all(
		"EduEdge Result Publication",
		filters=filters,
		fields=[
			"name",
			"title",
			"publication_version",
			"supersedes_publication",
			"published_on",
		],
		order_by="publication_version desc, published_on desc",
		page_length=0,
	)
	return {
		"issues": issue_history,
		"publications": [dict(row) for row in publications],
	}


@frappe.whitelist()
def get_report_card(publication: str, student: str) -> dict:
	_require_login()
	return _attach_report_identity(
		get_student_report_card_payload(publication, student)
	)


@frappe.whitelist()
def preview_report_card(publication: str, student: str) -> None:
	_require_login()
	payload = _attach_report_identity(
		get_student_report_card_payload(publication, student)
	)
	assert_report_card_access(frappe._dict(payload["publication"]), student)
	settings = frappe.get_single("EduEdge Settings")
	letterhead = None
	if settings.report_card_letter_head:
		letterhead = frappe.db.get_value(
			"Letter Head", settings.report_card_letter_head, "content"
		)

	html = frappe.render_template(
		"eduedge/templates/report_card.html",
		{
			**payload,
			"letterhead": letterhead,
			"show_marks": bool(settings.report_card_show_marks),
		},
	)
	final_html = frappe.render_template(
		"frappe/www/printview.html",
		{"body": html, "title": _("Student Report Card")},
	)
	frappe.response.filename = f"Report Card {student}.pdf"
	frappe.response.filecontent = get_pdf(final_html)
	frappe.response.type = "pdf"


def _get_review_for_update(name: str):
	rows = frappe.db.sql(
		"select name from `tabEduEdge Report Card Review` where name=%s for update",
		(name,),
	)
	if not rows:
		frappe.throw(_("Report Card Review does not exist."), frappe.DoesNotExistError)
	doc = frappe.get_doc(REVIEW_DOCTYPE, name)
	doc.check_permission("write")
	assert_branch_access(doc.school_branch)
	return doc


def _transition(doc, to_status: str, *, updates: dict | None = None) -> None:
	frappe.flags.in_eduedge_report_card_transition = True
	try:
		doc.progression_status = to_status
		for fieldname, value in (updates or {}).items():
			doc.set(fieldname, value)
		doc.save()
	finally:
		frappe.flags.in_eduedge_report_card_transition = False


def _review_payload(name: str) -> dict:
	return frappe.db.get_value(
		REVIEW_DOCTYPE,
		name,
		[
			"name",
			"result_publication",
			"school_branch",
			"student_group",
			"student",
			"student_name",
			"academic_year",
			"academic_term",
			"assessment_group",
			"course_count",
			"total_score",
			"maximum_score",
			"average_percent",
			"overall_grade",
			"attendance_present",
			"attendance_absent",
			"attendance_leave",
			"attendance_total",
			"attendance_percent",
			"class_teacher_comment",
			"principal_comment",
			"progression_recommendation",
			"progression_status",
			"recommended_by",
			"recommended_on",
			"approved_by",
			"approved_on",
			"last_review_note",
		],
		as_dict=True,
	) or {}
