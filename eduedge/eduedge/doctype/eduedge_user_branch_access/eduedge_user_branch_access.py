from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from eduedge.services.branch_context import (
	ASSIGNMENT_SCOPE_BRANCH,
	ASSIGNMENT_SCOPE_COMPANY,
	ASSIGNMENT_SCOPE_INSTITUTION,
	ASSIGNMENT_SCOPES,
	clear_school_branch,
	invalidate_user_branch_context,
)


class EduEdgeUserBranchAccess(Document):
	def before_validate(self) -> None:
		self._normalise_scope()

	def validate(self) -> None:
		self._validate_user()
		self._validate_scope()
		self._validate_dates()
		self._validate_duplicate()

	def on_update(self) -> None:
		if self.access_scope == ASSIGNMENT_SCOPE_BRANCH and self.is_default_branch:
			frappe.db.set_value(
				"EduEdge User Branch Access",
				{
					"user": self.user,
					"is_default_branch": 1,
					"name": ["!=", self.name],
				},
				"is_default_branch",
				0,
				update_modified=False,
			)
		invalidate_user_branch_context(self.user)

	def on_trash(self) -> None:
		clear_school_branch(user=self.user)

	def _normalise_scope(self) -> None:
		if self.access_scope not in ASSIGNMENT_SCOPES:
			if self.hq_all_branch_access:
				self.access_scope = ASSIGNMENT_SCOPE_COMPANY
			elif self.institution and not self.school_branch:
				self.access_scope = ASSIGNMENT_SCOPE_INSTITUTION
			else:
				self.access_scope = ASSIGNMENT_SCOPE_BRANCH

		if self.access_scope == ASSIGNMENT_SCOPE_COMPANY:
			self.hq_all_branch_access = 1
			self.institution = None
			self.school_branch = None
			self.branch_name = None
			self.is_default_branch = 0
			self.can_switch_branch = 1
			return

		self.hq_all_branch_access = 0
		if self.access_scope == ASSIGNMENT_SCOPE_INSTITUTION:
			self.school_branch = None
			self.branch_name = None
			self.is_default_branch = 0
			self.can_switch_branch = 1
			if self.institution:
				self.company = frappe.db.get_value("EduEdge Institution", self.institution, "company")
			return

		if self.school_branch:
			branch = frappe.db.get_value(
				"EduEdge School Branch",
				self.school_branch,
				["branch_name", "company", "institution"],
				as_dict=True,
			)
			if branch:
				self.branch_name = branch.branch_name
				self.company = branch.company
				self.institution = branch.institution

	def _validate_user(self) -> None:
		if not self.user or self.user == "Guest":
			frappe.throw(_("Select a valid System User."), frappe.ValidationError)
		if self.enabled and not frappe.db.get_value("User", self.user, "enabled"):
			frappe.throw(_("Access cannot be enabled for a disabled User."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.access_scope not in ASSIGNMENT_SCOPES:
			frappe.throw(_("Select Company, Institution, or Branch access."), frappe.ValidationError)
		if not self.company:
			frappe.throw(_("Company is required for every access assignment."), frappe.ValidationError)
		if frappe.db.get_value("Company", self.company, "is_group"):
			frappe.throw(_("Access assignments cannot use a group Company."), frappe.ValidationError)

		if self.access_scope == ASSIGNMENT_SCOPE_COMPANY:
			return

		if not self.institution:
			frappe.throw(_("Institution is required for this access level."), frappe.ValidationError)
		institution = frappe.db.get_value(
			"EduEdge Institution",
			self.institution,
			["company", "enabled"],
			as_dict=True,
		)
		if not institution:
			frappe.throw(_("Selected Institution does not exist."), frappe.ValidationError)
		if self.enabled and not institution.enabled:
			frappe.throw(_("Enable the Institution before enabling this access record."), frappe.ValidationError)
		if self.company != institution.company:
			frappe.throw(_("Access Company must match the selected Institution."), frappe.ValidationError)

		if self.access_scope == ASSIGNMENT_SCOPE_INSTITUTION:
			return

		if not self.school_branch:
			frappe.throw(_("School Branch / Campus is required for Branch access."), frappe.ValidationError)
		branch = frappe.db.get_value(
			"EduEdge School Branch",
			self.school_branch,
			["company", "institution", "enabled"],
			as_dict=True,
		)
		if not branch:
			frappe.throw(_("Selected School Branch / Campus does not exist."), frappe.ValidationError)
		if self.enabled and not branch.enabled:
			frappe.throw(_("Enable the School Branch before enabling this access record."), frappe.ValidationError)
		if self.company != branch.company or self.institution != branch.institution:
			frappe.throw(
				_("Branch access Company and Institution must match the selected School Branch."),
				frappe.ValidationError,
			)

	def _validate_dates(self) -> None:
		if self.valid_from and self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be earlier than Valid From."), frappe.ValidationError)

	def _validate_duplicate(self) -> None:
		filters = {
			"name": ["!=", self.name],
			"user": self.user,
			"access_scope": self.access_scope,
		}
		if self.access_scope == ASSIGNMENT_SCOPE_COMPANY:
			filters["company"] = self.company
		elif self.access_scope == ASSIGNMENT_SCOPE_INSTITUTION:
			filters["institution"] = self.institution
		else:
			filters["school_branch"] = self.school_branch
		duplicate = frappe.db.exists("EduEdge User Branch Access", filters)
		if duplicate:
			frappe.throw(
				_("User Access Assignment {0} already covers this user and scope.").format(duplicate),
				frappe.DuplicateEntryError,
			)
