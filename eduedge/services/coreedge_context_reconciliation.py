from __future__ import annotations

import frappe
from frappe.utils import cint


def get_context_reconciliation_rows(
	company: str | None = None,
	*,
	include_disabled: bool = True,
) -> list[dict]:
	"""
	Return EduEdge School Branch rows in the CoreEdge reconciliation shape.

	The helper is read-only. EduEdge School Branch remains the operational and
	accounting-default authority until a later, explicit platform cutover.
	"""
	filters = {}
	if company:
		filters["company"] = company
	if not include_disabled:
		filters["enabled"] = 1

	branches = frappe.get_all(
		"EduEdge School Branch",
		filters=filters,
		fields=[
			"name",
			"branch_name",
			"branch_code",
			"company",
			"enabled",
			"platform_branch_id",
		],
		limit_page_length=0,
		order_by="company asc, branch_name asc, name asc",
	)

	return [
		{
			"local_doctype": "EduEdge School Branch",
			"local_name": str(row.get("name") or "").strip(),
			"local_label": str(row.get("branch_name") or row.get("name") or "").strip(),
			"local_code": str(row.get("branch_code") or "").strip(),
			"company": str(row.get("company") or "").strip(),
			"active": bool(cint(row.get("enabled"))),
			"platform_branch_id": str(row.get("platform_branch_id") or "").strip(),
		}
		for row in branches
		if row.get("name") and row.get("company")
	]
