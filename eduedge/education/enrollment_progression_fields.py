from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PROGRESSION_SOURCE_FIELD = "eduedge_progression_source_enrollment"
PROGRESSION_OUTCOME_FIELD = "eduedge_progression_outcome"
PROGRESSION_REASON_FIELD = "eduedge_progression_reason"

PROGRESSION_FIELDS = {
	"Program Enrollment": [
		{
			"fieldname": "eduedge_progression_section",
			"fieldtype": "Section Break",
			"label": "Progression Plan",
			"insert_after": "eduedge_program_offering",
			"collapsible": 1,
			"depends_on": f"eval:doc.{PROGRESSION_SOURCE_FIELD}",
		},
		{
			"fieldname": PROGRESSION_SOURCE_FIELD,
			"fieldtype": "Link",
			"label": "Source Program Enrollment",
			"options": "Program Enrollment",
			"read_only": 1,
			"no_copy": 1,
			"in_standard_filter": 1,
			"description": "Submitted historical enrollment from which this draft promotion, repetition or transfer was created.",
		},
		{
			"fieldname": PROGRESSION_OUTCOME_FIELD,
			"fieldtype": "Select",
			"label": "Planned Outcome",
			"options": "\nPromote\nRepeat\nTransfer",
			"read_only": 1,
			"no_copy": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": PROGRESSION_REASON_FIELD,
			"fieldtype": "Small Text",
			"label": "Progression Reason / Note",
			"read_only": 1,
			"no_copy": 1,
		},
	],
}


def ensure_enrollment_progression_fields() -> None:
	if not frappe.db.exists("DocType", "Program Enrollment"):
		return
	create_custom_fields(PROGRESSION_FIELDS, update=True)
	frappe.clear_cache(doctype="Program Enrollment")
