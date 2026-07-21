from __future__ import annotations

import frappe

CBT_MASTER_DOCTYPES = (
	"EduEdge CBT Question",
	"EduEdge CBT Exam Template",
)


def execute() -> None:
	for doctype in CBT_MASTER_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.db.set_value(
				"DocType",
				doctype,
				"is_submittable",
				0,
				update_modified=False,
			)

		if not frappe.db.table_exists(doctype):
			continue

		# V0.8A is still in controlled QA. Repair any master accidentally
		# submitted while stale metadata exposed Submit. These are configuration
		# records, not accounting documents or published academic results.
		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET `docstatus` = 0
			WHERE `docstatus` != 0
			"""
		)
