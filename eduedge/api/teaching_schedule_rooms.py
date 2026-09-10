from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import academic_operations_safe as operations
from eduedge.education.custom_fields import BRANCH_FIELD


def _resolved_branch(branch: str) -> str:
	return operations.base._resolve_branch(branch)


def _require_room_create() -> None:
	operations.base._require_academic_operator()
	if not frappe.has_permission("Room", "create"):
		frappe.throw(_("You are not permitted to create Rooms."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def create_teaching_schedule_room(
	branch: str,
	room_name: str,
	room_number: str = "",
	seating_capacity: str = "",
) -> dict:
	"""Create or reuse one native Education Room for the selected Branch / Campus."""
	_require_room_create()
	resolved_branch = _resolved_branch(branch)
	cleaned_name = str(room_name or "").strip()
	if not cleaned_name:
		frappe.throw(_("Room Name is required."), frappe.ValidationError)

	existing = frappe.db.get_value(
		"Room",
		{BRANCH_FIELD: resolved_branch, "room_name": cleaned_name},
		["name", "room_name", "room_number", "seating_capacity"],
		as_dict=True,
	)
	if existing:
		return {
			"value": existing.name,
			"name": existing.name,
			"label": existing.room_name or existing.name,
			"room_name": existing.room_name or existing.name,
			"room_number": existing.room_number or "",
			"seating_capacity": existing.seating_capacity or "",
			BRANCH_FIELD: resolved_branch,
			"created": False,
		}

	values = {
		"doctype": "Room",
		"room_name": cleaned_name,
		BRANCH_FIELD: resolved_branch,
	}
	meta = frappe.get_meta("Room")
	if meta.has_field("room_number") and str(room_number or "").strip():
		values["room_number"] = str(room_number).strip()
	if meta.has_field("seating_capacity") and str(seating_capacity or "").strip():
		values["seating_capacity"] = str(seating_capacity).strip()

	# Keep native Room validation, EduEdge Branch validation and normal create
	# permissions authoritative. Quick create must never bypass those controls.
	doc = frappe.get_doc(values)
	doc.insert()

	return {
		"value": doc.name,
		"name": doc.name,
		"label": doc.room_name or doc.name,
		"room_name": doc.room_name or doc.name,
		"room_number": doc.get("room_number") or "",
		"seating_capacity": doc.get("seating_capacity") or "",
		BRANCH_FIELD: doc.get(BRANCH_FIELD),
		"created": True,
	}
