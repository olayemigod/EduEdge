from __future__ import annotations

from urllib.parse import unquote

import frappe
from frappe import _


POST_ONLY_MUTATION_PREFIXES = (
	"save_",
	"create_",
	"update_",
	"delete_",
	"submit_",
	"cancel_",
	"approve_",
	"reject_",
	"publish_",
	"unpublish_",
	"switch_",
	"clear_",
	"perform_",
	"resolve_",
	"prepare_",
	"assign_",
	"import_",
	"upload_",
	"set_",
	"mark_",
	"record_",
	"finalize_",
	"sync_",
)


def _request_method() -> str:
	request = getattr(frappe.local, "request", None)
	return str(getattr(request, "method", "") or "").upper()


def _request_command() -> str:
	command = str((getattr(frappe.local, "form_dict", None) or {}).get("cmd") or "").strip()
	if command:
		return command
	request = getattr(frappe.local, "request", None)
	path = unquote(str(getattr(request, "path", "") or ""))
	marker = "/api/method/"
	if marker in path:
		return path.split(marker, 1)[1].strip("/")
	return ""


def is_eduedge_mutation_command(command: str) -> bool:
	if not command.startswith("eduedge."):
		return False
	function_name = command.rsplit(".", 1)[-1]
	return function_name.startswith(POST_ONLY_MUTATION_PREFIXES)


def enforce_post_for_mutations() -> None:
	"""Block GET and other non-POST transport for EduEdge mutations.

	This request-boundary control also covers methods redirected through
	override_whitelisted_methods, so legacy source decorators cannot reopen a GET
	mutation path. Normal internal Python calls and read-only RPC methods are not
	affected.
	"""
	method = _request_method()
	if not method or method in {"POST", "OPTIONS"}:
		return
	command = _request_command()
	if not is_eduedge_mutation_command(command):
		return
	frappe.local.response["http_status_code"] = 405
	frappe.throw(
		_("This EduEdge action requires a POST request."),
		frappe.PermissionError,
		title=_("POST Required"),
	)
