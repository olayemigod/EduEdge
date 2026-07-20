from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from eduedge.training.catalog import (
	AUDIENCES,
	allowed_audience_keys,
	can_view_module,
	extract_heading_section,
	load_manifest,
	module_availability,
	module_by_id,
	primary_audience,
	read_markdown,
	screenshot_references,
	visible_modules,
)


def _is_administrator(user: str | None = None) -> bool:
	return (user or frappe.session.user) == "Administrator"


def _parse_list(value) -> list[str]:
	if value in (None, ""):
		return []
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except Exception:
			value = []
	if not isinstance(value, list):
		return []
	result = []
	for item in value:
		item = str(item or "").strip()
		if item and item not in result:
			result.append(item)
	return result


def _progress_key(user: str, module_id: str) -> str:
	return hashlib.sha256(f"{user}|{module_id}".encode()).hexdigest()


def _progress_rows(user: str, module_ids: list[str]) -> dict[str, dict]:
	if not module_ids or not frappe.db.exists("DocType", "EduEdge Training Progress"):
		return {}
	rows = frappe.get_all(
		"EduEdge Training Progress",
		filters={"user": user, "module_id": ["in", module_ids]},
		fields=[
			"name",
			"module_id",
			"status",
			"progress_percent",
			"completed_step_ids",
			"started_on",
			"last_opened_on",
			"completed_on",
		],
	)
	for row in rows:
		row["completed_step_ids"] = _parse_list(row.get("completed_step_ids"))
	return {row["module_id"]: row for row in rows}


def _public_module(
	module: dict,
	progress: dict | None,
	completed_modules: set[str],
	user: str | None = None,
) -> dict:
	user = user or frappe.session.user
	administrator_override = _is_administrator(user)
	progress = progress or {}
	missing = [item for item in module.get("prerequisites") or [] if item not in completed_modules]
	site_availability = module_availability(module)
	available = site_availability["available"] or administrator_override
	locked = False if administrator_override else bool(missing) or not site_availability["available"]
	return {
		"module_id": module["module_id"],
		"title": module["title"],
		"audience": module["audience"],
		"role_group": module["role_group"],
		"category": module["category"],
		"short_description": module["short_description"],
		"order": module["order"],
		"estimated_minutes": module["estimated_minutes"],
		"content_version": module["content_version"],
		"prerequisites": module.get("prerequisites") or [],
		"missing_prerequisites": missing,
		"required_apps": module.get("required_apps") or [],
		"required_doctypes": module.get("required_doctypes") or [],
		"site_available": site_availability["available"],
		"available": available,
		"missing_apps": site_availability["missing_apps"],
		"missing_doctypes": site_availability["missing_doctypes"],
		"availability_message": site_availability["availability_message"],
		"administrator_override": administrator_override,
		"locked": locked,
		"has_video": module["has_video"],
		"video_display_status": module["video_display_status"],
		"status": progress.get("status") or "Not Started",
		"progress_percent": float(progress.get("progress_percent") or 0),
		"completed_step_ids": progress.get("completed_step_ids") or [],
		"step_count": len(module.get("steps") or []),
		"started_on": progress.get("started_on"),
		"last_opened_on": progress.get("last_opened_on"),
		"completed_on": progress.get("completed_on"),
	}


def _assert_prerequisites(module: dict, user: str) -> None:
	if _is_administrator(user):
		return
	prerequisites = module.get("prerequisites") or []
	if not prerequisites:
		return
	rows = _progress_rows(user, prerequisites)
	missing = [item for item in prerequisites if rows.get(item, {}).get("status") != "Completed"]
	if missing:
		frappe.throw(
			_("Complete the prerequisite module(s) first: {0}").format(", ".join(missing)),
			frappe.ValidationError,
		)


def _assert_available(module: dict, user: str | None = None) -> None:
	if _is_administrator(user):
		return
	availability = module_availability(module)
	if availability["available"]:
		return
	frappe.throw(
		availability["availability_message"] or _("This training module is not available on this site."),
		frappe.ValidationError,
	)


@frappe.whitelist()
def get_training_overview(audience: str | None = None) -> dict:
	user = frappe.session.user
	administrator_override = _is_administrator(user)
	allowed = list(AUDIENCES) if administrator_override else allowed_audience_keys(user)
	selected = str(audience or "").strip() or (
		"processedge_staff" if administrator_override else primary_audience(user)
	)
	if selected not in allowed:
		frappe.throw(_("That training path is not available for your role."), frappe.PermissionError)
	modules = (
		[module for module in load_manifest() if module["status"] == "Published"]
		if administrator_override
		else visible_modules(user)
	)
	rows = _progress_rows(user, [module["module_id"] for module in modules])
	completed_modules = {
		module_id for module_id, progress in rows.items() if progress.get("status") == "Completed"
	}
	payload = [
		_public_module(module, rows.get(module["module_id"]), completed_modules, user)
		for module in modules
		if module["audience"] in {"shared", selected}
	]
	completed = sum(1 for module in payload if module["status"] == "Completed")
	in_progress = sum(1 for module in payload if module["status"] == "In Progress")
	available = sum(1 for module in payload if module["available"])
	user_doc = frappe.get_cached_value(
		"User",
		user,
		["full_name", "user_image"],
		as_dict=True,
	) or {}
	return {
		"user": {
			"name": user,
			"full_name": user_doc.get("full_name") or user,
			"image": user_doc.get("user_image") or "",
		},
		"administrator_override": administrator_override,
		"selected_audience": selected,
		"primary_audience": "processedge_staff" if administrator_override else primary_audience(user),
		"audiences": [
			{
				"key": key,
				"label": AUDIENCES[key]["label"],
				"description": AUDIENCES[key]["description"],
			}
			for key in allowed
			if key != "shared"
		],
		"modules": payload,
		"summary": {
			"total": len(payload),
			"available": available,
			"unavailable": len(payload) - available,
			"completed": completed,
			"in_progress": in_progress,
			"estimated_minutes": sum(
				module["estimated_minutes"] for module in payload if module["available"]
			),
			"progress_percent": round((completed / available) * 100, 1) if available else 0,
		},
	}


@frappe.whitelist()
def get_training_module_content(module_id: str) -> dict:
	user = frappe.session.user
	module = module_by_id(module_id)
	if not _is_administrator(user) and not can_view_module(module, user):
		frappe.throw(_("You are not permitted to view this training module."), frappe.PermissionError)
	_assert_available(module, user)
	markdown = read_markdown(module)
	rows = _progress_rows(
		user,
		[module_id, *(module.get("prerequisites") or [])],
	)
	completed_modules = {
		key for key, progress in rows.items() if progress.get("status") == "Completed"
	}
	return {
		"module": {
			**_public_module(module, rows.get(module_id), completed_modules, user),
			"steps": module["steps"],
			"video_embed_url": module["video_embed_url"],
			"video_title": module["video_title"],
		},
		"markdown": markdown,
		"practice_exercise": extract_heading_section(
			markdown,
			{"practice exercise", "practical exercise"},
		),
		"screenshots": screenshot_references(markdown),
	}


@frappe.whitelist()
def save_training_progress(
	module_id: str,
	completed_step_ids: str | list | None = None,
	status: str | None = None,
) -> dict:
	user = frappe.session.user
	module = module_by_id(module_id)
	if not _is_administrator(user) and not can_view_module(module, user):
		frappe.throw(_("You are not permitted to update this training module."), frappe.PermissionError)
	_assert_available(module, user)
	_assert_prerequisites(module, user)
	valid_steps = [step["step_id"] for step in module["steps"]]
	completed = [step_id for step_id in _parse_list(completed_step_ids) if step_id in valid_steps]
	percent = round((len(completed) / len(valid_steps)) * 100, 1)
	requested_status = str(status or "").strip()
	if percent >= 100 or requested_status == "Completed":
		if len(completed) != len(valid_steps):
			frappe.throw(_("Complete every guided step before marking this module complete."))
		resolved_status = "Completed"
	elif completed or requested_status == "In Progress":
		resolved_status = "In Progress"
	else:
		resolved_status = "Not Started"
	key = _progress_key(user, module_id)
	name = frappe.db.get_value("EduEdge Training Progress", {"training_key": key}, "name")
	now = now_datetime()
	if name:
		doc = frappe.get_doc("EduEdge Training Progress", name)
		doc.check_permission("write")
	else:
		if not frappe.has_permission("EduEdge Training Progress", "create"):
			frappe.throw(_("You are not permitted to record training progress."), frappe.PermissionError)
		doc = frappe.new_doc("EduEdge Training Progress")
		doc.user = user
		doc.training_key = key
		doc.module_id = module_id
		doc.started_on = now
	doc.module_title = module["title"]
	doc.audience = module["audience"]
	doc.content_version = module["content_version"]
	doc.status = resolved_status
	doc.progress_percent = percent
	doc.completed_step_ids = json.dumps(completed)
	doc.last_opened_on = now
	doc.completed_on = now if resolved_status == "Completed" else None
	if doc.is_new():
		doc.insert()
	else:
		doc.save()
	return {
		"module_id": module_id,
		"status": doc.status,
		"progress_percent": float(doc.progress_percent or 0),
		"completed_step_ids": completed,
		"completed_on": doc.completed_on,
	}


@frappe.whitelist()
def reset_training_progress(module_id: str) -> dict:
	user = frappe.session.user
	module = module_by_id(module_id)
	if not _is_administrator(user) and not can_view_module(module, user):
		frappe.throw(_("You are not permitted to reset this training module."), frappe.PermissionError)
	_assert_available(module, user)
	key = _progress_key(user, module_id)
	name = frappe.db.get_value("EduEdge Training Progress", {"training_key": key}, "name")
	if name:
		doc = frappe.get_doc("EduEdge Training Progress", name)
		doc.check_permission("delete")
		doc.delete()
	return {"module_id": module_id, "status": "Not Started", "progress_percent": 0}
