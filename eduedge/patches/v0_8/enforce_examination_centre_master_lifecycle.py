from __future__ import annotations

import frappe


DOCTYPE = "EduEdge Examination Centre"


def execute() -> None:
	if frappe.db.exists("DocType", DOCTYPE):
		# Be explicit because an earlier development schema exposed Submit. The
		# centre lifecycle is governed by centre_status, never Frappe docstatus.
		frappe.db.set_value(
			"DocType",
			DOCTYPE,
			"is_submittable",
			0,
			update_modified=False,
		)

	if not frappe.db.table_exists(DOCTYPE):
		return

	# V0.8A is still in controlled QA. Repair any centre accidentally submitted
	# while the stale metadata was present so it returns to the intended editable
	# master-record lifecycle. This does not touch accounting or academic results.
	frappe.db.sql(
		"""
		UPDATE `tabEduEdge Examination Centre`
		SET `docstatus` = 0
		WHERE `docstatus` != 0
		"""
	)
