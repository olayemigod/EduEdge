from __future__ import annotations

import frappe

from eduedge.api.report_verification import verify_report_card

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = True
	context.show_sidebar = False
	context.title = "Verify Result"
	code = str(frappe.form_dict.get("code") or "").strip()
	context.code = code
	context.verification = verify_report_card(code) if code else None
	return context
