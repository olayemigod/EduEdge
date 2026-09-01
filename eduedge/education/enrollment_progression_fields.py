from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PROGRESSION_SOURCE_FIELD = "eduedge_progression_source_enrollment"
PROGRESSION_OUTCOME_FIELD = "eduedge_progression_outcome"
PROGRESSION_REASON_FIELD = "eduedge_progression_reason"
PROGRESSION_TARGET_GROUP_FIELD = "eduedge_progression_target_student_group"
PROGRESSION_RECOMMENDATION_FIELD = "eduedge_progression_recommendation"
PROGRESSION_EVIDENCE_FIELD = "eduedge_progression_evidence_snapshot"

PROGRESSION_FIELDS = {
	"Program Enrollment": [
		{
			"fieldname": "eduedge_progression_plan_section",
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
		},
		{
			"fieldname": PROGRESSION_OUTCOME_FIELD,
			"fieldtype": "Select",
			"label": "Planned Progression Outcome",
			"options": "\nPromote\nRepeat\nTransfer",
			"read_only": 1,
			"no_copy": 1,
			"in_standard_filter": 1,
		},
		{
			"fieldname": PROGRESSION_TARGET_GROUP_FIELD,
			"fieldtype": "Link",
			"label": "Planned Destination Class Arm / Group",
			"options": "Student Group",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": PROGRESSION_REASON_FIELD,
			"fieldtype": "Small Text",
			"label": "Progression Reason / Note",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": PROGRESSION_RECOMMENDATION_FIELD,
			"fieldtype": "Data",
			"label": "Progression Recommendation Snapshot",
			"read_only": 1,
			"no_copy": 1,
		},
		{
			"fieldname": PROGRESSION_EVIDENCE_FIELD,
			"fieldtype": "Long Text",
			"label": "Progression Evidence Snapshot",
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
