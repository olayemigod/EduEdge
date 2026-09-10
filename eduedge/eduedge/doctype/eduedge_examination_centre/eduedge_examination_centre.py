from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from eduedge.cbt.public_access import require_public_exam_authoring
from eduedge.education.offerings import assert_branch_access

SCHOOL_CENTRE = "School Examination Centre"
PLATFORM_CENTRE = "EduEdge Exam Centre"
CENTRE_GOVERNANCE_ROLES = {
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
}
ALLOWED_STATUS_TRANSITIONS = {
	"Draft": {"Draft", "Active"},
	"Active": {"Active", "Suspended", "Retired"},
	"Suspended": {"Suspended", "Active", "Retired"},
	"Retired": {"Retired"},
}
PUBLIC_HOSTING_STATUSES = {"Not Requested", "Pending", "Approved", "Suspended", "Revoked"}


class EduEdgeExaminationCentre(Document):
	def autoname(self) -> None:
		self.centre_code = (self.centre_code or "").strip().upper()
		if self.centre_code:
			self.name = self.centre_code

	def validate(self) -> None:
		self._validate_master_docstatus()
		self.centre_code = (self.centre_code or "").strip().upper()
		self.centre_name = (self.centre_name or "").strip()
		self._validate_identity()
		self._validate_scope()
		self._validate_capacity()
		self._validate_public_hosting_state()
		self._validate_status_transition()
		self.enabled = 1 if self.centre_status == "Active" else 0

	def before_submit(self) -> None:
		self._throw_master_lifecycle_error()

	def before_cancel(self) -> None:
		self._throw_master_lifecycle_error()

	def on_trash(self) -> None:
		if self.centre_status != "Draft":
			frappe.throw(
				_("Only a Draft examination centre can be deleted. Suspend or retire an operational centre instead."),
				frappe.ValidationError,
			)
		if self.centre_type == PLATFORM_CENTRE:
			require_public_exam_authoring()

	def _validate_master_docstatus(self) -> None:
		if cint(self.docstatus) != 0:
			self._throw_master_lifecycle_error()

	def _throw_master_lifecycle_error(self) -> None:
		frappe.throw(
			_(
				"Examination Centres are non-submittable master records. "
				"Use Centre Status to activate, suspend, or retire a centre."
			),
			frappe.ValidationError,
			title=_("Use Centre Status"),
		)

	def _validate_identity(self) -> None:
		if not self.centre_code:
			frappe.throw(_("Centre Code is required."), frappe.ValidationError)
		if not self.centre_name:
			frappe.throw(_("Examination Centre Name is required."), frappe.ValidationError)

	def _validate_scope(self) -> None:
		if self.centre_type == SCHOOL_CENTRE:
			if not self.school_branch:
				frappe.throw(
					_("School Branch / Campus is required for a School Examination Centre."),
					frappe.ValidationError,
				)
			assert_branch_access(self.school_branch)
			self.allow_public_registration = 0
			return

		if self.centre_type == PLATFORM_CENTRE:
			require_public_exam_authoring()
			self.school_branch = None
			self.public_hosting_status = "Not Requested"
			self.public_centre_reference = None
			return

		frappe.throw(_("Select a valid Examination Centre Type."), frappe.ValidationError)

	def _validate_capacity(self) -> None:
		if cint(self.capacity) < 0:
			frappe.throw(_("Candidate Capacity cannot be negative."), frappe.ValidationError)

	def _validate_public_hosting_state(self) -> None:
		if self.centre_type != SCHOOL_CENTRE:
			return
		self.public_hosting_status = self.public_hosting_status or "Not Requested"
		if self.public_hosting_status not in PUBLIC_HOSTING_STATUSES:
			frappe.throw(_("Select a valid Public Exam Hosting Status."), frappe.ValidationError)

		before = self.get_doc_before_save()
		if not before:
			if self.public_hosting_status != "Not Requested" or self.public_centre_reference:
				require_public_exam_authoring()
			return

		previous_hosting_status = before.public_hosting_status or "Not Requested"
		previous_reference = (before.public_centre_reference or "").strip()
		current_reference = (self.public_centre_reference or "").strip()
		if previous_hosting_status != self.public_hosting_status or previous_reference != current_reference:
			# A future signed CoreEdge centre-verification sync may set this flag
			# after validating its payload. Ordinary local form/API writes must use
			# the same ProcessEdge authorisation gate.
			if not self.flags.get("from_public_exam_sync"):
				require_public_exam_authoring()

	def _validate_status_transition(self) -> None:
		before = self.get_doc_before_save()
		previous_status = before.centre_status if before else "Draft"
		previous_status = previous_status or ("Active" if before and cint(before.enabled) else "Draft")
		self.centre_status = self.centre_status or ("Active" if cint(self.enabled) else "Draft")
		allowed = ALLOWED_STATUS_TRANSITIONS.get(previous_status, {previous_status})
		if self.centre_status not in allowed:
			frappe.throw(
				_("Examination Centre Status cannot change from {0} to {1}.").format(
					previous_status, self.centre_status
				),
				frappe.ValidationError,
			)
		if self.centre_status == previous_status:
			return
		if self.centre_type == PLATFORM_CENTRE:
			require_public_exam_authoring()
		else:
			self._assert_school_centre_governance()
		self.status_changed_by = frappe.session.user
		self.status_changed_on = now_datetime()

	def _assert_school_centre_governance(self) -> None:
		if frappe.session.user == "Administrator":
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if not roles.intersection(CENTRE_GOVERNANCE_ROLES):
			frappe.throw(
				_("You are not permitted to activate, suspend, or retire an examination centre."),
				frappe.PermissionError,
			)
