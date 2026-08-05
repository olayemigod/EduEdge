from __future__ import annotations

import frappe

from eduedge.cbt.result_sync_fields import ensure_result_sync_custom_fields
from eduedge.education.custom_fields import (
	backfill_education_branch_context,
	ensure_education_custom_fields,
)
from eduedge.education.enrollment_field_setup import ensure_program_enrollment_branch_selector
from eduedge.education.institution_type_defaults import apply_institution_type_defaults
from eduedge.education.institution_types import ensure_institution_type_foundation
from eduedge.education.native_hierarchy_migration import ensure_native_academic_context_foundation
from eduedge.education.people_fields import ensure_people_operations_foundation
from eduedge.permissions_baseline import ensure_eduedge_page_role_baseline
from eduedge.security.permission_policy import apply_safe_default_permission_baseline

ROLE_DESK_ACCESS = {
	"EduEdge Super Administrator": 1,
	"EduEdge Public Exam Administrator": 1,
	"EduEdge Administrator": 1,
	"School Administrator": 1,
	"Academic Administrator": 1,
	"Bursar": 1,
	"Teacher": 1,
	"CBT Invigilator": 1,
	"Student Safety Officer": 1,
	"Registrar": 1,
	"Admission Officer": 1,
	"School HR Officer": 1,
	"Procurement Officer": 1,
	"School Operations Manager": 1,
	"EduEdge Parent": 0,
}


def after_install() -> None:
	ensure_institution_type_foundation()
	apply_institution_type_defaults()
	ensure_roles()
	ensure_education_custom_fields()
	ensure_result_sync_custom_fields()
	ensure_native_academic_context_foundation()
	ensure_people_operations_foundation()
	ensure_program_enrollment_branch_selector()
	# Seed a least-privilege default matrix once for a new site. Existing sites
	# are normalised by idempotent patches and later Role Permission Manager
	# choices remain authoritative.
	apply_safe_default_permission_baseline()
	ensure_eduedge_page_role_baseline()
	backfill_education_branch_context()


def after_migrate() -> None:
	"""Maintain schema/runtime foundations without re-granting role permissions."""
	ensure_institution_type_foundation()
	apply_institution_type_defaults()
	ensure_roles()
	ensure_education_custom_fields()
	ensure_result_sync_custom_fields()
	ensure_native_academic_context_foundation()
	ensure_people_operations_foundation()
	ensure_program_enrollment_branch_selector()
	# Standard Page JSON may reintroduce legacy role rows during model sync.
	# Keep EdgeSuite shells neutral; menus, APIs and DocTypes remain authoritative.
	ensure_eduedge_page_role_baseline()
	backfill_education_branch_context()


def ensure_roles() -> None:
	for role_name, desk_access in ROLE_DESK_ACCESS.items():
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": desk_access,
				}
			).insert(ignore_permissions=True)
		elif role_name == "EduEdge Parent":
			frappe.db.set_value("Role", role_name, "desk_access", 0, update_modified=False)
