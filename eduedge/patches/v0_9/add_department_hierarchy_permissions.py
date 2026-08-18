from __future__ import annotations

import frappe

from eduedge.permissions_baseline import (
	ACADEMIC_OPERATORS,
	ADMISSION_OPERATORS,
	MANAGE,
	PLATFORM_MANAGERS,
	SCHOOL_MANAGERS,
	VIEW,
	_ensure_permission_row,
)


HIERARCHY_MANAGERS = PLATFORM_MANAGERS + SCHOOL_MANAGERS
HIERARCHY_VIEWERS = ACADEMIC_OPERATORS + ADMISSION_OPERATORS + ("CBT Invigilator",)


def execute() -> None:
	"""Align native Department / School Section rights with the EduEdge academic hierarchy.

	Program/Class management depends on a valid Department/School Section. Existing
	sites created before this correction may allow school managers to maintain
	Programs while treating Department as read-only. Seed only the missing default
	rights; record-level Institution permission hooks remain authoritative.
	"""
	if not frappe.db.exists("DocType", "Department"):
		return

	for role in HIERARCHY_MANAGERS:
		_ensure_permission_row("Department", role, set(MANAGE))
	for role in HIERARCHY_VIEWERS:
		_ensure_permission_row("Department", role, set(VIEW))

	frappe.clear_cache(doctype="Department")
