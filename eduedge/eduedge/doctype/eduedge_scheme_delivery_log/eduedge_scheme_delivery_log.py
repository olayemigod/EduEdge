from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

DELIVERY_ACTION_FLAG = "in_eduedge_scheme_delivery_action"
DELIVERY_STATUSES = {"Started", "Progress Update", "Completed", "Deferred", "Resumed"}
IMMUTABLE_FIELDS = (
	"scheme_of_work",
	"scheme_version",
	"scheme_item_reference",
	"scheme_item_sequence",
	"delivery_status",
	"delivered_on",
	"periods_delivered",
	"institution",
	"school_branch",
	"program_offering",
	"student_group",
	"course",
	"topic",
	"instructor",
	"instructor_assignment",
	"scheme_title_snapshot",
	"course_name_snapshot",
	"offering_title_snapshot",
	"student_group_name_snapshot",
	"topic_name_snapshot",
	"learning_objective_snapshot",
	"logged_by",
	"logged_on",
	"notes",
	"evidence",
)


class EduEdgeSchemeDeliveryLog(Document):
	def validate(self) -> None:
		if not getattr(frappe.flags, DELIVERY_ACTION_FLAG, False):
			frappe.throw(
				_("Scheme delivery history is append-only. Record progress through the Scheme of Work workbench."),
				frappe.PermissionError,
			)
		if self.delivery_status not in DELIVERY_STATUSES:
			frappe.throw(_("Select a valid Scheme delivery update."), frappe.ValidationError)
		if not self.delivered_on:
			frappe.throw(_("Delivery Date is required."), frappe.ValidationError)
		if flt(self.periods_delivered) < 0:
			frappe.throw(_("Periods Delivered cannot be negative."), frappe.ValidationError)
		if self.delivery_status in {"Started", "Progress Update", "Completed", "Resumed"} and flt(self.periods_delivered) <= 0:
			frappe.throw(_("Enter the number of periods delivered for this progress update."), frappe.ValidationError)
		self._validate_scheme_reference()
		self._protect_existing_log()

	def on_trash(self) -> None:
		frappe.throw(
			_("Scheme delivery logs are retained as append-only academic history and cannot be deleted."),
			frappe.PermissionError,
		)

	def _validate_scheme_reference(self) -> None:
		scheme = frappe.get_doc("EduEdge Scheme of Work", self.scheme_of_work)
		if scheme.status != "Approved":
			frappe.throw(_("Delivery updates can be recorded only against an Approved Scheme of Work."), frappe.ValidationError)
		item = next((row for row in scheme.get("items") or [] if row.name == self.scheme_item_reference), None)
		if not item:
			frappe.throw(_("Scheme Item Reference does not belong to the selected approved Scheme."), frappe.ValidationError)
		if str(self.topic or "") != str(item.topic or ""):
			frappe.throw(_("Delivery Topic must match the approved Scheme item."), frappe.ValidationError)
		if getdate(self.delivered_on) < getdate(scheme.period_start_date) or getdate(self.delivered_on) > getdate(scheme.period_end_date):
			frappe.throw(_("Delivery Date must fall within the Scheme academic period."), frappe.ValidationError)
		for fieldname in ("institution", "school_branch", "program_offering", "student_group", "course"):
			if str(self.get(fieldname) or "") != str(scheme.get(fieldname) or ""):
				frappe.throw(_("Scheme delivery academic context must match the approved Scheme snapshot."), frappe.ValidationError)

	def _protect_existing_log(self) -> None:
		before = self.get_doc_before_save()
		if not before:
			return
		for fieldname in IMMUTABLE_FIELDS:
			if str(before.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(_("Scheme delivery logs cannot be edited after creation. Record a new progress update instead."), frappe.ValidationError)
