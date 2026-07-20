from __future__ import annotations

import frappe
from frappe import _

from eduedge.services.branch_accounting import (
	get_branch_accounting_defaults as _get_branch_accounting_defaults,
	resolve_transaction_defaults as _resolve_transaction_defaults,
)

ACCOUNTING_VIEW_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Bursar",
}


def _require_accounting_access() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required."), frappe.PermissionError)
	if not ACCOUNTING_VIEW_ROLES.intersection(frappe.get_roles(frappe.session.user)):
		frappe.throw(_("You are not permitted to view branch accounting defaults."), frappe.PermissionError)


@frappe.whitelist()
def get_branch_accounting_defaults(branch: str, company: str | None = None) -> dict:
	_require_accounting_access()
	return _get_branch_accounting_defaults(branch, company=company)


@frappe.whitelist()
def resolve_transaction_defaults(
	branch: str,
	purpose: str,
	payment_channel: str | None = None,
	company: str | None = None,
) -> dict:
	_require_accounting_access()
	return _resolve_transaction_defaults(
		branch,
		purpose=purpose,
		payment_channel=payment_channel,
		company=company,
	)
