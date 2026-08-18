from __future__ import annotations

import frappe
from frappe import _


ERPNext_TEST_ITEM_GROUP_ROOT = "All Item Groups"


def ensure_erpnext_test_roots() -> dict:
	"""Prepare upstream ERPNext roots required by its test bootstrap on clean CI sites.

	ERPNext v16's current BootStrapTestData creates `_Test Item Group` beneath the
	hard-coded `All Item Groups` root. A freshly installed, not-yet-setup ERPNext site
	may not have that setup-wizard fixture yet, so Frappe's test preloader can fail
	before any EduEdge test method executes.

	This helper is intentionally test-only and refuses to run unless `allow_tests`
	is enabled for the site. It does not participate in EduEdge installation,
	migration or runtime behavior.
	"""
	if not frappe.conf.get("allow_tests"):
		frappe.throw(_("ERPNext integration test bootstrap requires allow_tests."), frappe.PermissionError)

	created = False
	if not frappe.db.exists("Item Group", ERPNext_TEST_ITEM_GROUP_ROOT):
		doc = frappe.new_doc("Item Group")
		doc.item_group_name = ERPNext_TEST_ITEM_GROUP_ROOT
		doc.is_group = 1
		doc.parent_item_group = ""
		doc.insert(ignore_permissions=True)
		created = True
		frappe.db.commit()

	return {
		"item_group_root": ERPNext_TEST_ITEM_GROUP_ROOT,
		"created": created,
		"exists": bool(frappe.db.exists("Item Group", ERPNext_TEST_ITEM_GROUP_ROOT)),
	}
