"""EduEdge test package bootstrap.

The import guard is deliberately test-only. Frappe initializes the site before
discovering EduEdge tests, so this gives clean ERPNext v16 test runs their
required tree root inside the same Python process without registering a product
hook or altering production install/migrate behaviour.
"""

try:
	import frappe
except ImportError:  # pure contract-test environment
	frappe = None

if frappe is not None and getattr(frappe.local, "site", None) and frappe.db:
	from eduedge.ci import ensure_erpnext_test_roots

	ensure_erpnext_test_roots()
