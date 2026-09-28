from __future__ import annotations

import frappe

from eduedge.permissions_baseline import (
    ACADEMIC_OPERATORS,
    MANAGE,
    PLATFORM_MANAGERS,
    SCHOOL_MANAGERS,
    VIEW,
    _ensure_permission_row,
)

INSTRUCTOR_MANAGERS = PLATFORM_MANAGERS + SCHOOL_MANAGERS + ("School HR Officer",)


def execute() -> None:
    """Reconcile the missing native Instructor defaults once.

    Older sites received these People Operations permissions from the v0.9
    migration, but clean installs created after that migration could miss them
    because the clean-install baseline did not include Instructor. Add only the
    known EduEdge managed-role defaults; custom roles are deliberately untouched.
    """
    if not frappe.db.exists("DocType", "Instructor"):
        return

    for role in INSTRUCTOR_MANAGERS:
        _ensure_permission_row("Instructor", role, set(MANAGE))
    for role in ACADEMIC_OPERATORS:
        _ensure_permission_row("Instructor", role, set(VIEW))

    frappe.clear_cache(doctype="Instructor")
