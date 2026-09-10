from __future__ import annotations

import frappe

from eduedge.education.custom_fields import BRANCH_FIELD


def ensure_program_enrollment_branch_selector() -> None:
	custom_field = frappe.db.get_value(
		"Custom Field",
		{"dt": "Program Enrollment", "fieldname": BRANCH_FIELD},
		"name",
	)
	if not custom_field:
		return
	frappe.db.set_value(
		"Custom Field",
		custom_field,
		{
			"read_only": 0,
			"description": "Select the target Branch before choosing a Programme Offering. Once selected, the Offering becomes authoritative.",
		},
		update_modified=False,
	)
	frappe.clear_cache(doctype="Program Enrollment")
