from __future__ import annotations

import frappe


def ensure_erpnext_test_roots() -> None:
	"""Prepare minimal ERPNext tree roots required by upstream test bootstrapping.

	This helper is CI-only and is invoked explicitly by EduEdge workflows. It is not
	registered in install or migrate hooks and therefore has no production side effects.

	ERPNext v16's current test bootstrap may try to create test Item Groups before the
	standard "All Item Groups" root exists on a clean install-only site. Creating the
	missing root keeps EduEdge's database-backed suite deterministic without altering
	ERPNext source or product data during normal runtime.
	"""
	if not frappe.db.exists("DocType", "Item Group"):
		return
	if frappe.db.exists("Item Group", "All Item Groups"):
		return

	root = frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": "All Item Groups",
			"is_group": 1,
			"parent_item_group": "",
		}
	)
	root.flags.ignore_permissions = True
	root.insert()
	frappe.db.commit()
