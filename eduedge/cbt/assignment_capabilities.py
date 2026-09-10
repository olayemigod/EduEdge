from __future__ import annotations

import frappe
from frappe import _

from eduedge.education.instructor_assignment_capabilities import (
    assignment_capability_enforcement_enabled,
    require_instructor_assignment_capability,
)
from eduedge.education.instructor_scope import is_limited_instructor_user

SCHOOL_BANK = "School Question Bank"
AUTHOR_ACTIONS = {"submit_for_review", "return_to_draft"}
REVIEW_ONLY_ACTIONS = {"request_changes", "recommend", "approve", "retire"}


def validate_question_authoring_capability(doc, method: str | None = None) -> None:
    """Require can_author_cbt for limited Instructor users editing school questions.

    Review and approval actions remain governed by Question Responsibility and are not
    converted into teaching-assignment capabilities. Public examination-bank questions
    also keep their separate public-exam capability model.
    """
    user = frappe.session.user
    if not assignment_capability_enforcement_enabled() or not is_limited_instructor_user(user):
        return
    if doc.get("ownership_scope") != SCHOOL_BANK:
        return

    governance_action = str(getattr(frappe.flags, "eduedge_question_governance_action", "") or "")
    if governance_action in REVIEW_ONLY_ACTIONS:
        return
    if governance_action and governance_action not in AUTHOR_ACTIONS:
        # Unknown governed actions fail closed for a limited Instructor rather than
        # accidentally inheriting author privileges.
        frappe.throw(_("This Question governance action is not available through Instructor authoring capability."), frappe.PermissionError)

    branch = str(doc.get("school_branch") or "").strip()
    offering = str(doc.get("program_offering") or "").strip()
    course = str(doc.get("course") or "").strip()
    student_group = str(doc.get("student_group") or "").strip()
    if not branch:
        frappe.throw(_("Select the School Branch / Campus before authoring a school CBT Question."), frappe.ValidationError)
    if not offering:
        frappe.throw(
            _("Select the Class / Programme Offering so EduEdge can verify the exact Instructor Assignment before authoring this CBT Question."),
            frappe.ValidationError,
        )
    if not course:
        frappe.throw(_("Select the Subject / Course before authoring this CBT Question."), frappe.ValidationError)

    require_instructor_assignment_capability(
        "can_author_cbt",
        user=user,
        school_branch=branch,
        program_offering=offering,
        student_group=student_group,
        course=course,
    )
