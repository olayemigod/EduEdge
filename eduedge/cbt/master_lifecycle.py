from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

CBT_MASTER_DOCTYPES = {
	"EduEdge CBT Question": "Question Status",
	"EduEdge CBT Exam Template": "Template Status",
}

DEVICE_CHANGE_POLICIES = {
	"Not Allowed",
	"Invigilator Approval Required",
	"Administrator Approval Required",
	"Allowed Before First Answer Only",
}
ATTEMPT_REVIEW_POLICIES = {
	"Review Flagged Attempts Only",
	"Review All Attempts",
	"No Pre-publication Review",
}


def validate_master_docstatus(doc, method: str | None = None) -> None:
	if doc.doctype not in CBT_MASTER_DOCTYPES:
		return
	if cint(doc.docstatus) != 0:
		throw_master_lifecycle_error(doc)
	if doc.doctype == "EduEdge CBT Question":
		from eduedge.cbt.assignment_capabilities import validate_question_authoring_capability
		from eduedge.cbt.question_governance import validate_question_governance_transition

		validate_question_governance_transition(doc)
		validate_question_authoring_capability(doc)
	if doc.doctype == "EduEdge CBT Exam Template":
		_validate_template_runtime_policies(doc)


def block_master_submit(doc, method: str | None = None) -> None:
	throw_master_lifecycle_error(doc)


def block_master_cancel(doc, method: str | None = None) -> None:
	throw_master_lifecycle_error(doc)


def throw_master_lifecycle_error(doc) -> None:
	status_field = CBT_MASTER_DOCTYPES.get(doc.doctype, _("Status"))
	frappe.throw(
		_(
			"{0} is a non-submittable master record. Use {1} for review, approval, and retirement."
		).format(_(doc.doctype), _(status_field)),
		frappe.ValidationError,
		title=_("Use Governance Status"),
	)


def _validate_template_runtime_policies(doc) -> None:
	if doc.device_change_policy not in DEVICE_CHANGE_POLICIES:
		frappe.throw(_("Select a valid Device Change Policy."), frappe.ValidationError)
	if doc.attempt_review_policy not in ATTEMPT_REVIEW_POLICIES:
		frappe.throw(_("Select a valid Attempt Review Policy."), frappe.ValidationError)
	before = doc.get_doc_before_save()
	if not before or before.status not in {"Approved", "Retired"}:
		return
	for fieldname in ("device_change_policy", "attempt_review_policy"):
		if before.get(fieldname) != doc.get(fieldname):
			frappe.throw(
				_("Approved exam template policies are immutable. Create a new template version instead."),
				frappe.ValidationError,
			)
