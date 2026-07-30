from __future__ import annotations

import frappe

from eduedge.api import academic_foundation_safe as base
from eduedge.api.native_display import annotate_master_rows


@frappe.whitelist()
def get_academic_foundation(institution: str | None = None) -> dict:
	payload = base.get_academic_foundation(institution=institution)
	annotate_master_rows(payload.get("departments") or [], "Department", "department_name")
	annotate_master_rows(payload.get("programmes") or [], "Program", "program_name")
	annotate_master_rows(payload.get("student_groups") or [], "Student Group", "student_group_name")
	payload["hierarchy"] = base._build_hierarchy(
		payload.get("departments") or [],
		payload.get("programmes") or [],
		payload.get("student_groups") or [],
	)
	return payload
