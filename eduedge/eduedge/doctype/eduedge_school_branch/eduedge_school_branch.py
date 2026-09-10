from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

from eduedge.education.custom_fields import BRANCH_FIELD

COST_CENTER_FIELDS = (
	"cost_center",
	"default_income_cost_center",
	"default_expense_cost_center",
)

ACCOUNT_RULES = {
	"school_fees_income_account": {"root_types": {"Income"}},
	"cbt_exam_fees_income_account": {"root_types": {"Income"}},
	"admission_registration_income_account": {"root_types": {"Income"}},
	"transport_fees_income_account": {"root_types": {"Income"}},
	"hostel_boarding_income_account": {"root_types": {"Income"}},
	"books_materials_income_account": {"root_types": {"Income"}},
	"uniform_sales_income_account": {"root_types": {"Income"}},
	"other_income_account": {"root_types": {"Income"}},
	"default_receivable_account": {"account_types": {"Receivable"}},
	"default_cash_account": {"account_types": {"Cash"}},
	"default_bank_account": {"account_types": {"Bank"}},
	"default_payment_gateway_account": {"account_types": {"Bank", "Cash"}},
	"default_discount_account": {"root_types": {"Expense"}},
	"default_scholarship_bursary_account": {"root_types": {"Expense"}},
	"default_write_off_account": {"root_types": {"Expense"}},
	"default_inventory_account": {"account_types": {"Stock"}},
	"default_cost_of_goods_sold_account": {"root_types": {"Expense"}},
	"default_stock_adjustment_account": {"root_types": {"Expense"}},
}

LINKED_BRANCH_DOCTYPES = (
	("Student", BRANCH_FIELD),
	("Student Applicant", BRANCH_FIELD),
	("Program Enrollment", BRANCH_FIELD),
	("Student Group", BRANCH_FIELD),
	("Course Schedule", BRANCH_FIELD),
	("Assessment Plan", BRANCH_FIELD),
	("EduEdge Program Offering", "school_branch"),
	("EduEdge User Branch Access", "school_branch"),
)


class EduEdgeSchoolBranch(Document):
	def before_naming(self) -> None:
		self.branch_code = _normalize_branch_code(self.branch_code)

	def before_validate(self) -> None:
		self.branch_code = _normalize_branch_code(self.branch_code)
		self._derive_institution_context()
		if (self.is_default or self.is_main_branch) and not self.enabled:
			frappe.throw(_("A default or main School Branch must be enabled."), frappe.ValidationError)

	def validate(self) -> None:
		self._validate_company()
		self._validate_company_change()
		self._validate_institution()
		self._validate_contact_details()
		self._validate_cost_centers()
		self._validate_accounts()
		self._validate_warehouse()

	def on_update(self) -> None:
		for fieldname in ("is_default", "is_main_branch"):
			if not self.get(fieldname):
				continue
			frappe.db.set_value(
				"EduEdge School Branch",
				{
					"institution": self.institution,
					fieldname: 1,
					"name": ["!=", self.name],
				},
				fieldname,
				0,
				update_modified=False,
			)

	def _derive_institution_context(self) -> None:
		if not self.institution:
			return
		institution = frappe.db.get_value(
			"EduEdge Institution",
			self.institution,
			["company", "institution_type", "enabled"],
			as_dict=True,
		)
		if not institution or not institution.enabled:
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
		if self.company and self.company != institution.company:
			frappe.throw(_("School Branch and Institution must belong to the same Company."), frappe.ValidationError)
		self.company = institution.company
		self.institution_type = institution.institution_type

	def _validate_company(self) -> None:
		if frappe.db.get_value("Company", self.company, "is_group") == 1:
			frappe.throw(_("A group Company cannot be used as a school branch company."))

	def _validate_company_change(self) -> None:
		if self.is_new() or not self.has_value_changed("company"):
			return
		if self._has_linked_records():
			frappe.throw(
				_("Company cannot change after branch-linked education or access records exist."),
				frappe.ValidationError,
			)

	def _validate_institution(self) -> None:
		if not self.institution:
			frappe.throw(_("Institution is required for every EduEdge School Branch."), frappe.ValidationError)
		institution = frappe.db.get_value(
			"EduEdge Institution",
			self.institution,
			["company", "institution_type", "enabled"],
			as_dict=True,
		)
		if not institution or not institution.enabled:
			frappe.throw(_("Select an enabled Institution."), frappe.ValidationError)
		if institution.company != self.company:
			frappe.throw(_("School Branch and Institution must belong to the same Company."), frappe.ValidationError)
		if institution.institution_type != self.institution_type:
			frappe.throw(_("Institution Type must be inherited from the selected Institution."), frappe.ValidationError)

	def _has_linked_records(self) -> bool:
		for doctype, fieldname in LINKED_BRANCH_DOCTYPES:
			if not frappe.db.exists("DocType", doctype):
				continue
			try:
				if not frappe.get_meta(doctype).has_field(fieldname):
					continue
			except frappe.DoesNotExistError:
				continue
			if frappe.db.exists(doctype, {fieldname: self.name}):
				return True
		return False

	def _validate_contact_details(self) -> None:
		if self.email and not validate_email_address(self.email):
			frappe.throw(_("Enter a valid branch email address."), frappe.ValidationError)

	def _validate_cost_centers(self) -> None:
		for fieldname in COST_CENTER_FIELDS:
			value = self.get(fieldname)
			if not value:
				continue
			row = frappe.db.get_value(
				"Cost Center",
				value,
				["company", "is_group", "disabled"],
				as_dict=True,
			)
			if not row or row.company != self.company:
				frappe.throw(_("{0} must belong to Company {1}.").format(self.meta.get_label(fieldname), self.company))
			if row.is_group or row.disabled:
				frappe.throw(_("{0} must be an enabled ledger Cost Center.").format(self.meta.get_label(fieldname)))

	def _validate_accounts(self) -> None:
		for fieldname, rule in ACCOUNT_RULES.items():
			value = self.get(fieldname)
			if not value:
				continue
			account = frappe.db.get_value(
				"Account",
				value,
				["company", "is_group", "disabled", "root_type", "account_type"],
				as_dict=True,
			)
			label = self.meta.get_label(fieldname)
			if not account or account.company != self.company:
				frappe.throw(_("{0} must belong to Company {1}.").format(label, self.company))
			if account.is_group or account.disabled:
				frappe.throw(_("{0} must be an enabled ledger Account.").format(label))
			root_types = rule.get("root_types")
			if root_types and account.root_type not in root_types:
				frappe.throw(_("{0} must be a {1} account.").format(label, "/".join(sorted(root_types))))
			account_types = rule.get("account_types")
			if account_types and account.account_type not in account_types:
				frappe.throw(
					_("{0} must use Account Type {1}.").format(label, "/".join(sorted(account_types)))
				)

	def _validate_warehouse(self) -> None:
		if not self.default_warehouse:
			return
		row = frappe.db.get_value(
			"Warehouse",
			self.default_warehouse,
			["company", "is_group", "disabled"],
			as_dict=True,
		)
		if not row or row.company != self.company:
			frappe.throw(_("Default Warehouse must belong to Company {0}.").format(self.company))
		if row.is_group or row.disabled:
			frappe.throw(_("Default Warehouse must be an enabled ledger Warehouse."))


def _normalize_branch_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Branch Code is required."))
	return code
