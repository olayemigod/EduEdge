from __future__ import annotations

import frappe
from frappe import _

from eduedge.api import question_batch as question_batch_api
from eduedge.api import question_upload as question_upload_api


QUESTION_DOCTYPE = "EduEdge CBT Question"


def _require_upload_permission() -> None:
	question_batch_api._require_create_permission()
	if not frappe.has_permission(QUESTION_DOCTYPE, "import"):
		frappe.throw(
			_("You are not permitted to upload or import CBT questions."),
			frappe.PermissionError,
		)


@frappe.whitelist()
def get_question_upload_access() -> dict:
	"""Return the permission-backed upload capability for the batch page."""
	question_batch_api._require_create_permission()
	return {
		"can_upload": bool(frappe.has_permission(QUESTION_DOCTYPE, "import")),
		"doctype": QUESTION_DOCTYPE,
	}


@frappe.whitelist()
def save_question_batch(common, questions, source: str | None = None) -> dict:
	"""Preserve manual entry while blocking upload-shaped calls without Import."""
	if source == "upload":
		_require_upload_permission()
	return question_batch_api.save_question_batch(common, questions, source=source)


@frappe.whitelist()
def preview_question_upload(file_name: str, file_content: str, common) -> dict:
	_require_upload_permission()
	return question_batch_api.preview_question_upload(file_name, file_content, common)


@frappe.whitelist()
def import_question_upload(file_name: str, file_content: str, common) -> dict:
	_require_upload_permission()
	return question_upload_api.import_question_upload(file_name, file_content, common)
