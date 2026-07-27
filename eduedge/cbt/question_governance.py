from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.cbt.public_access import can_author_public_exams
from eduedge.education.operations_policy import resolve_question_governance
from eduedge.eduedge.doctype.eduedge_cbt_question.eduedge_cbt_question import (
	PLATFORM_BANK,
	SCHOOL_BANK,
	can_review_questions,
)

QUESTION_DOCTYPE = "EduEdge CBT Question"
GOVERNANCE_ACTION_FLAG = "eduedge_question_governance_action"

ACTION_SUBMIT = "submit_for_review"
ACTION_RETURN = "return_to_draft"
ACTION_APPROVE = "approve"
ACTION_RETIRE = "retire"

ACTION_DEFINITIONS = {
	ACTION_SUBMIT: {
		"label": _("Send for Review"),
		"source_status": "Draft",
		"target_status": "Under Review",
		"confirmation": False,
	},
	ACTION_RETURN: {
		"label": _("Return to Draft"),
		"source_status": "Under Review",
		"target_status": "Draft",
		"confirmation": True,
	},
	ACTION_APPROVE: {
		"label": _("Approve Question"),
		"source_status": "Under Review",
		"target_status": "Approved",
		"confirmation": True,
	},
	ACTION_RETIRE: {
		"label": _("Retire Question"),
		"source_status": "Approved",
		"target_status": "Retired",
		"confirmation": True,
	},
}

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


def _can_write_question(question: Any) -> bool:
	if hasattr(question, "has_permission"):
		return bool(question.has_permission("write"))
	return bool(frappe.has_permission(QUESTION_DOCTYPE, "write"))


def _academic_admin_override_blocked(policy: dict, user: str) -> bool:
	if policy.get("allow_academic_admin_override"):
		return False
	roles = set(frappe.get_roles(user))
	if "Academic Administrator" not in roles:
		return False
	return not bool(PRIVILEGED_REVIEW_ROLES.intersection(roles | {user}))


def _review_block_reason(question: Any, policy: dict, user: str, can_review: bool) -> str:
	if not can_review:
		return _("Your role does not permit final question approval.")
	if _value(question, "ownership_scope") == PLATFORM_BANK and not can_author_public_exams(user):
		return _("EduEdge Examination Bank approval requires public-exam authoring access.")
	if policy.get("source") == "Missing Institution Context":
		return _("The Question Branch is not linked to an Institution, so its approval policy cannot be resolved.")
	if policy.get("question_approval_mode") == "Standard":
		return _("This Institution uses Standard approval. A subject reviewer recommendation is required before final approval.")
	if policy.get("require_separate_question_approver") and _value(question, "owner") == user:
		return _("The question author cannot approve this question because separate author and approver governance is enabled.")
	if _academic_admin_override_blocked(policy, user):
		return _("Academic Administrator override is disabled for this Institution.")
	return ""


def get_question_action_state(
	question: Any,
	*,
	user: str | None = None,
	can_write: bool | None = None,
	can_review: bool | None = None,
) -> dict:
	resolved_user = user or frappe.session.user
	status = _value(question, "status", "Draft") or "Draft"
	policy = _question_policy(question)
	resolved_can_write = _can_write_question(question) if can_write is None else bool(can_write)
	resolved_can_review = can_review_questions(resolved_user) if can_review is None else bool(can_review)

	actions = []
	for action, definition in ACTION_DEFINITIONS.items():
		reason = ""
		if status != definition["source_status"]:
			reason = _("This action is not available while the question is {0}.").format(status)
		elif action in {ACTION_SUBMIT, ACTION_RETURN} and not resolved_can_write:
			reason = _("You do not have permission to change this question.")
		elif action == ACTION_APPROVE:
			reason = _review_block_reason(question, policy, resolved_user, resolved_can_review)
		elif action == ACTION_RETIRE:
			if not resolved_can_review:
				reason = _("Your role does not permit question retirement.")
			elif _value(question, "ownership_scope") == PLATFORM_BANK and not can_author_public_exams(resolved_user):
				reason = _("EduEdge Examination Bank retirement requires public-exam authoring access.")

		actions.append(
			{
				"action": action,
				"label": definition["label"],
				"source_status": definition["source_status"],
				"target_status": definition["target_status"],
				"requires_confirmation": definition["confirmation"],
				"allowed": not bool(reason),
				"reason": reason,
			}
		)

	return {
		"status": status,
		"policy": {
			"source": policy.get("source"),
			"institution": policy.get("institution") or _question_institution(question) or None,
			"question_approval_mode": policy.get("question_approval_mode"),
			"require_separate_question_approver": bool(policy.get("require_separate_question_approver")),
			"allow_academic_admin_override": bool(policy.get("allow_academic_admin_override")),
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


def apply_question_action(doc, action: str, expected_modified: str | None = None) -> dict:
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

	with governance_action_context(action):
		doc.status = definition["target_status"]
		if action in {ACTION_SUBMIT, ACTION_RETURN}:
			doc.reviewed_by = None
			doc.reviewed_on = None
		elif action == ACTION_APPROVE:
			doc.reviewed_by = frappe.session.user
			doc.reviewed_on = now_datetime()
		doc.save()

	return {
		"question": doc.name,
		"status": doc.status,
		"modified": str(doc.modified),
		"reviewed_by": doc.reviewed_by or "",
		"reviewed_on": doc.reviewed_on,
		"action": action,
		"action_label": definition["label"],
		"action_state": get_question_action_state(doc),
	}
