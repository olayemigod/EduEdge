from __future__ import annotations

from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_url

from eduedge.cbt.attempts import prepare_attempt


@frappe.whitelist()
def prepare_candidate_launch(candidate_assignment: str) -> dict:
	"""Prepare one school CBT attempt and return a fragment-token launch URL.

	The launch token is returned once and is placed after ``#`` so it is not sent
	in the initial HTTP request, web-server logs, or referrer headers. Only the
	token hash is stored on the Attempt record.
	"""
	result = prepare_attempt(candidate_assignment)
	attempt = quote(str(result["attempt"]), safe="")
	token = quote(str(result["launch_token"]), safe="")
	result["launch_url"] = f"{get_url()}/eduedge-cbt-attempt#attempt={attempt}&token={token}"
	result["launch_notice"] = _(
		"Copy this candidate link now. EduEdge stores only its secure token hash and cannot display the same token again."
	)
	return result
