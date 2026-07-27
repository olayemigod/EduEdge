from __future__ import annotations

import frappe
from frappe import _

from eduedge.cbt.question_governance import apply_question_action, get_question_action_state

QUESTION_DOCTYPE = "EduEdge CBT Question"


def _require_readable_question(question: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	doc = frappe.get_doc(QUESTION_DOCTYPE, question)
	if not doc.has_permission("read"):
		frappe.throw(_("You are not permitted to view this CBT question."), frappe.PermissionError)
	return doc


@frappe.whitelist()
def get_action_state(question: str) -> dict:
	doc = _require_readable_question(question)
	return get_question_action_state(doc)


@frappe.whitelist()
def perform_action(question: str, action: str, expected_modified: str | None = None) -> dict:
	doc = _require_readable_question(question)
	return apply_question_action(doc, action, expected_modified=expected_modified)
