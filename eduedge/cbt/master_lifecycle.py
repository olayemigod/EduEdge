from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

CBT_MASTER_DOCTYPES = {
	"EduEdge CBT Question": "Question Status",
	"EduEdge CBT Exam Template": "Template Status",
}


def validate_master_docstatus(doc, method: str | None = None) -> None:
	if doc.doctype not in CBT_MASTER_DOCTYPES:
		return
	if cint(doc.docstatus) != 0:
		throw_master_lifecycle_error(doc)


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
