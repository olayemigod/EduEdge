from __future__ import annotations

import frappe

from eduedge.permissions_baseline import MANAGE, OPERATE, VIEW, _ensure_permission_row

CURRICULUM_MANAGERS = (
	"System Manager",
	"EduEdge Super Administrator",
	"EduEdge Administrator",
	"School Administrator",
	"Academic Administrator",
	"Education Manager",
	"Academics User",
)
TEACHER_COURSE_RIGHTS = set(VIEW) | {"write"}
TEACHER_TOPIC_RIGHTS = set(OPERATE)


def execute() -> None:
	"""Grant page-level curriculum rights once; record hooks remain authoritative."""
	for role in CURRICULUM_MANAGERS:
		_ensure_permission_row("Course", role, set(MANAGE))
		_ensure_permission_row("Topic", role, set(MANAGE))
	for role in ("Teacher", "Instructor"):
		_ensure_permission_row("Course", role, TEACHER_COURSE_RIGHTS)
		_ensure_permission_row("Topic", role, TEACHER_TOPIC_RIGHTS)
	for doctype in ("Course", "Topic"):
		if frappe.db.exists("DocType", doctype):
			frappe.clear_cache(doctype=doctype)
