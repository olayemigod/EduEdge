from __future__ import annotations

import frappe
from frappe.permissions import add_permission, update_permission_property

from eduedge.cbt.result_sync_fields import ensure_result_sync_custom_fields
from eduedge.education.custom_fields import (
	backfill_education_branch_context,
	ensure_education_custom_fields,
)
from eduedge.education.enrollment_field_setup import ensure_program_enrollment_branch_selector
from eduedge.education.institution_type_defaults import apply_institution_type_defaults
from eduedge.education.institution_types import ensure_institution_type_foundation
from eduedge.education.native_hierarchy_migration import ensure_native_academic_context_foundation
from eduedge.permissions_baseline import (
	apply_default_permission_baseline,
	ensure_eduedge_page_role_baseline,
)

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

ADMISSION_MANAGER_ROLES = (
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
)

ADMISSION_PERMISSION_TYPES = (
	"read",
	"write",
	"create",
	"delete",
	"report",
	"export",
	"print",
	"email",
	"share",
)

TRAINING_PROGRESS_ROLES = (
	"EduEdge Super Administrator",
	"System Manager",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"School Operations Manager",
	"Registrar",
	"Admission Officer",
	"Bursar",
	"Accounts User",
	"Accounts Manager",
	"Teacher",
	"Instructor",
	"CBT Invigilator",
	"Student Safety Officer",
	"School HR Officer",
	"HR User",
	"HR Manager",
	"Procurement Officer",
	"Purchase User",
	"Purchase Manager",
	"Stock User",
	"Stock Manager",
	"Asset User",
	"Asset Manager",
	"Student",
	"EduEdge Parent",
)


def after_install() -> None:
	ensure_institution_type_foundation()
	apply_institution_type_defaults()
	ensure_roles()
	ensure_education_custom_fields()
	ensure_result_sync_custom_fields()
	ensure_native_academic_context_foundation()
	ensure_program_enrollment_branch_selector()
	ensure_admission_manager_permissions()
	ensure_training_progress_permissions()
	ensure_training_page_roles()
	apply_default_permission_baseline()
	ensure_eduedge_page_role_baseline()
	backfill_education_branch_context()


def after_migrate() -> None:
	"""Maintain combined schema/runtime foundations without overwriting role permissions."""
	ensure_institution_type_foundation()
	apply_institution_type_defaults()
	ensure_roles()
	ensure_education_custom_fields()
	ensure_result_sync_custom_fields()
	ensure_native_academic_context_foundation()
	ensure_program_enrollment_branch_selector()
	ensure_admission_manager_permissions()
	ensure_training_progress_permissions()
	ensure_training_page_roles()
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


def ensure_admission_manager_permissions() -> None:
	"""Grant intended EduEdge administrators normal Frappe admission permissions."""
	if not frappe.db.exists("DocType", "Student Admission"):
		return
	for role in ADMISSION_MANAGER_ROLES:
		if not frappe.db.exists(
			"Custom DocPerm",
			{
				"parent": "Student Admission",
				"role": role,
				"permlevel": 0,
				"if_owner": 0,
			},
		):
			add_permission("Student Admission", role, permlevel=0, ptype="read")
		for permission_type in ADMISSION_PERMISSION_TYPES:
			update_permission_property(
				"Student Admission",
				role,
				0,
				permission_type,
				1,
				validate=False,
			)
	frappe.clear_cache(doctype="Student Admission")


def ensure_training_progress_permissions() -> None:
	"""Allow supported role families to maintain only their own training progress."""
	if not frappe.db.exists("DocType", "EduEdge Training Progress"):
		return
	for role in TRAINING_PROGRESS_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists(
			"Custom DocPerm",
			{
				"parent": "EduEdge Training Progress",
				"role": role,
				"permlevel": 0,
				"if_owner": 0,
			},
		):
			add_permission("EduEdge Training Progress", role, permlevel=0, ptype="read")
		for permission_type in ("read", "write", "create", "delete"):
			update_permission_property(
				"EduEdge Training Progress",
				role,
				0,
				permission_type,
				1,
				validate=False,
			)
	frappe.clear_cache(doctype="EduEdge Training Progress")


def ensure_training_page_roles() -> None:
	"""Expose the Desk Training Centre only to existing roles with Desk access."""
	if not frappe.db.exists("Page", "eduedge-training-centre"):
		return
	page = frappe.get_doc("Page", "eduedge-training-centre")
	existing = {row.role for row in page.roles}
	changed = False
	for role in TRAINING_PROGRESS_ROLES:
		if role in existing or role in {"EduEdge Parent", "Student"}:
			continue
		desk_access = frappe.db.get_value("Role", role, "desk_access")
		if not desk_access:
			continue
		page.append("roles", {"role": role})
		existing.add(role)
		changed = True
	if changed:
		page.save(ignore_permissions=True)
		frappe.clear_cache()
