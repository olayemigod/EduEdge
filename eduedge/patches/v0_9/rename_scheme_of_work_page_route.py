from __future__ import annotations

import frappe


OLD_PAGE = "eduedge-scheme-of-work"
NEW_PAGE = "eduedge-schemes-of-work"


def execute() -> None:
	"""Remove the custom Page name that collides with the Scheme DocType Desk route.

	`EduEdge Scheme of Work` naturally owns `/app/eduedge-scheme-of-work` as its
	DocType route. The EdgeSuite workbench therefore uses the plural Page route
	`/app/eduedge-schemes-of-work`.
	"""
	old_exists = bool(frappe.db.exists("Page", OLD_PAGE))
	new_exists = bool(frappe.db.exists("Page", NEW_PAGE))

	if old_exists and not new_exists:
		frappe.rename_doc("Page", OLD_PAGE, NEW_PAGE, force=True, ignore_permissions=True)
	elif old_exists and new_exists:
		frappe.delete_doc("Page", OLD_PAGE, force=True, ignore_permissions=True)

	frappe.clear_cache()
