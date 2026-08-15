from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint, getdate

from eduedge.education.academic_fields import INSTITUTION_FIELD, OFFERING_FIELD
from eduedge.education.custom_fields import BRANCH_FIELD
from eduedge.education.offerings import assert_branch_access, resolve_program_offering_period_dates

CLASS_ARM_DOCTYPE = "EduEdge Class Arm"
CLASS_ARM_FIELD = "eduedge_class_arm"
DISPLAY_NAME_FIELD = "eduedge_display_name"
PREVIOUS_GROUP_FIELD = "eduedge_previous_student_group"


def clean_class_arm_name(value: str | None) -> str:
	return " ".join(str(value or "").split())


def ensure_class_arm_foundation() -> None:
	if not frappe.db.exists("DocType", "Student Group") or not frappe.db.exists("DocType", CLASS_ARM_DOCTYPE):
		return
	create_custom_fields(
		{
			"Student Group": [
				{
					"fieldname": CLASS_ARM_FIELD,
					"fieldtype": "Link",
					"label": "Class Arm Identity",
					"options": CLASS_ARM_DOCTYPE,
					"read_only": 1,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"insert_after": OFFERING_FIELD,
					"description": "Reusable Class Arm identity shared by this Class Arm across academic periods.",
				},
				{
					"fieldname": DISPLAY_NAME_FIELD,
					"fieldtype": "Data",
					"label": "Class Arm Display Name",
					"read_only": 1,
					"in_list_view": 1,
					"insert_after": CLASS_ARM_FIELD,
					"description": "School-facing Class Arm label. The native Student Group name remains the technical operational identity.",
				},
				{
					"fieldname": PREVIOUS_GROUP_FIELD,
					"fieldtype": "Link",
					"label": "Previous Period Class Arm",
					"options": "Student Group",
					"read_only": 1,
					"insert_after": DISPLAY_NAME_FIELD,
					"description": "Previous operational Student Group in this Class Arm lineage.",
				},
			],
		},
		update=True,
	)
	backfill_class_arm_identities()


def get_or_create_class_arm(
	*,
	branch: str,
	program: str,
	friendly_name: str,
	institution: str | None = None,
	default_capacity: int = 0,
	ignore_permissions: bool = False,
) -> frappe.model.document.Document:
	friendly_name = clean_class_arm_name(friendly_name)
	if not friendly_name:
		frappe.throw(_("Class Arm name is required."), frappe.ValidationError)
	assert_branch_access(branch)
	institution = institution or frappe.db.get_value("EduEdge School Branch", branch, "institution")
	if not institution:
		frappe.throw(_("The selected School Branch / Campus is not linked to an Institution."), frappe.ValidationError)

	rows = frappe.db.sql(
		"""
		select name
		from `tabEduEdge Class Arm`
		where school_branch = %(branch)s
		  and program = %(program)s
		  and lower(trim(class_arm_name)) = lower(trim(%(label)s))
		limit 1
		""",
		{"branch": branch, "program": program, "label": friendly_name},
		as_dict=True,
	)
	if rows:
		return frappe.get_doc(CLASS_ARM_DOCTYPE, rows[0].name)

	if not ignore_permissions and not frappe.has_permission(CLASS_ARM_DOCTYPE, "create"):
		frappe.throw(_("You are not permitted to create Class Arm identities."), frappe.PermissionError)
	doc = frappe.get_doc(
		{
			"doctype": CLASS_ARM_DOCTYPE,
			"class_arm_name": friendly_name,
			"school_branch": branch,
			"institution": institution,
			"program": program,
			"default_capacity": max(cint(default_capacity), 0),
			"enabled": 1,
		}
	)
	doc.insert(ignore_permissions=ignore_permissions)
	return doc


def generate_operational_group_name(
	*,
	friendly_name: str,
	branch: str,
	program: str,
	offering: str,
	academic_year: str | None = None,
	academic_term: str | None = None,
) -> str:
	friendly_name = clean_class_arm_name(friendly_name) or "Class Arm"
	context = " · ".join(value for value in (academic_year, academic_term) if value)
	seed = "::".join(str(value or "") for value in (branch, program, offering, friendly_name.casefold()))
	digest = hashlib.sha1(seed.encode()).hexdigest()[:10].upper()
	base = friendly_name[:72]
	if context:
		base = f"{base} · {context[:42]}"
	return f"{base} · {digest}"[:140]


def destination_is_later(source_offering, destination_offering) -> bool:
	source_start, source_end = resolve_program_offering_period_dates(source_offering)
	destination_start, destination_end = resolve_program_offering_period_dates(destination_offering)
	source_start = getdate(source_start) if source_start else None
	source_end = getdate(source_end) if source_end else None
	destination_start = getdate(destination_start) if destination_start else None
	destination_end = getdate(destination_end) if destination_end else None
	if source_end and destination_start:
		return destination_start > source_end
	if source_start and destination_start:
		return destination_start > source_start
	if source_end and destination_end:
		return destination_end > source_end
	return False


def validate_student_group_class_arm(doc) -> None:
	meta = doc.meta
	if not meta.has_field(CLASS_ARM_FIELD):
		return
	class_arm = doc.get(CLASS_ARM_FIELD)
	if not class_arm:
		return
	identity = frappe.db.get_value(
		CLASS_ARM_DOCTYPE,
		class_arm,
		["class_arm_name", "school_branch", "institution", "program", "enabled"],
		as_dict=True,
	)
	if not identity or not cint(identity.enabled):
		frappe.throw(_("Select an enabled Class Arm identity."), frappe.ValidationError)
	if doc.get(BRANCH_FIELD) and doc.get(BRANCH_FIELD) != identity.school_branch:
		frappe.throw(_("Class Arm identity must belong to the same Branch / Campus as the Student Group."), frappe.ValidationError)
	if doc.program and doc.program != identity.program:
		frappe.throw(_("Class Arm identity must belong to the same Class / Programme as the Student Group."), frappe.ValidationError)
	if meta.has_field(INSTITUTION_FIELD) and doc.get(INSTITUTION_FIELD) and doc.get(INSTITUTION_FIELD) != identity.institution:
		frappe.throw(_("Class Arm identity must belong to the same Institution as the Student Group."), frappe.ValidationError)
	if meta.has_field(DISPLAY_NAME_FIELD):
		doc.set(DISPLAY_NAME_FIELD, identity.class_arm_name)

	if not doc.is_new():
		fields = [BRANCH_FIELD, OFFERING_FIELD, "program", "academic_year", "academic_term", CLASS_ARM_FIELD]
		fields = [field for field in fields if meta.has_field(field)]
		original = frappe.db.get_value("Student Group", doc.name, fields, as_dict=True) or {}
		for fieldname in fields:
			old = original.get(fieldname)
			if old and old != doc.get(fieldname):
				frappe.throw(
					_("Academic context cannot be changed on an existing Class Arm period. Prepare a new period instead."),
					frappe.ValidationError,
				)


def backfill_class_arm_identities() -> None:
	if not frappe.db.exists("DocType", CLASS_ARM_DOCTYPE):
		return
	meta = frappe.get_meta("Student Group")
	if not (meta.has_field(CLASS_ARM_FIELD) and meta.has_field(DISPLAY_NAME_FIELD) and meta.has_field(BRANCH_FIELD)):
		return
	fields = ["name", "student_group_name", "program", BRANCH_FIELD, CLASS_ARM_FIELD, DISPLAY_NAME_FIELD, "max_strength"]
	if meta.has_field(INSTITUTION_FIELD):
		fields.append(INSTITUTION_FIELD)
	rows = frappe.get_all(
		"Student Group",
		filters={BRANCH_FIELD: ["is", "set"], "program": ["is", "set"]},
		fields=fields,
		order_by="creation asc",
		limit_page_length=0,
	)
	for row in rows:
		if row.get(CLASS_ARM_FIELD):
			continue
		friendly = clean_class_arm_name(row.get(DISPLAY_NAME_FIELD) or row.student_group_name or row.name)
		if not friendly:
			continue
		institution = row.get(INSTITUTION_FIELD) or frappe.db.get_value("EduEdge School Branch", row.get(BRANCH_FIELD), "institution")
		if not institution:
			continue
		identity = get_or_create_class_arm(
			branch=row.get(BRANCH_FIELD),
			program=row.program,
			friendly_name=friendly,
			institution=institution,
			default_capacity=cint(row.max_strength),
			ignore_permissions=True,
		)
		updates = {CLASS_ARM_FIELD: identity.name}
		if not row.get(DISPLAY_NAME_FIELD):
			updates[DISPLAY_NAME_FIELD] = identity.class_arm_name
		frappe.db.set_value("Student Group", row.name, updates, update_modified=False)
	frappe.clear_cache(doctype="Student Group")
	frappe.clear_cache(doctype=CLASS_ARM_DOCTYPE)
