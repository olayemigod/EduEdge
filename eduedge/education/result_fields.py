from __future__ import annotations

import frappe
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


def backfill_result_score_states() -> None:
	"""Normalize legacy blank score states to the runtime-compatible Scored value."""
	if not frappe.db.table_exists("Assessment Result"):
		return
	if not frappe.get_meta("Assessment Result").has_field("eduedge_score_state"):
		return

	assessment_result = frappe.qb.DocType("Assessment Result")
	(
		frappe.qb.update(assessment_result)
		.set(assessment_result.eduedge_score_state, "Scored")
		.where(
			assessment_result.eduedge_score_state.isnull()
			| (assessment_result.eduedge_score_state == "")
		)
	).run()


def ensure_result_engine_custom_fields() -> None:
	create_custom_fields(RESULT_ENGINE_CUSTOM_FIELDS, update=True)
	backfill_result_score_states()
