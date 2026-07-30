from __future__ import annotations

import frappe

from eduedge.api import programmes as base
from eduedge.api.native_display import annotate_master_rows


@frappe.whitelist()
def get_programmes_page(**kwargs) -> dict:
	payload = base.get_programmes_page(**kwargs)
	annotate_master_rows(payload.get("programmes") or [], "Program", "program_name")
	annotate_master_rows(payload.get("departments") or [], "Department", "department_name")
	return payload
