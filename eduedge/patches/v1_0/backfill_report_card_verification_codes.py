from __future__ import annotations

import frappe

from eduedge.education.report_card_issues import (
	ISSUE_DOCTYPE,
	generate_verification_code,
)


def execute():
	if not frappe.db.exists("DocType", ISSUE_DOCTYPE):
		return
	meta = frappe.get_meta(ISSUE_DOCTYPE)
	if not meta.has_field("verification_code"):
		return

	rows = frappe.get_all(
		ISSUE_DOCTYPE,
		filters={"verification_code": ["is", "not set"]},
		pluck="name",
		page_length=0,
	)
	for name in rows:
		frappe.db.set_value(
			ISSUE_DOCTYPE,
			name,
			"verification_code",
			generate_verification_code(),
			update_modified=False,
		)
