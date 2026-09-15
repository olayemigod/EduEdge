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



def install_frappe_v16_test_dependency_compat() -> None:
	"""Skip dangling Link options during Frappe v16 test dependency discovery.

	ERPNext v16 still contains Link fields to optional doctypes such as
	`Payment Gateway` that are supplied only when the corresponding optional
	integration app is installed. Frappe's legacy compatibility preloader walks
	every Link as a required test dependency and raises DoesNotExistError before
	EduEdge integration tests can start.

	This patch is intentionally installed only from `eduedge.tests`; it never
	runs in product install, migrate, request, or worker processes.
	"""
	from frappe.tests.utils import generators

	if getattr(generators, "_eduedge_optional_doctype_guard_installed", False):
		return

	original = generators.get_missing_records_doctypes

	def guarded_get_missing_records_doctypes(doctype, visited=None):
		if not frappe.db.exists("DocType", doctype):
			return []
		try:
			return original(doctype, visited)
		except frappe.DoesNotExistError:
			# A nested dependency may itself be an optional app DocType. Skip only
			# when the missing DocType is genuinely absent on this installed site.
			if not frappe.db.exists("DocType", doctype):
				return []
			raise

	original_try_create = generators._try_create

	def guarded_try_create(record, reset=False, commit=False):
		"""Let upstream test fixtures keep their native institution-neutral shape.

		EduEdge intentionally requires Institution ownership on new academic masters,
		but Frappe Education/ERPNext legacy test fixtures are created before EduEdge
		tests run and do not know about EduEdge custom fields. Relax only the
		"required on insert" part while Frappe's test-record generator is creating a
		fixture. Direct EduEdge test inserts still exercise the production validator.
		"""
		from eduedge.education import academic_validation

		original_validate = academic_validation.validate_master_institution

		def fixture_validate_master_institution(doc, *, required=False):
			if required and doc.meta.has_field("eduedge_institution") and not doc.get("eduedge_institution"):
				return original_validate(doc, required=False)
			return original_validate(doc, required=required)

		academic_validation.validate_master_institution = fixture_validate_master_institution
		try:
			return original_try_create(record, reset=reset, commit=commit)
		finally:
			academic_validation.validate_master_institution = original_validate

	generators.get_missing_records_doctypes = guarded_get_missing_records_doctypes
	generators._try_create = guarded_try_create
	generators._eduedge_optional_doctype_guard_installed = True
