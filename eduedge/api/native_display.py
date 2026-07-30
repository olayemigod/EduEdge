from __future__ import annotations

import frappe

from eduedge.education.native_identity import DISPLAY_FIELD

MASTER_SOURCES = {
	"Department": "department_name",
	"Program": "program_name",
	"Course": "course_name",
	"Student Group": "student_group_name",
	"Student Batch Name": "batch_name",
}


def label_map(doctype: str, names: list[str] | set[str] | tuple[str, ...]) -> dict[str, str]:
	resolved = sorted({str(name) for name in names if name})
	if not resolved or not frappe.db.exists("DocType", doctype):
		return {}
	meta = frappe.get_meta(doctype)
	source = MASTER_SOURCES.get(doctype, "name")
	fields = ["name"]
	if meta.has_field(source) and source != "name":
		fields.append(source)
	if meta.has_field(DISPLAY_FIELD):
		fields.append(DISPLAY_FIELD)
	rows = frappe.get_all(doctype, filters={"name": ["in", resolved]}, fields=fields, page_length=len(resolved))
	return {
		row.name: str(row.get(DISPLAY_FIELD) or row.get(source) or row.name)
		for row in rows
	}


def annotate_master_rows(rows: list[dict], doctype: str, source_field: str) -> None:
	labels = label_map(doctype, [row.get("name") for row in rows])
	for row in rows:
		technical = row.get(source_field) or row.get("name")
		row["technical_name"] = technical
		row["display_name"] = labels.get(row.get("name")) or technical
		row[source_field] = row["display_name"]


def annotate_link(rows: list[dict], fieldname: str, doctype: str, output_field: str) -> None:
	labels = label_map(doctype, [row.get(fieldname) for row in rows])
	for row in rows:
		row[output_field] = labels.get(row.get(fieldname)) or row.get(fieldname) or ""
