from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.access_control import user_has_role_permission
from eduedge.cbt.public_access import can_author_public_exams
from eduedge.cbt.question_responsibilities import get_question_responsibility_state
from eduedge.education.operations_policy import resolve_question_governance
from eduedge.eduedge.doctype.eduedge_cbt_question import eduedge_cbt_question as question_doctype
from eduedge.eduedge.doctype.eduedge_cbt_question.eduedge_cbt_question import (
	PLATFORM_BANK,
	SCHOOL_BANK,
	can_review_questions,
)

QUESTION_DOCTYPE = "EduEdge CBT Question"
GOVERNANCE_ACTION_FLAG = "eduedge_question_governance_action"

ACTION_SUBMIT = "submit_for_review"
ACTION_RETURN = "return_to_draft"
ACTION_REQUEST_CHANGES = "request_changes"
ACTION_RECOMMEND = "recommend"
ACTION_APPROVE = "approve"
ACTION_RETIRE = "retire"

ACTION_DEFINITIONS = {
	ACTION_SUBMIT: {"label": _("Send for Review"), "confirmation": False},
	ACTION_RETURN: {"label": _("Return to Draft"), "confirmation": True},
	ACTION_REQUEST_CHANGES: {
		"label": _("Request Changes"),
		"confirmation": True,
		"requires_feedback": True,
	},
	ACTION_RECOMMEND: {"label": _("Recommend Question"), "confirmation": True},
	ACTION_APPROVE: {"label": _("Approve Question"), "confirmation": True},
	ACTION_RETIRE: {"label": _("Retire Question"), "confirmation": True},
}

# The DocType controller predates the Standard workflow. Its internal transition
# guard remains useful, so extend its allowed transition map instead of bypassing
# validation. The lifecycle hook still blocks every direct Status write.
question_doctype.ALLOWED_STATUS_TRANSITIONS.update(
	{
		"Draft": {"Draft", "Under Review", "Under Subject Review"},
		"Under Review": {
			"Draft",
			"Under Review",
			"Changes Requested",
			"Recommended",
			"Approved",
		},
		"Under Subject Review": {"Under Subject Review", "Changes Requested", "Recommended"},
		"Changes Requested": {"Changes Requested", "Draft", "Under Review", "Under Subject Review"},
		"Recommended": {"Recommended", "Approved"},
		"Approved": {"Approved", "Retired"},
		"Retired": {"Retired"},
	}
)

PRIVILEGED_REVIEW_ROLES = {
	"Administrator",
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
}


def _value(question: Any, fieldname: str, default=None):
	if hasattr(question, "get"):
		value = question.get(fieldname)
	else:
		value = getattr(question, fieldname, None)
	return default if value is None else value


def _question_institution(question: Any) -> str:
	if _value(question, "ownership_scope") != SCHOOL_BANK:
		return ""
	branch = _value(question, "school_branch") or ""
	if not branch:
		return ""
	return frappe.db.get_value("EduEdge School Branch", branch, "institution") or ""


def _question_policy(question: Any) -> dict:
	if _value(question, "ownership_scope") == PLATFORM_BANK:
		return {
			"source": "EduEdge Examination Bank",
			"question_approval_mode": "Simple",
			"require_separate_question_approver": False,
			"allow_academic_admin_override": True,
		}
	institution = _question_institution(question)
	if not institution:
		return {
			"source": "Missing Institution Context",
			"institution": None,
			"question_approval_mode": "Standard",
			"require_separate_question_approver": True,
			"allow_academic_admin_override": False,
		}
	return resolve_question_governance(institution)


def _question_responsibilities(question: Any, user: str) -> dict:
	if _value(question, "ownership_scope") == PLATFORM_BANK:
		allowed = bool(can_author_public_exams(user))
		return {
			"user": user,
			"institution": "",
			"school_branch": "",
			"course": _value(question, "course") or "",
			"can_author": allowed,
			"can_subject_review": allowed,
			"can_final_approve": allowed,
			"assignment_names": [],
		}
	institution = _question_institution(question)
	return get_question_responsibility_state(
		user=user,
		institution=institution,
		course=_value(question, "course") or "",
		school_branch=_value(question, "school_branch") or "",
	)


def _can_write_question(question: Any) -> bool:
	if hasattr(question, "has_permission"):
		return bool(question.has_permission("write"))
	return bool(frappe.has_permission(QUESTION_DOCTYPE, "write"))


def _can_subject_review(user: str) -> bool:
	return user_has_role_permission(QUESTION_DOCTYPE, "write", user)


def _academic_admin_override_blocked(policy: dict, user: str) -> bool:
	if policy.get("allow_academic_admin_override"):
		return False
	roles = set(frappe.get_roles(user))
	if "Academic Administrator" not in roles:
		return False
	return not bool(PRIVILEGED_REVIEW_ROLES.intersection(roles | {user}))


def _common_scope_reason(question: Any, policy: dict) -> str:
	if policy.get("source") == "Missing Institution Context":
		return _("The Question Branch is not linked to an Institution, so its approval policy cannot be resolved.")
	if not _value(question, "course"):
		return _("Select a Subject / Course before using Question governance actions.")
	return ""


def _author_reason(question: Any, policy: dict, responsibilities: dict, can_write: bool) -> str:
	common = _common_scope_reason(question, policy)
	if common:
		return common
	if not can_write:
		return _("You do not have permission to change this question.")
	if not responsibilities.get("can_author"):
		return _("You do not have an active Question Author assignment for this Institution, Branch, and Subject / Course.")
	return ""


def _subject_review_reason(
	question: Any,
	policy: dict,
	user: str,
	responsibilities: dict,
	can_subject_review: bool,
) -> str:
	common = _common_scope_reason(question, policy)
	if common:
		return common
	if policy.get("question_approval_mode") != "Standard":
		return _("Subject recommendation is available only when the Institution uses Standard approval.")
	if not can_subject_review:
		return _("Your role does not provide CBT Question review capability.")
	if _value(question, "ownership_scope") == PLATFORM_BANK and not can_author_public_exams(user):
		return _("EduEdge Examination Bank review requires public-exam authoring access.")
	if not responsibilities.get("can_subject_review"):
		return _("You do not have an active Subject Reviewer assignment for this Institution, Branch, and Subject / Course.")
	return ""


def _final_approval_reason(
	question: Any,
	policy: dict,
	user: str,
	responsibilities: dict,
	can_review: bool,
) -> str:
	common = _common_scope_reason(question, policy)
	if common:
		return common
	if not can_review:
		return _("Your role does not permit final question approval.")
	if _value(question, "ownership_scope") == PLATFORM_BANK and not can_author_public_exams(user):
		return _("EduEdge Examination Bank approval requires public-exam authoring access.")
	if not responsibilities.get("can_final_approve"):
		return _("You do not have an active Final Approver assignment for this Institution, Branch, and Subject / Course.")
	if policy.get("require_separate_question_approver") and _value(question, "owner") == user:
		return _("The question author cannot approve this question because separate author and approver governance is enabled.")
	if _academic_admin_override_blocked(policy, user):
		return _("Academic Administrator override is disabled for this Institution.")
	return ""


def _action_target(action: str, status: str, policy: dict) -> str:
	mode = policy.get("question_approval_mode") or "Standard"
	if action == ACTION_SUBMIT:
		return "Under Subject Review" if mode == "Standard" else "Under Review"
	if action == ACTION_RETURN:
		return "Draft"
	if action == ACTION_REQUEST_CHANGES:
		return "Changes Requested"
	if action == ACTION_RECOMMEND:
		return "Recommended"
	if action == ACTION_APPROVE:
		return "Approved"
	if action == ACTION_RETIRE:
		return "Retired"
	return status


def _action_source_allowed(action: str, status: str, policy: dict) -> bool:
	mode = policy.get("question_approval_mode") or "Standard"
	if action == ACTION_SUBMIT:
		return status in {"Draft", "Changes Requested"}
	if action == ACTION_RETURN:
		return status == "Changes Requested" or (status == "Under Review" and mode == "Simple")
	if action in {ACTION_REQUEST_CHANGES, ACTION_RECOMMEND}:
		return mode == "Standard" and status in {"Under Subject Review", "Under Review"}
	if action == ACTION_APPROVE:
		return status == ("Recommended" if mode == "Standard" else "Under Review")
	if action == ACTION_RETIRE:
		return status == "Approved"
	return False


def _action_reason(
	action: str,
	question: Any,
	status: str,
	policy: dict,
	user: str,
	responsibilities: dict,
	can_write: bool,
	can_subject_review: bool,
	can_review: bool,
) -> str:
	if not _action_source_allowed(action, status, policy):
		return _("This action is not available while the question is {0}.").format(status)
	if action in {ACTION_SUBMIT, ACTION_RETURN}:
		return _author_reason(question, policy, responsibilities, can_write)
	if action in {ACTION_REQUEST_CHANGES, ACTION_RECOMMEND}:
		return _subject_review_reason(question, policy, user, responsibilities, can_subject_review)
	if action in {ACTION_APPROVE, ACTION_RETIRE}:
		return _final_approval_reason(question, policy, user, responsibilities, can_review)
	return _("This Question action is not available.")


def get_question_action_state(
	question: Any,
	*,
	user: str | None = None,
	can_write: bool | None = None,
	can_review: bool | None = None,
	can_subject_review: bool | None = None,
) -> dict:
	resolved_user = user or frappe.session.user
	status = _value(question, "status", "Draft") or "Draft"
	policy = _question_policy(question)
	responsibilities = _question_responsibilities(question, resolved_user)
	resolved_can_write = _can_write_question(question) if can_write is None else bool(can_write)
	resolved_can_review = can_review_questions(resolved_user) if can_review is None else bool(can_review)
	resolved_can_subject_review = (
		_can_subject_review(resolved_user) if can_subject_review is None else bool(can_subject_review)
	)

	actions = []
	for action, definition in ACTION_DEFINITIONS.items():
		reason = _action_reason(
			action,
			question,
			status,
			policy,
			resolved_user,
			responsibilities,
			resolved_can_write,
			resolved_can_subject_review,
			resolved_can_review,
		)
		actions.append(
			{
				"action": action,
				"label": definition["label"],
				"source_status": status,
				"target_status": _action_target(action, status, policy),
				"requires_confirmation": bool(definition.get("confirmation")),
				"requires_feedback": bool(definition.get("requires_feedback")),
				"allowed": not bool(reason),
				"reason": reason,
			}
		)

	return {
		"status": status,
		"modified": str(_value(question, "modified") or ""),
		"policy": {
			"source": policy.get("source"),
			"institution": policy.get("institution") or _question_institution(question) or None,
			"question_approval_mode": policy.get("question_approval_mode"),
			"require_separate_question_approver": bool(policy.get("require_separate_question_approver")),
			"allow_academic_admin_override": bool(policy.get("allow_academic_admin_override")),
		},
		"responsibilities": responsibilities,
		"audit": {
			"recommended_by": _value(question, "recommended_by") or "",
			"recommended_on": _value(question, "recommended_on"),
			"review_feedback": _value(question, "review_feedback") or "",
			"approved_by": _value(question, "reviewed_by") or "",
			"approved_on": _value(question, "reviewed_on"),
		},
		"actions": actions,
	}


def action_by_name(state: dict, action: str) -> dict | None:
	return next((row for row in state.get("actions") or [] if row.get("action") == action), None)


@contextmanager
def governance_action_context(action: str):
	previous = getattr(frappe.flags, GOVERNANCE_ACTION_FLAG, None)
	setattr(frappe.flags, GOVERNANCE_ACTION_FLAG, action)
	try:
		yield
	finally:
		setattr(frappe.flags, GOVERNANCE_ACTION_FLAG, previous)


def validate_question_governance_transition(doc, method: str | None = None) -> None:
	before = doc.get_doc_before_save()
	previous_status = before.status if before else "Draft"
	current_status = doc.status or "Draft"
	if current_status == previous_status:
		return
	if getattr(frappe.flags, GOVERNANCE_ACTION_FLAG, None):
		return
	frappe.throw(
		_("Question Status is governed. Use the Question Bank or Question Builder action instead of changing Status directly."),
		frappe.ValidationError,
		title=_("Use a Governed Question Action"),
	)


def apply_question_action(
	doc,
	action: str,
	expected_modified: str | None = None,
	feedback: str | None = None,
) -> dict:
	definition = ACTION_DEFINITIONS.get(action)
	if not definition:
		frappe.throw(_("Select a valid Question action."), frappe.ValidationError)
	if expected_modified and str(doc.modified) != str(expected_modified):
		frappe.throw(
			_("This question changed after the page was loaded. Refresh it before applying the action."),
			frappe.TimestampMismatchError,
		)

	state = get_question_action_state(doc)
	action_state = action_by_name(state, action)
	if not action_state or not action_state.get("allowed"):
		frappe.throw(
			(action_state or {}).get("reason") or _("This Question action is not available."),
			frappe.PermissionError,
		)

	clean_feedback = str(feedback or "").strip()
	if action_state.get("requires_feedback") and not clean_feedback:
		frappe.throw(_("Enter the changes required before returning this question to the author."), frappe.ValidationError)

	with governance_action_context(action):
		doc.status = action_state["target_status"]
		if action == ACTION_SUBMIT:
			doc.reviewed_by = None
			doc.reviewed_on = None
			doc.recommended_by = None
			doc.recommended_on = None
		elif action == ACTION_RETURN:
			doc.reviewed_by = None
			doc.reviewed_on = None
		elif action == ACTION_REQUEST_CHANGES:
			doc.review_feedback = clean_feedback
			doc.recommended_by = None
			doc.recommended_on = None
			doc.reviewed_by = None
			doc.reviewed_on = None
		elif action == ACTION_RECOMMEND:
			doc.recommended_by = frappe.session.user
			doc.recommended_on = now_datetime()
			if clean_feedback:
				doc.review_feedback = clean_feedback
		elif action == ACTION_APPROVE:
			doc.reviewed_by = frappe.session.user
			doc.reviewed_on = now_datetime()
		doc.save()

	return {
		"question": doc.name,
		"status": doc.status,
		"modified": str(doc.modified),
		"recommended_by": doc.recommended_by or "",
		"recommended_on": doc.recommended_on,
		"review_feedback": doc.review_feedback or "",
		"reviewed_by": doc.reviewed_by or "",
		"reviewed_on": doc.reviewed_on,
		"action": action,
		"action_label": definition["label"],
		"action_state": get_question_action_state(doc),
	}
