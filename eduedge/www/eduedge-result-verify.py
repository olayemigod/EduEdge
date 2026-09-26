from __future__ import annotations

import frappe

from eduedge.education.result_verification import verify_issued_report_card

no_cache = 1


def get_context(context):
	frappe.local.no_cache = 1
	context.no_cache = 1
	context.no_breadcrumbs = True
	context.show_sidebar = False
	context.title = "Verify Result"
	context.verification = verify_issued_report_card(
		frappe.form_dict.get("issue"),
		frappe.form_dict.get("token"),
	)
	return context
