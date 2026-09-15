from __future__ import annotations

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

RESULT_ENGINE_CUSTOM_FIELDS = {
	"Grading Scale Interval": [
		{
			"fieldname": "eduedge_report_remark",
			"fieldtype": "Data",
			"label": "EduEdge Report Remark",
			"insert_after": "threshold",
			"description": "Optional human-readable report remark for this grade interval, for example Excellent or Very Good.",
		},
	],
	"Academic Term": [
		{
			"fieldname": "eduedge_report_label",
			"fieldtype": "Data",
			"label": "EduEdge Report Label",
			"insert_after": "term_name",
			"description": "Optional Institution-facing term label for reports, for example Alpha, Rapha, Omega, First Term or Semester 1.",
		},
		{
			"fieldname": "eduedge_annual_weight",
			"fieldtype": "Percent",
			"label": "EduEdge Annual Result Weight",
			"insert_after": "eduedge_report_label",
			"description": "Optional weight used only when the selected Result Profile uses Weighted Average annual aggregation.",
		},
	],
	"Assessment Result": [
		{
			"fieldname": "eduedge_score_state",
			"fieldtype": "Select",
			"label": "EduEdge Score State",
			"options": "Scored\nAbsent\nExempt\nNot Offered",
			"default": "Scored",
			"insert_after": "total_score",
			"description": "Separates a genuine numeric zero from absence, exemption or a subject not offered. Missing and pending results remain represented by missing/draft Assessment Results.",
		},
	],
}


def ensure_result_engine_custom_fields() -> None:
	create_custom_fields(RESULT_ENGINE_CUSTOM_FIELDS, update=True)
