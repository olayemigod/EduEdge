from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document


class EduEdgeSchoolBranch(Document):
	def before_naming(self) -> None:
		self.branch_code = _normalize_branch_code(self.branch_code)

	def before_validate(self) -> None:
		self.branch_code = _normalize_branch_code(self.branch_code)

	def validate(self) -> None:
		self._validate_company()
		self._validate_cost_center()
		self._validate_warehouse()

	def on_update(self) -> None:
		if self.is_default:
			frappe.db.set_value(
				"EduEdge School Branch",
				{
					"company": self.company,
					"is_default": 1,
					"name": ["!=", self.name],
				},
				"is_default",
				0,
				update_modified=False,
			)

	def _validate_company(self) -> None:
		if frappe.db.get_value("Company", self.company, "is_group") == 1:
			frappe.throw(_("A group Company cannot be used as a school branch company."))

	def _validate_cost_center(self) -> None:
		if not self.cost_center:
			return
		company = frappe.db.get_value("Cost Center", self.cost_center, "company")
		if company != self.company:
			frappe.throw(_("Cost Center must belong to Company {0}.").format(self.company))

	def _validate_warehouse(self) -> None:
		if not self.default_warehouse:
			return
		company = frappe.db.get_value("Warehouse", self.default_warehouse, "company")
		if company != self.company:
			frappe.throw(_("Default Warehouse must belong to Company {0}.").format(self.company))


def _normalize_branch_code(value: str | None) -> str:
	code = re.sub(r"[^A-Z0-9]+", "-", str(value or "").strip().upper()).strip("-")
	if not code:
		frappe.throw(_("Branch Code is required."))
	return code
