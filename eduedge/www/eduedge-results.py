from __future__ import annotations

import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = True
	context.show_sidebar = False
	context.title = "My Results"

	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/eduedge-results"
		raise frappe.Redirect

	return context
