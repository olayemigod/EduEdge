from __future__ import annotations

import frappe

from eduedge.permissions_baseline import MANAGE, OPERATE, VIEW, _ensure_permission_row

PLATFORM_AND_SCHOOL_MANAGERS = (
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
)
PHOTO_REVIEWERS = PLATFORM_AND_SCHOOL_MANAGERS + (
	"Registrar",
	"Admission Officer",
	"School HR Officer",
)
PHOTO_REVIEW_RIGHTS = {"read", "create", "report", "export", "print"}


def execute() -> None:
	"""Grant the minimum rights required by the new People Operations surfaces once.

	This is a one-time migration. Later Role Permission Manager changes remain
	authoritative because after_migrate does not re-apply the permission matrix.
	"""
	for role in PLATFORM_AND_SCHOOL_MANAGERS + ("School HR Officer",):
		_ensure_permission_row("Instructor", role, set(MANAGE))
	for role in ("Academics User", "Teacher", "Instructor"):
		_ensure_permission_row("Instructor", role, set(VIEW))

	for role in PLATFORM_AND_SCHOOL_MANAGERS:
		_ensure_permission_row("EduEdge Instructor Assignment", role, set(MANAGE))
	for role in ("Academics User",):
		_ensure_permission_row("EduEdge Instructor Assignment", role, set(OPERATE))
	for role in ("Teacher", "Instructor"):
		_ensure_permission_row("EduEdge Instructor Assignment", role, set(VIEW))

	for role in PHOTO_REVIEWERS:
		_ensure_permission_row("EduEdge Student Photo Review Log", role, set(PHOTO_REVIEW_RIGHTS))

	for doctype in ("Instructor", "EduEdge Instructor Assignment", "EduEdge Student Photo Review Log"):
		if frappe.db.exists("DocType", doctype):
			frappe.clear_cache(doctype=doctype)
