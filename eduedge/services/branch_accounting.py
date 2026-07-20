from __future__ import annotations

import frappe
from frappe import _

from eduedge.services.branch_context import get_allowed_school_branches

ACCOUNTING_FIELDS = [
	"company",
	"cost_center",
	"default_income_cost_center",
	"default_expense_cost_center",
	"school_fees_income_account",
	"cbt_exam_fees_income_account",
	"admission_registration_income_account",
	"transport_fees_income_account",
	"hostel_boarding_income_account",
	"books_materials_income_account",
	"uniform_sales_income_account",
	"other_income_account",
	"default_receivable_account",
	"default_cash_account",
	"default_bank_account",
	"default_payment_gateway_account",
	"default_discount_account",
	"default_scholarship_bursary_account",
	"default_write_off_account",
	"default_warehouse",
	"default_inventory_account",
	"default_cost_of_goods_sold_account",
	"default_stock_adjustment_account",
]

INCOME_PURPOSE_FIELD = {
	"school_fees": "school_fees_income_account",
	"cbt_exam": "cbt_exam_fees_income_account",
	"admission_registration": "admission_registration_income_account",
	"transport": "transport_fees_income_account",
	"hostel_boarding": "hostel_boarding_income_account",
	"books_materials": "books_materials_income_account",
	"uniform_sales": "uniform_sales_income_account",
	"other_income": "other_income_account",
}


def get_branch_accounting_defaults(
	branch: str,
	*,
	company: str | None = None,
	check_access: bool = True,
) -> dict:
	if not branch:
		frappe.throw(_("School Branch / Campus is required."), frappe.ValidationError)
	if check_access and not _has_branch_access(branch):
		frappe.throw(_("You do not have access to the selected School Branch."), frappe.PermissionError)
	meta = frappe.get_meta("EduEdge School Branch")
	missing_schema = [fieldname for fieldname in ACCOUNTING_FIELDS if not meta.has_field(fieldname)]
	if missing_schema:
		frappe.throw(_("Run EduEdge migration before using branch accounting defaults."), frappe.ValidationError)
	row = frappe.db.get_value(
		"EduEdge School Branch",
		branch,
		["name", "branch_name", "enabled", *ACCOUNTING_FIELDS],
		as_dict=True,
	)
	if not row or not row.enabled:
		frappe.throw(_("Select an enabled School Branch / Campus."), frappe.ValidationError)
	if company and row.company != company:
		frappe.throw(
			_("School Branch {0} does not belong to Company {1}.").format(branch, company),
			frappe.ValidationError,
		)
	result = dict(row)
	result["missing_core_defaults"] = get_missing_core_defaults(result)
	result["core_accounting_ready"] = not result["missing_core_defaults"]
	return result


def get_missing_core_defaults(defaults: dict) -> list[str]:
	missing = []
	for fieldname in ("cost_center", "school_fees_income_account", "default_receivable_account"):
		if not defaults.get(fieldname):
			missing.append(fieldname)
	if not any(
		defaults.get(fieldname)
		for fieldname in ("default_cash_account", "default_bank_account", "default_payment_gateway_account")
	):
		missing.append("default_cash_or_bank_account")
	return missing


def resolve_transaction_defaults(
	branch: str,
	*,
	purpose: str,
	payment_channel: str | None = None,
	company: str | None = None,
) -> dict:
	if purpose not in INCOME_PURPOSE_FIELD:
		frappe.throw(_("Unsupported EduEdge accounting purpose: {0}").format(purpose), frappe.ValidationError)
	defaults = get_branch_accounting_defaults(branch, company=company)
	income_account = defaults.get(INCOME_PURPOSE_FIELD[purpose]) or defaults.get("other_income_account")
	cost_center = defaults.get("default_income_cost_center") or defaults.get("cost_center")
	payment_account = _resolve_payment_account(defaults, payment_channel)
	return {
		"branch": branch,
		"company": defaults.get("company"),
		"purpose": purpose,
		"income_account": income_account,
		"cost_center": cost_center,
		"receivable_account": defaults.get("default_receivable_account"),
		"payment_account": payment_account,
		"warehouse": defaults.get("default_warehouse"),
		"inventory_account": defaults.get("default_inventory_account"),
		"cost_of_goods_sold_account": defaults.get("default_cost_of_goods_sold_account"),
		"stock_adjustment_account": defaults.get("default_stock_adjustment_account"),
		"discount_account": defaults.get("default_discount_account"),
		"scholarship_bursary_account": defaults.get("default_scholarship_bursary_account"),
		"write_off_account": defaults.get("default_write_off_account"),
		"missing_core_defaults": defaults.get("missing_core_defaults"),
	}


def _resolve_payment_account(defaults: dict, payment_channel: str | None) -> str | None:
	fieldname = {
		"cash": "default_cash_account",
		"bank": "default_bank_account",
		"gateway": "default_payment_gateway_account",
		"mobile_money": "default_payment_gateway_account",
	}.get((payment_channel or "").strip().lower())
	if fieldname:
		return defaults.get(fieldname)
	return (
		defaults.get("default_payment_gateway_account")
		or defaults.get("default_bank_account")
		or defaults.get("default_cash_account")
	)


def _has_branch_access(branch: str) -> bool:
	if frappe.session.user == "Administrator":
		return True
	roles = set(frappe.get_roles(frappe.session.user))
	if roles.intersection({"System Manager", "EduEdge Administrator"}):
		return True
	return branch in {row["name"] for row in get_allowed_school_branches()}
