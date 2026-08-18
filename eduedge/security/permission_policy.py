from __future__ import annotations

import frappe
from frappe.permissions import setup_custom_perms

from eduedge.permissions_baseline import (
	ACADEMIC_OPERATORS,
	ADMISSION_OPERATORS,
	FINANCE_READERS,
	PLATFORM_MANAGERS,
	SCHOOL_MANAGERS,
	apply_default_permission_baseline,
)

HIGH_RISK_DEFAULT_RIGHTS = ("delete", "email", "share")

# Records containing personal, academic, operational, or assessment history.
# Platform roles retain their explicitly seeded authority. Ordinary school roles
# keep Read/Create/Write/Report/Import/Export only where the baseline grants it.
SENSITIVE_DOCTYPES = (
	"Student Admission",
	"Student Applicant",
	"Student",
	"Guardian",
	"Program Enrollment",
	"Student Group",
	"Course Schedule",
	"Student Attendance",
	"Assessment Plan",
	"Assessment Result",
	"EduEdge Program Offering",
	"EduEdge Result Publication",
	"EduEdge Report Card Review",
	"EduEdge Examination Centre",
	"EduEdge CBT Question",
	"EduEdge CBT Exam Template",
	"EduEdge CBT Exam Schedule",
	"EduEdge CBT Candidate Assignment",
	"EduEdge CBT Attempt",
	"EduEdge CBT Attempt Review",
	"EduEdge CBT Result",
)

MANAGED_NON_PLATFORM_ROLES = tuple(
	dict.fromkeys(
		SCHOOL_MANAGERS
		+ ACADEMIC_OPERATORS
		+ ADMISSION_OPERATORS
		+ FINANCE_READERS
		+ (
			"CBT Invigilator",
			"Student Safety Officer",
			"School Operations Manager",
			"School HR Officer",
			"Procurement Officer",
		)
	)
)


def apply_safe_default_permission_baseline() -> dict:
	"""Seed new-site defaults and immediately remove high-risk school-role grants."""
	result = apply_default_permission_baseline()
	hardening = harden_sensitive_managed_permissions()
	return {**result, **hardening}


def harden_sensitive_managed_permissions() -> dict:
	"""Remove unsafe default rights from known EduEdge-managed school roles.

	The cleanup is deliberately bounded to known managed roles and known sensitive
	DocTypes. Platform managers and custom school roles remain governed by Role
	Permission Manager. This function never adds permissions.
	"""
	changed: list[dict] = []
	platform_roles = set(PLATFORM_MANAGERS)
	for doctype in SENSITIVE_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		setup_custom_perms(doctype)
		rows = frappe.get_all(
			"Custom DocPerm",
			filters={
				"parent": doctype,
				"role": ["in", MANAGED_NON_PLATFORM_ROLES],
				"permlevel": 0,
				"if_owner": 0,
			},
			fields=["name", "role", *HIGH_RISK_DEFAULT_RIGHTS],
		)
		for row in rows:
			if row.role in platform_roles:
				continue
			updates = {
				right: 0
				for right in HIGH_RISK_DEFAULT_RIGHTS
				if int(row.get(right) or 0)
			}
			if not updates:
				continue
			frappe.db.set_value("Custom DocPerm", row.name, updates, update_modified=False)
			changed.append({"doctype": doctype, "role": row.role, "removed": sorted(updates)})
		frappe.clear_cache(doctype=doctype)
	return {"hardened_sensitive_permissions": changed}
