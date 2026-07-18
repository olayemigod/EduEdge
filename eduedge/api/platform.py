from __future__ import annotations

import frappe

from eduedge.platform.access import get_eduedge_access_decision
from eduedge.platform.client import get_platform_client
from eduedge.platform.config import get_platform_config


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw("Authentication required.", frappe.PermissionError)


@frappe.whitelist()
def get_platform_status() -> dict:
	_require_login()
	config = get_platform_config()
	client = get_platform_client(config)
	return {
		"configuration": config.sanitized(),
		"health": client.get_health(),
	}


@frappe.whitelist()
def get_my_access_decision(
	feature_key: str | None = None,
	action: str | None = None,
) -> dict:
	_require_login()
	return get_eduedge_access_decision(
		user=frappe.session.user,
		feature_key=feature_key,
		action=action,
	)
