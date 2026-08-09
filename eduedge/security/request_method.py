from __future__ import annotations

from urllib.parse import unquote

import frappe
from frappe import _

from eduedge.security.cbt_candidate_requests import (
	enforce_candidate_request,
	is_candidate_command,
)
from eduedge.security.feature_gate import enforce_feature_for_command


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
	"end_",
	"replace_",
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


def _reject_non_post() -> None:
	frappe.local.response["http_status_code"] = 405
	frappe.throw(
		_("This EduEdge action requires a POST request."),
		frappe.PermissionError,
		title=_("POST Required"),
	)


def enforce_post_for_mutations() -> None:
	"""Protect feature access, all EduEdge mutations, and public CBT requests.

	The request-boundary control also covers methods redirected through
	override_whitelisted_methods, so legacy source decorators cannot reopen a GET
	mutation path. Candidate launch tokens are accepted only in POST bodies and
	are validated and throttled before any Attempt query runs.
	"""
	method = _request_method()
	if not method:
		return
	command = _request_command()
	if command.startswith("eduedge."):
		enforce_feature_for_command(command)
	if is_candidate_command(command):
		if method == "OPTIONS":
			return
		if method != "POST":
			_reject_non_post()
		enforce_candidate_request(command, getattr(frappe.local, "form_dict", None) or {})
		return
	if method in {"POST", "OPTIONS"} or not is_eduedge_mutation_command(command):
		return
	_reject_non_post()
