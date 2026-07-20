from __future__ import annotations

import frappe

from eduedge.services.setup_readiness import get_setup_readiness as _get_setup_readiness


@frappe.whitelist()
def get_setup_readiness() -> dict:
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required.", frappe.PermissionError)
	if not frappe.has_permission("EduEdge Settings", "read"):
		frappe.throw("You are not permitted to view EduEdge setup readiness.", frappe.PermissionError)
	return _get_setup_readiness()
