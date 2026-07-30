from __future__ import annotations

import frappe

from eduedge.api import programme_offerings_safe as base
from eduedge.api.native_display import annotate_link, annotate_master_rows


@frappe.whitelist()
def get_programme_offerings_page(**kwargs) -> dict:
	payload = base.get_programme_offerings_page(**kwargs)
	_annotate_payload(payload)
	return payload


@frappe.whitelist()
def get_programme_offering_options(branch: str | None = None, academic_year: str | None = None) -> dict:
	payload = base.get_programme_offering_options(branch=branch, academic_year=academic_year)
	_annotate_options(payload.get("options") or {})
	return payload


def _annotate_payload(payload: dict) -> None:
	options = payload.get("options") or {}
	_annotate_options(options)
	offerings = payload.get("offerings") or []
	annotate_link(offerings, "program", "Program", "program_display_name")
	annotate_link(offerings, "department", "Department", "department_display_name")
	annotate_link(offerings, "student_batch", "Student Batch Name", "student_batch_display_name")


def _annotate_options(options: dict) -> None:
	annotate_master_rows(options.get("programmes") or [], "Program", "program_name")
	annotate_master_rows(options.get("departments") or [], "Department", "department_name")
	batches = options.get("student_batches") or []
	labels = {
		row.name: row
		for row in frappe.get_all(
			"Student Batch Name",
			filters={"name": ["in", [row.get("name") for row in batches if row.get("name")]]},
			fields=["name", "eduedge_display_name"],
			page_length=max(len(batches), 1),
		)
	} if batches else {}
	for row in batches:
		row["display_name"] = (labels.get(row.get("name")) or {}).get("eduedge_display_name") or row.get("name") or ""
