from __future__ import annotations

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


RESULT_SYNC_CUSTOM_FIELDS = {
	"Assessment Result": [
		{
			"fieldname": "eduedge_cbt_source_section",
			"fieldtype": "Section Break",
			"label": "EduEdge CBT Source",
			"insert_after": "comment",
			"collapsible": 1,
		},
		{
			"fieldname": "eduedge_cbt_result",
			"fieldtype": "Link",
			"label": "Source CBT Result",
			"options": "EduEdge CBT Result",
			"insert_after": "eduedge_cbt_source_section",
			"read_only": 1,
			"no_copy": 1,
			"unique": 1,
			"in_standard_filter": 1,
			"description": "Approved EduEdge CBT Result used to prepare this academic result.",
		},
		{
			"fieldname": "eduedge_cbt_exam_schedule",
			"fieldtype": "Link",
			"label": "CBT Examination Schedule",
			"options": "EduEdge CBT Exam Schedule",
			"insert_after": "eduedge_cbt_result",
			"read_only": 1,
			"no_copy": 1,
			"in_standard_filter": 1,
		},
	]
}


def ensure_result_sync_custom_fields() -> None:
	"""Install traceable CBT source links without modifying Frappe Education schemas."""
	create_custom_fields(RESULT_SYNC_CUSTOM_FIELDS, update=True)
