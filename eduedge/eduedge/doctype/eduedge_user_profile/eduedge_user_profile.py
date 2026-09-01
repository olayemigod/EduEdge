from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.html_utils import sanitize_html


COMMUNICATION_CHANNELS = {"", "Email", "SMS", "WhatsApp", "Phone"}
TEXT_LIMITS = {
	"preferred_name": 140,
	"professional_title": 140,
	"whatsapp_number": 40,
	"address_line_1": 240,
	"address_line_2": 240,
	"city": 140,
	"state": 140,
	"postal_code": 40,
	"emergency_contact_name": 140,
	"emergency_contact_relationship": 100,
	"emergency_contact_phone": 40,
}


class EduEdgeUserProfile(Document):
	def before_validate(self) -> None:
		if not self.user and frappe.session.user not in {"", "Guest"}:
			self.user = frappe.session.user
		self._clean_values()

	def before_insert(self) -> None:
		self._assert_self_service_user()
		frappe.db.sql("select name from `tabUser` where name = %s for update", (self.user,))
		if frappe.db.exists("EduEdge User Profile", {"user": self.user}):
			frappe.throw(_("An EduEdge Profile already exists for this User."), frappe.DuplicateEntryError)

	def validate(self) -> None:
		self._assert_self_service_user()
		if not frappe.db.exists("User", self.user):
			frappe.throw(_("Select a valid User."), frappe.ValidationError)
		if not self.is_new() and self.has_value_changed("user"):
			frappe.throw(_("The Profile User cannot be changed after creation."), frappe.ValidationError)
		if self.preferred_communication not in COMMUNICATION_CHANNELS:
			frappe.throw(_("Select a valid preferred communication channel."), frappe.ValidationError)
		if self.country and not frappe.db.exists("Country", self.country):
			frappe.throw(_("Select a valid Country."), frappe.ValidationError)

	def _assert_self_service_user(self) -> None:
		if frappe.session.user == "Administrator":
			return
		if not frappe.session.user or frappe.session.user == "Guest" or self.user != frappe.session.user:
			frappe.throw(_("You can only maintain your own EduEdge Profile."), frappe.PermissionError)

	def _clean_values(self) -> None:
		for fieldname, limit in TEXT_LIMITS.items():
			value = sanitize_html(str(self.get(fieldname) or "").strip(), always_sanitize=True, disallowed_tags="*")
			if len(value) > limit:
				frappe.throw(
					_("{0} is longer than the allowed limit.").format(self.meta.get_label(fieldname)),
					frappe.ValidationError,
				)
			self.set(fieldname, value or None)
